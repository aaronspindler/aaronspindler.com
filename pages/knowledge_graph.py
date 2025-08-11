import os
import re
import time
import logging
from typing import Dict, List, Optional, Union
from urllib.parse import urljoin, urlparse
from pathlib import Path

from bs4 import BeautifulSoup, Comment
from django.conf import settings
from django.core.cache import cache
from django.template.loader import render_to_string
from django.template import Template, Context

from .utils import get_blog_from_template_name

logger = logging.getLogger(__name__)


class LinkParser:
    """
    Service for parsing HTML content and extracting links from blog posts.
    Identifies internal blog post links vs external links with context.
    """
    
    # Pattern to match internal blog links: /b/NNNN_*
    INTERNAL_BLOG_PATTERN = re.compile(r'/b/(\d{4}_[^/]+)/?')
    
    # Cache timeout in seconds (24 hours)
    CACHE_TIMEOUT = 86400
    
    def __init__(self, base_url: str = ''):
        """
        Initialize the LinkParser.
        
        Args:
            base_url: Base URL for the site (used for relative link resolution)
        """
        self.base_url = base_url.rstrip('/')
        
    def parse_blog_post(self, template_name: str, force_refresh: bool = False) -> Dict:
        """
        Parse a single blog post and extract all links with context.
        
        Args:
            template_name: The template name (e.g., '0001_what_even_is_this?')
            force_refresh: If True, bypass cache and re-parse
            
        Returns:
            Dictionary containing parsed link data:
            {
                'source_post': str,
                'internal_links': List[Dict],
                'external_links': List[Dict],
                'parse_errors': List[str]
            }
        """
        cache_key = f'blog:links:{template_name}'
        
        logger.info(f"[DEBUG] parse_blog_post called for: {template_name}, force_refresh={force_refresh}")
        
        # Check if we need to refresh based on file modification time
        if not force_refresh and not self._is_cache_stale(template_name, cache_key):
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.debug(f"Using cached link data for {template_name}")
                logger.info(f"[DEBUG] Cached result found: {len(cached_result.get('internal_links', []))} internal links")
                return cached_result
        
        try:
            # Get the raw HTML content from the template
            html_content = self._get_template_content(template_name)
            logger.info(f"[DEBUG] Got HTML content for {template_name}, length: {len(html_content)}")
            
            # Parse the HTML and extract links
            result = self._parse_html_content(html_content, template_name)
            logger.info(f"[DEBUG] Parsed {template_name}: {len(result['internal_links'])} internal, {len(result['external_links'])} external links")
            
            # Cache the result with metadata
            cache.set(cache_key, result, self.CACHE_TIMEOUT)
            
            # Store cache metadata including file modification time
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
                'source_post': template_name,
                'internal_links': [],
                'external_links': [],
                'parse_errors': [error_msg]
            }
    
    def _get_template_content(self, template_name: str) -> str:
        """
        Get the raw HTML content from a blog template.
        
        Args:
            template_name: The template name
            
        Returns:
            Raw HTML content as string
            
        Raises:
            FileNotFoundError: If template file doesn't exist
        """
        try:
            # First try to render the template (handles Django template tags)
            html_content = render_to_string(f"blog/{template_name}.html")
            return html_content
        except Exception as e:
            logger.warning(f"Could not render template {template_name}, trying raw file: {str(e)}")
            
            # Fallback: read raw file content
            template_path = os.path.join(settings.BASE_DIR, 'templates', 'blog', f'{template_name}.html')
            if not os.path.exists(template_path):
                raise FileNotFoundError(f"Blog template not found: {template_name}")
            
            with open(template_path, 'r', encoding='utf-8') as f:
                return f.read()
    
    def _parse_html_content(self, html_content: str, source_post: str) -> Dict:
        """
        Parse HTML content and extract links with context.
        
        Args:
            html_content: The HTML content to parse
            source_post: The source blog post name
            
        Returns:
            Dictionary with parsed link data
        """
        result = {
            'source_post': source_post,
            'internal_links': [],
            'external_links': [],
            'parse_errors': []
        }
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove comments and script/style tags that might interfere
            for element in soup(["script", "style"]):
                element.decompose()
            for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
                comment.extract()
            
            # Find all anchor tags with href attributes
            links = soup.find_all('a', href=True)
            logger.info(f"[DEBUG] Found {len(links)} total links in {source_post}")
            
            for link in links:
                href = link.get('href', '').strip()
                if not href or href.startswith('#'):  # Skip empty links and fragments
                    continue
                
                link_text = link.get_text(strip=True)
                context = self._extract_link_context(link)
                
                logger.debug(f"[DEBUG] Processing link: href='{href}', text='{link_text}'")
                
                if self._is_internal_blog_link(href):
                    # Extract template name from internal link
                    match = self.INTERNAL_BLOG_PATTERN.search(href)
                    logger.debug(f"[DEBUG] Internal blog link detected: {href}, pattern match: {match}")
                    if match:
                        target_template = match.group(1)
                        logger.info(f"[DEBUG] Extracted target template: {target_template}")
                        result['internal_links'].append({
                            'target': target_template,
                            'text': link_text,
                            'context': context,
                            'href': href
                        })
                elif self._is_external_link(href):
                    # Parse external link
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
    
    def _is_internal_blog_link(self, href: str) -> bool:
        """
        Check if a link is an internal blog post link.
        
        Args:
            href: The href attribute value
            
        Returns:
            True if it's an internal blog link
        """
        is_match = bool(self.INTERNAL_BLOG_PATTERN.search(href))
        logger.debug(f"[DEBUG] _is_internal_blog_link: href='{href}', pattern='{self.INTERNAL_BLOG_PATTERN.pattern}', match={is_match}")
        return is_match
    
    def _is_external_link(self, href: str) -> bool:
        """
        Check if a link is an external link.
        
        Args:
            href: The href attribute value
            
        Returns:
            True if it's an external link
        """
        # Check if it's a full URL (has scheme)
        parsed = urlparse(href)
        return bool(parsed.scheme and parsed.netloc)
    
    def _extract_link_context(self, link_element, context_length: int = 100) -> str:
        """
        Extract surrounding context for a link element.
        
        Args:
            link_element: BeautifulSoup element for the link
            context_length: Maximum length of context to extract (per side)
            
        Returns:
            String containing surrounding context
        """
        try:
            # Get the parent element's text
            parent = link_element.parent
            if not parent:
                return ""
            
            parent_text = parent.get_text()
            link_text = link_element.get_text()
            
            # Find the link text position in parent text
            link_start = parent_text.find(link_text)
            if link_start == -1:
                return parent_text[:context_length * 2]  # Fallback
            
            # Extract context before and after the link
            context_start = max(0, link_start - context_length)
            context_end = min(len(parent_text), link_start + len(link_text) + context_length)
            
            context = parent_text[context_start:context_end].strip()
            
            # Clean up whitespace
            context = re.sub(r'\s+', ' ', context)
            
            return context
            
        except Exception as e:
            logger.warning(f"Error extracting link context: {str(e)}")
            return ""
    
    def _is_cache_stale(self, template_name: str, cache_key: str) -> bool:
        """
        Check if cache is stale by comparing file modification time with cache timestamp.
        
        Args:
            template_name: The template name
            cache_key: The cache key to check
            
        Returns:
            True if cache is stale and should be refreshed
        """
        try:
            template_path = Path(settings.BASE_DIR) / 'templates' / 'blog' / f'{template_name}.html'
            
            if not template_path.exists():
                return True  # File doesn't exist, cache is stale
            
            file_mtime = template_path.stat().st_mtime
            
            # Get cache metadata if it exists
            cache_meta_key = f'{cache_key}:meta'
            cache_meta = cache.get(cache_meta_key)
            
            if not cache_meta:
                return True  # No cache metadata, consider stale
            
            cached_mtime = cache_meta.get('file_mtime', 0)
            
            # If file is newer than cached version, cache is stale
            if file_mtime > cached_mtime:
                logger.debug(f"Cache stale for {template_name}: file mtime {file_mtime} > cached mtime {cached_mtime}")
                return True
            
            return False
            
        except Exception as e:
            logger.warning(f"Error checking cache staleness for {template_name}: {e}")
            return True  # On error, assume stale


