import os
import re
import time
import logging
import hashlib
from typing import Dict, List, Optional, Union
from urllib.parse import urljoin, urlparse
from pathlib import Path

from bs4 import BeautifulSoup, Comment
from django.conf import settings
from django.core.cache import cache
from django.template.loader import render_to_string
from django.template import Template, Context

from blog.utils import get_blog_from_template_name, get_all_blog_posts, find_blog_template

logger = logging.getLogger(__name__)

CACHE_TIMEOUT = 1200 # 20 minutes


def normalize_template_name(template_name: str) -> str:
    """Normalize template name to ensure consistent casing.
    
    Converts template names to lowercase to avoid duplicate nodes
    caused by case differences between filesystem names and URL paths.
    """
    return template_name.lower() if template_name else template_name


class LinkParser:
    """Service for parsing HTML content and extracting links from blog posts."""
    
    INTERNAL_BLOG_PATTERN = re.compile(r'/b/(\d{4}_[^/]+)/?')
    CACHE_TIMEOUT = CACHE_TIMEOUT
    CONTEXT_LENGTH = 100
    
    def __init__(self, base_url: str = ''):
        self.base_url = base_url.rstrip('/')
        
    def parse_blog_post(self, template_name: str, force_refresh: bool = False) -> Dict:
        """Parse a single blog post and extract all links with context."""
        # Normalize template name for consistent caching
        normalized_name = normalize_template_name(template_name)
        cache_key = f'blog:links:{normalized_name}'
        
        # Check cache
        if not force_refresh and not self._is_cache_stale(template_name, cache_key):
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.debug(f"Using cached link data for {template_name}")
                return cached_result
        
        try:
            html_content = self._get_template_content(template_name)
            result = self._parse_html_content(html_content, normalized_name)
            
            # Cache the result
            cache.set(cache_key, result, self.CACHE_TIMEOUT)
            
            # Store cache metadata
            try:
                template_path = Path(settings.BASE_DIR) / 'templates' / 'blog' / f'{template_name}.html'
                if template_path.exists():
                    cache_meta = {
                        'file_mtime': template_path.stat().st_mtime,
                        'cached_at': time.time()
                    }
                    cache.set(f'{cache_key}:meta', cache_meta, self.CACHE_TIMEOUT)
            except Exception as e:
                logger.warning(f"Could not store cache metadata for {template_name}: {e}")
            
            logger.info(f"Parsed {template_name}: {len(result['internal_links'])} internal, {len(result['external_links'])} external links")
            return result
            
        except Exception as e:
            error_msg = f"Error parsing blog post {template_name}: {str(e)}"
            logger.error(error_msg)
            return {
                'source_post': normalized_name,
                'internal_links': [],
                'external_links': [],
                'parse_errors': [error_msg]
            }
    
    def _get_template_content(self, template_name: str) -> str:
        """Get the raw HTML content from a blog template."""
        try:
            # First try to find the template using our helper function
            template_path = find_blog_template(template_name)
            if template_path:
                return render_to_string(template_path)
            else:
                # Fallback to old direct path
                return render_to_string(f"blog/{template_name}.html")
        except Exception as e:
            logger.warning(f"Could not render template {template_name}, trying raw file: {str(e)}")
            
            # Try to find the file in any category
            all_posts = get_all_blog_posts()
            for post in all_posts:
                if post['template_name'] == template_name:
                    with open(post['full_path'], 'r', encoding='utf-8') as f:
                        return f.read()
            
            raise FileNotFoundError(f"Blog template not found: {template_name}")
    
    def _parse_html_content(self, html_content: str, source_post: str) -> Dict:
        """Parse HTML content and extract links with context."""
        result = {
            'source_post': source_post,
            'internal_links': [],
            'external_links': [],
            'parse_errors': []
        }
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script/style tags and comments
            for element in soup(["script", "style"]):
                element.decompose()
            for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
                comment.extract()
            
            links = soup.find_all('a', href=True)
            
            for link in links:
                href = link.get('href', '').strip()
                if not href or href.startswith('#'):
                    continue
                
                link_text = link.get_text(strip=True)
                context = self._extract_link_context(link)
                
                # Check link type and process accordingly
                match = self.INTERNAL_BLOG_PATTERN.search(href)
                if match:
                    # Normalize the target template name
                    target = normalize_template_name(match.group(1))
                    result['internal_links'].append({
                        'target': target,
                        'text': link_text,
                        'context': context,
                        'href': href
                    })
                elif self._is_external_link(href):
                    parsed_url = urlparse(href)
                    result['external_links'].append({
                        'url': href,
                        'text': link_text,
                        'context': context,
                        'domain': parsed_url.netloc if parsed_url.netloc else 'unknown'
                    })
                        
        except Exception as e:
            error_msg = f"Error parsing HTML content: {str(e)}"
            result['parse_errors'].append(error_msg)
            logger.error(error_msg)
        
        return result
    
    def _is_external_link(self, href: str) -> bool:
        """Check if a link is external based on URL scheme."""
        parsed = urlparse(href)
        return bool(parsed.scheme and parsed.netloc)
    
    def _extract_link_context(self, link_element) -> str:
        """Extract surrounding context for a link element."""
        try:
            parent = link_element.parent
            if not parent:
                return ""
            
            parent_text = parent.get_text()
            link_text = link_element.get_text()
            
            link_start = parent_text.find(link_text)
            if link_start == -1:
                return parent_text[:self.CONTEXT_LENGTH * 2]
            
            context_start = max(0, link_start - self.CONTEXT_LENGTH)
            context_end = min(len(parent_text), link_start + len(link_text) + self.CONTEXT_LENGTH)
            
            context = parent_text[context_start:context_end].strip()
            return re.sub(r'\s+', ' ', context)
            
        except Exception as e:
            logger.warning(f"Error extracting link context: {str(e)}")
            return ""
    
    def _is_cache_stale(self, template_name: str, cache_key: str) -> bool:
        """Check if cache is stale by comparing file modification time."""
        try:
            template_path = Path(settings.BASE_DIR) / 'templates' / 'blog' / f'{template_name}.html'
            
            if not template_path.exists():
                return True
            
            file_mtime = template_path.stat().st_mtime
            cache_meta = cache.get(f'{cache_key}:meta')
            
            if not cache_meta:
                return True
            
            if file_mtime > cache_meta.get('file_mtime', 0):
                logger.debug(f"Cache stale for {template_name}")
                return True
            
            return False
            
        except Exception as e:
            logger.warning(f"Error checking cache staleness for {template_name}: {e}")
            return True


class GraphBuilder:
    """Service for building graph data structures from parsed link data."""
    
    GRAPH_CACHE_TIMEOUT = CACHE_TIMEOUT
    SUBGRAPH_CACHE_TIMEOUT = CACHE_TIMEOUT
    EXTERNAL_NODE_ID_LENGTH = 12
    MAX_PATH_SNIPPET_LENGTH = 30
    TOP_ITEMS_LIMIT = 5
    
    def __init__(self, link_parser: LinkParser = None):
        self.link_parser = link_parser or LinkParser()
    
    def build_complete_graph(self, force_refresh: bool = False) -> Dict:
        """Build a complete knowledge graph from all blog posts."""
        cache_key = 'blog:graph:complete'
        
        if not force_refresh:
            cached_graph = cache.get(cache_key)
            if cached_graph:
                logger.debug("Using cached complete graph")
                return cached_graph
        
        try:
            blog_templates = self._get_all_blog_templates()
            
            all_links_data = []
            categories_info = {}  # Track categories and their posts
            
            for template_info in blog_templates:
                template_name = template_info['template_name']  # This is now normalized
                original_name = template_info.get('original_name', template_name)
                category = template_info['category']
                
                # Track categories with normalized names
                if category:
                    if category not in categories_info:
                        categories_info[category] = []
                    categories_info[category].append(template_name)
                
                # Parse using original name for file access, but it will be normalized internally
                links_data = self.link_parser.parse_blog_post(original_name, force_refresh)
                links_data['category'] = category  # Add category info to links data
                all_links_data.append(links_data)
            
            graph = self._build_graph_structure(all_links_data, categories_info)
            
            cache.set(cache_key, graph, self.GRAPH_CACHE_TIMEOUT)
            
            logger.info(f"Built complete graph with {len(graph['nodes'])} nodes and {len(graph['edges'])} edges")
            return graph
            
        except Exception as e:
            logger.error(f"Error building complete graph: {str(e)}")
            return {
                'nodes': [],
                'edges': [],
                'metrics': {},
                'errors': [str(e)]
            }
    
    def get_post_connections(self, template_name: str, depth: int = 1) -> Dict:
        """Get connections for a specific blog post."""
        # Normalize the template name for consistent caching and processing
        normalized_name = normalize_template_name(template_name)
        cache_key = f'blog:graph:post:{normalized_name}:depth:{depth}'
        
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        try:
            visited = set()
            to_process = [(template_name, 0)]  # Use original for file access
            all_links_data = []
            
            while to_process:
                current_template, current_depth = to_process.pop(0)
                
                # Normalize for visited tracking
                current_normalized = normalize_template_name(current_template)
                
                if current_normalized in visited or current_depth >= depth:
                    continue
                
                visited.add(current_normalized)
                
                links_data = self.link_parser.parse_blog_post(current_template)
                all_links_data.append(links_data)
                
                for link in links_data['internal_links']:
                    target = link['target']  # Already normalized in parse_blog_post
                    if target not in visited:
                        # Need to get the original template name for file access
                        # For now, we'll use the normalized name as links already point to it
                        to_process.append((target, current_depth + 1))
            
            subgraph = self._build_graph_structure(all_links_data)
            
            cache.set(cache_key, subgraph, self.SUBGRAPH_CACHE_TIMEOUT)
            
            return subgraph
            
        except Exception as e:
            logger.error(f"Error getting post connections for {template_name}: {str(e)}")
            return {
                'nodes': [],
                'edges': [],
                'metrics': {},
                'errors': [str(e)]
            }
    
    def _get_all_blog_templates(self) -> List[Dict[str, str]]:
        """Get all blog template names with their categories."""
        all_posts = get_all_blog_posts()
        blog_templates = []
        
        for post in all_posts:
            # Store both normalized and original names
            blog_templates.append({
                'template_name': normalize_template_name(post['template_name']),
                'original_name': post['template_name'],  # Keep original for file access
                'category': post['category']
            })
        
        blog_templates.sort(key=lambda x: x['template_name'])
        logger.info(f"Found {len(blog_templates)} blog templates")
        
        return blog_templates
    
    def _build_graph_structure(self, all_links_data: List[Dict], categories_info: Dict[str, List[str]] = None) -> Dict:
        """Build the graph data structure from parsed link data."""
        nodes = {}
        edges = []
        external_domains = {}
        category_metadata = {}  # Store category information for visualization
        
        # Process category information for visualization metadata
        if categories_info:
            for category, posts in categories_info.items():
                category_metadata[category] = {
                    'name': category.replace('_', ' ').title(),
                    'posts': posts,
                    'count': len(posts)
                }
        
        for links_data in all_links_data:
            source_post = links_data['source_post']
            category = links_data.get('category')
            
            # Create source node with category information
            self._ensure_blog_node(nodes, source_post)
            
            # Add category information to the node
            if category:
                nodes[source_post]['category'] = category
                nodes[source_post]['category_name'] = category.replace('_', ' ').title()
            
            # Process internal links
            edges.extend(self._process_internal_links(nodes, links_data, source_post))
            
            # Process external links
            edges.extend(self._process_external_links(nodes, links_data, source_post, external_domains))
        
        metrics = self._calculate_graph_metrics(nodes, edges, external_domains)
        
        return {
            'nodes': list(nodes.values()),
            'edges': edges,
            'metrics': metrics,
            'external_domains': external_domains,
            'categories': category_metadata,  # Add category metadata for visualization
            'errors': []
        }
    
    def _ensure_blog_node(self, nodes: Dict, post_id: str) -> None:
        """Ensure a blog post node exists in the nodes dictionary."""
        if post_id not in nodes:
            nodes[post_id] = {
                'id': post_id,
                'label': self._get_post_title(post_id),
                'type': 'blog_post',
                'in_degree': 0,
                'out_degree': 0,
                'total_links': 0,
                'category': None,  # Will be filled in later if applicable
                'category_name': None
            }
    
    def _process_internal_links(self, nodes: Dict, links_data: Dict, source_post: str) -> List[Dict]:
        """Process internal links and return edges."""
        edges = []
        
        for link in links_data['internal_links']:
            target = link['target']
            
            self._ensure_blog_node(nodes, target)
            
            edges.append({
                'source': source_post,
                'target': target,
                'type': 'internal',
                'text': link['text'],
                'context': link['context']
            })
            
            nodes[source_post]['out_degree'] += 1
            nodes[target]['in_degree'] += 1
        
        return edges
    
    def _process_external_links(self, nodes: Dict, links_data: Dict, source_post: str, external_domains: Dict) -> List[Dict]:
        """Process external links and return edges."""
        edges = []
        
        for link in links_data['external_links']:
            domain = link['domain']
            url = link['url']
            
            external_node_id = f"external_{hashlib.md5(url.encode()).hexdigest()[:self.EXTERNAL_NODE_ID_LENGTH]}"
            
            if external_node_id not in nodes:
                nodes[external_node_id] = self._create_external_node(url, domain, external_node_id)
            
            edges.append({
                'source': source_post,
                'target': external_node_id,
                'type': 'external',
                'text': link['text'],
                'context': link['context']
            })
            
            nodes[source_post]['out_degree'] += 1
            nodes[external_node_id]['in_degree'] += 1
            
            if url not in external_domains:
                external_domains[url] = 0
            external_domains[url] += 1
            
            nodes[source_post]['total_links'] += 1
        
        return edges
    
    def _create_external_node(self, url: str, domain: str, node_id: str) -> Dict:
        """Create an external link node."""
        parsed_url = urlparse(url)
        path_snippet = parsed_url.path[:self.MAX_PATH_SNIPPET_LENGTH] if parsed_url.path and parsed_url.path != '/' else ''
        
        if path_snippet and len(parsed_url.path) > self.MAX_PATH_SNIPPET_LENGTH:
            path_snippet += '...'
        
        label = f"{domain}{path_snippet}" if path_snippet else domain
        
        return {
            'id': node_id,
            'label': label,
            'type': 'external_link',
            'url': url,
            'domain': domain,
            'in_degree': 0,
            'out_degree': 0,
            'total_links': 0
        }
    
    def _get_post_title(self, template_name: str) -> str:
        """Get a readable title for a blog post from its template name."""
        try:
            # Try to get the blog data with category information
            all_posts = get_all_blog_posts()
            category = None
            for post in all_posts:
                if post['template_name'] == template_name:
                    category = post['category']
                    break
            
            blog_data = get_blog_from_template_name(template_name, load_content=False, category=category)
            return blog_data['blog_title']
        except Exception:
            return template_name.replace('_', ' ')  # Preserve original case from filename
    
    def _calculate_graph_metrics(self, nodes: Dict, edges: List[Dict], external_domains: Dict) -> Dict:
        """Calculate various graph metrics."""
        blog_nodes = [n for n in nodes.values() if n['type'] == 'blog_post']
        total_posts = len(blog_nodes)
        total_internal_links = len([edge for edge in edges if edge['type'] == 'internal'])
        total_external_links = sum(external_domains.values())
        
        # Most connected posts
        most_linked_posts = sorted(
            blog_nodes,
            key=lambda x: x['in_degree'] + x['out_degree'],
            reverse=True
        )[:self.TOP_ITEMS_LIMIT]
        
        # Orphan posts
        orphan_posts = [
            n for n in blog_nodes 
            if n['in_degree'] == 0 and n['out_degree'] == 0
        ]
        
        # Top external domains
        domain_counts = {}
        for url, count in external_domains.items():
            domain = urlparse(url).netloc
            if domain not in domain_counts:
                domain_counts[domain] = 0
            domain_counts[domain] += count
        
        top_external_domains = sorted(
            domain_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:self.TOP_ITEMS_LIMIT]
        
        return {
            'total_posts': total_posts,
            'total_internal_links': total_internal_links,
            'total_external_links': total_external_links,
            'average_links_per_post': round(total_internal_links / total_posts, 2) if total_posts > 0 else 0,
            'most_linked_posts': [{'id': p['id'], 'label': p['label'], 'connections': p['in_degree'] + p['out_degree']} for p in most_linked_posts],
            'orphan_posts': [{'id': p['id'], 'label': p['label']} for p in orphan_posts],
            'top_external_domains': [{'domain': d, 'count': c} for d, c in top_external_domains]
        }


# Utility functions for easy access
def parse_all_blog_posts(force_refresh: bool = False) -> List[Dict]:
    """Parse all blog posts and return their link data."""
    graph_builder = GraphBuilder()
    blog_templates = graph_builder._get_all_blog_templates()
    
    all_links_data = []
    for template_info in blog_templates:
        # Use original name for file access
        original_name = template_info.get('original_name', template_info['template_name'])
        links_data = graph_builder.link_parser.parse_blog_post(original_name, force_refresh)
        all_links_data.append(links_data)
    
    return all_links_data


def build_knowledge_graph(force_refresh: bool = False) -> Dict:
    """Build the complete knowledge graph."""
    graph_builder = GraphBuilder()
    return graph_builder.build_complete_graph(force_refresh)


def get_post_graph(template_name: str, depth: int = 1) -> Dict:
    """Get graph data for a specific blog post and its connections."""
    graph_builder = GraphBuilder()
    return graph_builder.get_post_connections(template_name, depth)