class GraphBuilder:
    """
    Service for building graph data structures from parsed link data.
    """
    
    def __init__(self, link_parser: LinkParser = None):
        """
        Initialize the GraphBuilder.
        
        Args:
            link_parser: LinkParser instance to use. If None, creates a new one.
        """
        self.link_parser = link_parser or LinkParser()
    
    def build_complete_graph(self, force_refresh: bool = False) -> Dict:
        """
        Build a complete knowledge graph from all blog posts.
        
        Args:
            force_refresh: If True, bypass cache and re-parse all posts
            
        Returns:
            Dictionary containing graph data with nodes and edges
        """
        cache_key = 'blog:graph:complete'
        
        if not force_refresh:
            cached_graph = cache.get(cache_key)
            if cached_graph:
                logger.debug("Using cached complete graph")
                return cached_graph
        
        try:
            # Get all blog post template names
            blog_templates = self._get_all_blog_templates()
            
            # Parse all blog posts
            all_links_data = []
            for template_name in blog_templates:
                links_data = self.link_parser.parse_blog_post(template_name, force_refresh)
                all_links_data.append(links_data)
            
            # Build graph structure
            graph = self._build_graph_structure(all_links_data)
            
            # Cache the result (shorter timeout for complete graph)
            cache.set(cache_key, graph, 3600)  # 1 hour
            
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
        """
        Get connections for a specific blog post.
        
        Args:
            template_name: The blog post template name
            depth: How many levels of connections to include
            
        Returns:
            Dictionary with post-specific graph data
        """
        cache_key = f'blog:graph:post:{template_name}:depth:{depth}'
        
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        try:
            # Start with the target post
            visited = set()
            to_process = [(template_name, 0)]
            all_links_data = []
            
            while to_process:
                current_template, current_depth = to_process.pop(0)
                
                if current_template in visited or current_depth >= depth:
                    continue
                
                visited.add(current_template)
                
                # Parse current post
                links_data = self.link_parser.parse_blog_post(current_template)
                all_links_data.append(links_data)
                
                # Add connected posts to processing queue
                for link in links_data['internal_links']:
                    target = link['target']
                    if target not in visited:
                        to_process.append((target, current_depth + 1))
            
            # Build subgraph
            subgraph = self._build_graph_structure(all_links_data)
            
            # Cache result
            cache.set(cache_key, subgraph, 1800)  # 30 minutes
            
            return subgraph
            
        except Exception as e:
            logger.error(f"Error getting post connections for {template_name}: {str(e)}")
            return {
                'nodes': [],
                'edges': [],
                'metrics': {},
                'errors': [str(e)]
            }
    
    def _get_all_blog_templates(self) -> List[str]:
        """
        Get all blog template names by scanning the templates/blog directory.
        
        Returns:
            List of template names (without .html extension)
        """
        blog_templates = []
        blog_dir = os.path.join(settings.BASE_DIR, 'templates', 'blog')
        
        if not os.path.exists(blog_dir):
            logger.warning(f"Blog templates directory not found: {blog_dir}")
            return []
        
        for filename in os.listdir(blog_dir):
            if filename.endswith('.html'):
                template_name = filename[:-5]  # Remove .html extension
                blog_templates.append(template_name)
        
        # Sort by entry number (assuming NNNN_ pattern)
        blog_templates.sort()
        logger.info(f"Found {len(blog_templates)} blog templates")
        
        return blog_templates
    
    def _build_graph_structure(self, all_links_data: List[Dict]) -> Dict:
        """
        Build the graph data structure from parsed link data.
        
        Args:
            all_links_data: List of parsed link data dictionaries
            
        Returns:
            Graph structure with nodes, edges, and metrics
        """
        nodes = {}
        edges = []
        external_domains = {}
        
        # Process each blog post's links
        for links_data in all_links_data:
            source_post = links_data['source_post']
            
            # Add source post as a node
            if source_post not in nodes:
                nodes[source_post] = {
                    'id': source_post,
                    'label': self._get_post_title(source_post),
                    'type': 'blog_post',
                    'in_degree': 0,
                    'out_degree': 0,
                    'total_links': 0
                }
            
            # Process internal links
            for link in links_data['internal_links']:
                target = link['target']
                
                # Add target as node if it doesn't exist
                if target not in nodes:
                    nodes[target] = {
                        'id': target,
                        'label': self._get_post_title(target),
                        'type': 'blog_post',
                        'in_degree': 0,
                        'out_degree': 0,
                        'total_links': 0
                    }
                
                # Add edge
                edges.append({
                    'source': source_post,
                    'target': target,
                    'type': 'internal',
                    'text': link['text'],
                    'context': link['context']
                })
                
                # Update degrees
                nodes[source_post]['out_degree'] += 1
                nodes[target]['in_degree'] += 1
            
            # Process external links - add them as nodes and edges
            for link in links_data['external_links']:
                domain = link['domain']
                external_node_id = f"external_{domain}"
                
                # Add external domain as a node if it doesn't exist
                if external_node_id not in nodes:
                    nodes[external_node_id] = {
                        'id': external_node_id,
                        'label': domain,
                        'type': 'external_link',
                        'url': link['url'],
                        'domain': domain,
                        'in_degree': 0,
                        'out_degree': 0,
                        'total_links': 0
                    }
                
                # Add edge from blog post to external link
                edges.append({
                    'source': source_post,
                    'target': external_node_id,
                    'type': 'external',
                    'text': link['text'],
                    'context': link['context']
                })
                
                # Update degrees
                nodes[source_post]['out_degree'] += 1
                nodes[external_node_id]['in_degree'] += 1
                
                # Track domain counts for metrics
                if domain not in external_domains:
                    external_domains[domain] = 0
                external_domains[domain] += 1
                
                nodes[source_post]['total_links'] += 1
        
        # Calculate final metrics
        metrics = self._calculate_graph_metrics(nodes, edges, external_domains)
        
        return {
            'nodes': list(nodes.values()),
            'edges': edges,
            'metrics': metrics,
            'external_domains': external_domains,
            'errors': []
        }
    
    def _get_post_title(self, template_name: str) -> str:
        """
        Get a readable title for a blog post from its template name.
        
        Args:
            template_name: The template name
            
        Returns:
            Human-readable title
        """
        try:
            # Use the existing utility function
            blog_data = get_blog_from_template_name(template_name, load_content=False)
            return blog_data['blog_title']
        except Exception:
            # Fallback: clean up the template name
            return template_name.replace('_', ' ').title()
    
    def _calculate_graph_metrics(self, nodes: Dict, edges: List[Dict], external_domains: Dict) -> Dict:
        """
        Calculate various graph metrics.
        
        Args:
            nodes: Dictionary of graph nodes
            edges: List of graph edges
            external_domains: Dictionary of external domain counts
            
        Returns:
            Dictionary containing calculated metrics
        """
        total_posts = len([n for n in nodes.values() if n['type'] == 'blog_post'])
        total_internal_links = len(edges)
        total_external_links = sum(external_domains.values())
        
        # Find most connected posts
        most_linked_posts = sorted(
            [n for n in nodes.values() if n['type'] == 'blog_post'],
            key=lambda x: x['in_degree'] + x['out_degree'],
            reverse=True
        )[:5]
        
        # Find orphan posts (no connections)
        orphan_posts = [
            n for n in nodes.values() 
            if n['type'] == 'blog_post' and n['in_degree'] == 0 and n['out_degree'] == 0
        ]
        
        # Most referenced external domains
        top_external_domains = sorted(
            external_domains.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
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
    """
    Parse all blog posts and return their link data.
    
    Args:
        force_refresh: If True, bypass cache and re-parse all posts
        
    Returns:
        List of parsed link data dictionaries
    """
    graph_builder = GraphBuilder()
    blog_templates = graph_builder._get_all_blog_templates()
    
    all_links_data = []
    for template_name in blog_templates:
        links_data = graph_builder.link_parser.parse_blog_post(template_name, force_refresh)
        all_links_data.append(links_data)
    
    return all_links_data


def build_knowledge_graph(force_refresh: bool = False) -> Dict:
    """
    Build the complete knowledge graph.
    
    Args:
        force_refresh: If True, bypass cache and rebuild from scratch
        
    Returns:
        Complete graph data structure
    """
    graph_builder = GraphBuilder()
    return graph_builder.build_complete_graph(force_refresh)


def get_post_graph(template_name: str, depth: int = 1) -> Dict:
    """
    Get graph data for a specific blog post and its connections.
    
    Args:
        template_name: The blog post template name
        depth: How many levels of connections to include
        
    Returns:
        Post-specific graph data
    """
    graph_builder = GraphBuilder()
    return graph_builder.get_post_connections(template_name, depth)


