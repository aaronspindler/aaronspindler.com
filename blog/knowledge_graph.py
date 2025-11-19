import logging
import re
import time
from pathlib import Path
from typing import Dict, List

from bs4 import BeautifulSoup, Comment
from django.core.cache import cache
from django.template.loader import render_to_string

from blog.utils import get_all_blog_posts, get_blog_from_template_name

logger = logging.getLogger(__name__)

CACHE_TIMEOUT = 1200  # 20 minutes


def normalize_template_name(template_name: str) -> str:
    """
    Normalize template names to lowercase for consistency.

    This prevents duplicate nodes in the graph caused by case differences
    between filesystem names and URL paths (e.g., "About_Me" vs "about_me").

    Args:
        template_name: The template name to normalize

    Returns:
        Lowercase version of the template name
    """
    return template_name.lower() if template_name else template_name


class LinkParser:
    """
    Service for parsing blog posts to extract internal links.

    This parser identifies links within blog content that point to other
    blog posts and extracts surrounding context for graph visualization.
    """

    INTERNAL_BLOG_PATTERN = re.compile(r"/b/(?:[^/]+/)?(\d{4}_[^/]+)/?")
    CACHE_TIMEOUT = CACHE_TIMEOUT
    CONTEXT_LENGTH = 100  # Characters of context to extract around each link

    def __init__(self, base_url: str = ""):
        self.base_url = base_url.rstrip("/")

    def parse_blog_post(self, template_name: str, force_refresh: bool = False) -> Dict:
        """
        Parse a blog post template and extract all links with their context.

        This method handles caching intelligently - it checks if the file has
        been modified since the last parse and only re-parses if necessary.

        Args:
            template_name: Name of the blog template to parse
            force_refresh: If True, bypass cache and force re-parsing

        Returns:
            Dict containing internal_links and any parse_errors
        """
        normalized_name = normalize_template_name(template_name)
        cache_key = f"blog:links:{normalized_name}"

        # Use cached result if available and not stale
        if not force_refresh and not self._is_cache_stale(template_name, cache_key):
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.debug(f"Using cached link data for {template_name}")
                return cached_result

        try:
            html_content = self._get_template_content(template_name)
            result = self._parse_html_content(html_content, template_name, normalized_name)

            # Cache the parsed result
            cache.set(cache_key, result, self.CACHE_TIMEOUT)

            # Store file modification time for cache staleness checking
            try:
                # Find the template path using get_all_blog_posts
                all_posts = get_all_blog_posts()
                template_path = None
                for post in all_posts:
                    if post["template_name"] == template_name:
                        template_path = Path(post["full_path"])
                        break

                if template_path and template_path.exists():
                    cache_meta = {
                        "file_mtime": template_path.stat().st_mtime,
                        "cached_at": time.time(),
                    }
                    cache.set(f"{cache_key}:meta", cache_meta, self.CACHE_TIMEOUT)
            except Exception as e:
                logger.warning(f"Could not store cache metadata for {template_name}: {e}")

            logger.info(f"Parsed {template_name}: {len(result['internal_links'])} internal links")
            return result

        except Exception as e:
            error_msg = f"Error parsing blog post {template_name}: {str(e)}"
            logger.error(error_msg)
            return {
                "source_post": normalized_name,
                "internal_links": [],
                "parse_errors": [error_msg],
            }

    def _get_template_content(self, template_name: str) -> str:
        """
        Retrieve the raw HTML content from a blog template file.

        Finds the template using get_all_blog_posts() which provides category information.
        """
        all_posts = get_all_blog_posts()
        for post in all_posts:
            if post["template_name"] == template_name:
                try:
                    template_path = f"blog/{post['category']}/{template_name}.html"
                    return render_to_string(template_path)
                except Exception as e:
                    logger.warning(f"Could not render template {template_name}, reading raw file: {str(e)}")
                    # Read the raw file directly
                    with open(post["full_path"], "r", encoding="utf-8") as f:
                        return f.read()

        raise FileNotFoundError(f"Blog template not found: {template_name}")

    def _parse_html_content(self, html_content: str, source_post: str, source_post_normalized: str = None) -> Dict:
        """
        Extract and categorize all links from HTML content.

        This method performs the core parsing logic:
        1. Cleans the HTML (removes scripts, styles, comments)
        2. Finds all anchor tags with href attributes
        3. Identifies internal links to other blog posts
        4. Extracts surrounding text context for each link

        Args:
            html_content: Raw HTML content to parse
            source_post: Original name of the source blog post (preserves casing)
            source_post_normalized: Normalized (lowercase) name of the source blog post

        Returns:
            Dict with categorized links and any parsing errors
        """
        if source_post_normalized is None:
            source_post_normalized = normalize_template_name(source_post)

        result = {
            "source_post": source_post,
            "source_post_normalized": source_post_normalized,
            "internal_links": [],
            "parse_errors": [],
        }

        try:
            soup = BeautifulSoup(html_content, "html.parser")

            # Clean HTML by removing non-content elements
            for element in soup(["script", "style"]):
                element.decompose()
            for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
                comment.extract()

            links = soup.find_all("a", href=True)

            for link in links:
                href = link.get("href", "").strip()
                if not href or href.startswith("#"):  # Skip empty or anchor links
                    continue

                link_text = link.get_text(strip=True)
                context = self._extract_link_context(link)

                # Categorize link based on URL pattern
                match = self.INTERNAL_BLOG_PATTERN.search(href)
                if match:
                    # Internal blog link - preserve original casing when possible
                    target_raw = match.group(1)
                    target_normalized = normalize_template_name(target_raw)

                    # Try to find the original casing from all blog posts
                    target_original = target_raw  # Default to what we extracted
                    try:
                        all_posts = get_all_blog_posts()
                        for post in all_posts:
                            if normalize_template_name(post["template_name"]) == target_normalized:
                                target_original = post["template_name"]
                                break
                    except Exception:
                        pass  # Use the raw extracted value if lookup fails

                    result["internal_links"].append(
                        {
                            "target": target_original,
                            "target_normalized": target_normalized,
                            "text": link_text,
                            "context": context,
                            "href": href,
                        }
                    )

        except Exception as e:
            error_msg = f"Error parsing HTML content: {str(e)}"
            result["parse_errors"].append(error_msg)
            logger.error(error_msg)

        return result

    def _extract_link_context(self, link_element) -> str:
        """
        Extract surrounding text context for a link.

        Gets CONTEXT_LENGTH characters before and after the link to provide
        context about where and how the link appears in the content.

        Args:
            link_element: BeautifulSoup link element

        Returns:
            String containing the link text with surrounding context
        """
        try:
            parent = link_element.parent
            if not parent:
                return ""

            parent_text = parent.get_text()
            link_text = link_element.get_text()

            # Find where the link text appears in parent
            link_start = parent_text.find(link_text)
            if link_start == -1:
                return parent_text[: self.CONTEXT_LENGTH * 2]

            # Extract context window around the link
            context_start = max(0, link_start - self.CONTEXT_LENGTH)
            context_end = min(len(parent_text), link_start + len(link_text) + self.CONTEXT_LENGTH)

            # Clean up whitespace
            context = parent_text[context_start:context_end].strip()
            return re.sub(r"\s+", " ", context)

        except Exception as e:
            logger.warning(f"Error extracting link context: {str(e)}")
            return ""

    def _is_cache_stale(self, template_name: str, cache_key: str) -> bool:
        """
        Check if cached data is stale by comparing file modification times.

        Compares the actual file's modification time against the cached
        metadata to determine if the cache needs refreshing.

        Args:
            template_name: Name of the template file
            cache_key: Cache key used for this template

        Returns:
            True if cache is stale or missing, False if cache is fresh
        """
        try:
            # Find the template path using get_all_blog_posts
            all_posts = get_all_blog_posts()
            template_path = None
            for post in all_posts:
                if post["template_name"] == template_name:
                    template_path = Path(post["full_path"])
                    break

            if not template_path or not template_path.exists():
                return True

            file_mtime = template_path.stat().st_mtime
            cache_meta = cache.get(f"{cache_key}:meta")

            if not cache_meta:
                return True

            # Check if file has been modified since caching
            if file_mtime > cache_meta.get("file_mtime", 0):
                logger.debug(f"Cache stale for {template_name}")
                return True

            return False

        except Exception as e:
            logger.warning(f"Error checking cache staleness for {template_name}: {e}")
            return True  # Assume stale on error


class GraphBuilder:
    """
    Service for constructing graph data structures from parsed blog links.

    This builder creates two types of graphs:
    1. Complete graph - all blog posts and their interconnections
    2. Post-specific subgraphs - connections for a single post at various depths
    """

    GRAPH_CACHE_TIMEOUT = CACHE_TIMEOUT
    SUBGRAPH_CACHE_TIMEOUT = CACHE_TIMEOUT
    TOP_ITEMS_LIMIT = 5  # Number of top items to show in metrics

    def __init__(self, link_parser: LinkParser = None):
        self.link_parser = link_parser or LinkParser()

    def build_complete_graph(self, force_refresh: bool = False) -> Dict:
        """
        Build the complete knowledge graph containing all blog posts.

        This method:
        1. Collects all blog templates across categories
        2. Parses each template to extract links
        3. Builds a graph structure with nodes (posts) and edges (links)
        4. Calculates metrics like most connected posts and orphans
        5. Caches the result for performance

        Args:
            force_refresh: If True, rebuild graph even if cached

        Returns:
            Dict containing nodes, edges, metrics, categories, and any errors
        """
        cache_key = "blog:graph:complete"

        if not force_refresh:
            cached_graph = cache.get(cache_key)
            if cached_graph:
                logger.debug("Using cached complete graph")
                return cached_graph

        try:
            blog_templates = self._get_all_blog_templates()

            all_links_data = []
            categories_info = {}  # Track which posts belong to which categories

            for template_info in blog_templates:
                template_name = template_info["template_name"]  # Normalized version
                original_name = template_info.get("original_name", template_name)
                category = template_info["category"]

                # Build category mapping - use original name to preserve casing
                if category:
                    if category not in categories_info:
                        categories_info[category] = []
                    categories_info[category].append(original_name)

                # Parse each blog post for links
                links_data = self.link_parser.parse_blog_post(original_name, force_refresh)
                links_data["category"] = category
                all_links_data.append(links_data)

            graph = self._build_graph_structure(all_links_data, categories_info)

            cache.set(cache_key, graph, self.GRAPH_CACHE_TIMEOUT)

            logger.info(f"Built complete graph with {len(graph['nodes'])} nodes and {len(graph['edges'])} edges")
            return graph

        except Exception as e:
            logger.error(f"Error building complete graph: {str(e)}", exc_info=True)
            return {
                "nodes": [],
                "edges": [],
                "metrics": {},
                "errors": ["A server error occurred while building the knowledge graph."],
            }

    def get_post_connections(self, template_name: str, depth: int = 1) -> Dict:
        """Get connections for a specific blog post."""
        # Normalize the template name for consistent caching and processing
        normalized_name = normalize_template_name(template_name)
        cache_key = f"blog:graph:post:{normalized_name}:depth:{depth}"

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

                for link in links_data["internal_links"]:
                    target = link["target"]  # Already normalized in parse_blog_post
                    if target not in visited:
                        # Need to get the original template name for file access
                        # For now, we'll use the normalized name as links already point to it
                        to_process.append((target, current_depth + 1))

            subgraph = self._build_graph_structure(all_links_data)

            cache.set(cache_key, subgraph, self.SUBGRAPH_CACHE_TIMEOUT)

            return subgraph

        except Exception as e:
            # Sanitize template_name to prevent log injection
            safe_template_name = str(template_name).replace("\n", "").replace("\r", "")[:100]
            logger.error(f"Error getting post connections for {safe_template_name}: {str(e)}", exc_info=True)
            return {
                "nodes": [],
                "edges": [],
                "metrics": {},
                "errors": ["A server error occurred while getting post connections."],
            }

    def _get_all_blog_templates(self) -> List[Dict[str, str]]:
        """Get all blog template names with their categories."""
        all_posts = get_all_blog_posts()
        blog_templates = []

        for post in all_posts:
            # Store both normalized and original names
            blog_templates.append(
                {
                    "template_name": normalize_template_name(post["template_name"]),
                    "original_name": post["template_name"],  # Keep original for file access
                    "category": post["category"],
                }
            )

        blog_templates.sort(key=lambda x: x["template_name"])
        logger.info(f"Found {len(blog_templates)} blog templates")

        return blog_templates

    def _build_graph_structure(self, all_links_data: List[Dict], categories_info: Dict[str, List[str]] = None) -> Dict:
        """Build the graph data structure from parsed link data."""
        nodes = {}
        edges = []
        category_metadata = {}  # Store category information for visualization

        # Process category information for visualization metadata
        if categories_info:
            for category, posts in categories_info.items():
                category_metadata[category] = {
                    "name": category.replace("_", " ").title(),
                    "posts": posts,
                    "count": len(posts),
                }

        for links_data in all_links_data:
            source_post = links_data["source_post"]
            category = links_data.get("category")

            # Create source node with category information
            self._ensure_blog_node(nodes, source_post)

            # Add category information to the node
            if category:
                nodes[source_post]["category"] = category
                nodes[source_post]["category_name"] = category.replace("_", " ").title()

            # Process internal links
            edges.extend(self._process_internal_links(nodes, links_data, source_post))

        metrics = self._calculate_graph_metrics(nodes, edges)

        return {
            "nodes": list(nodes.values()),
            "edges": edges,
            "metrics": metrics,
            "categories": category_metadata,  # Add category metadata for visualization
            "errors": [],
        }

    def _ensure_blog_node(self, nodes: Dict, post_id: str) -> None:
        """Ensure a blog post node exists in the nodes dictionary."""
        if post_id not in nodes:
            nodes[post_id] = {
                "id": post_id,
                "label": self._get_post_title(post_id),
                "type": "blog_post",
                "in_degree": 0,
                "out_degree": 0,
                "total_links": 0,
                "category": None,  # Will be filled in later if applicable
                "category_name": None,
            }

    def _process_internal_links(self, nodes: Dict, links_data: Dict, source_post: str) -> List[Dict]:
        """Process internal links and return edges."""
        edges = []

        for link in links_data["internal_links"]:
            target = link["target"]

            self._ensure_blog_node(nodes, target)

            edges.append(
                {
                    "source": source_post,
                    "target": target,
                    "type": "internal",
                    "text": link["text"],
                    "context": link["context"],
                }
            )

            nodes[source_post]["out_degree"] += 1
            nodes[target]["in_degree"] += 1

        return edges

    def _get_post_title(self, template_name: str) -> str:
        """
        Get a readable title for a blog post from its template name.

        Preserves the original casing from the filename.
        """
        all_posts = get_all_blog_posts()
        normalized_input = normalize_template_name(template_name)

        # Find exact match by comparing normalized versions
        for post in all_posts:
            if normalize_template_name(post["template_name"]) == normalized_input:
                try:
                    blog_data = get_blog_from_template_name(
                        post["template_name"],
                        load_content=False,
                        category=post["category"],
                    )
                    return blog_data["blog_title"]
                except Exception:
                    # If template can't be loaded, fall back to filename-based title
                    return post["template_name"].replace("_", " ")

        # Fallback: convert underscores to spaces (preserves whatever casing was provided)
        return template_name.replace("_", " ")

    def _calculate_graph_metrics(self, nodes: Dict, edges: List[Dict]) -> Dict:
        """Calculate various graph metrics."""
        blog_nodes = [n for n in nodes.values() if n["type"] == "blog_post"]
        total_posts = len(blog_nodes)
        total_internal_links = len([edge for edge in edges if edge["type"] == "internal"])

        # Most connected posts
        most_linked_posts = sorted(blog_nodes, key=lambda x: x["in_degree"] + x["out_degree"], reverse=True)[
            : self.TOP_ITEMS_LIMIT
        ]

        # Orphan posts
        orphan_posts = [n for n in blog_nodes if n["in_degree"] == 0 and n["out_degree"] == 0]

        return {
            "total_posts": total_posts,
            "total_internal_links": total_internal_links,
            "average_links_per_post": (round(total_internal_links / total_posts, 2) if total_posts > 0 else 0),
            "most_linked_posts": [
                {
                    "id": p["id"],
                    "label": p["label"],
                    "connections": p["in_degree"] + p["out_degree"],
                }
                for p in most_linked_posts
            ],
            "orphan_posts": [{"id": p["id"], "label": p["label"]} for p in orphan_posts],
        }


# Utility functions for easy access
def parse_all_blog_posts(force_refresh: bool = False) -> List[Dict]:
    """Parse all blog posts and return their link data."""
    graph_builder = GraphBuilder()
    blog_templates = graph_builder._get_all_blog_templates()

    all_links_data = []
    for template_info in blog_templates:
        # Use original name for file access
        original_name = template_info.get("original_name", template_info["template_name"])
        links_data = graph_builder.link_parser.parse_blog_post(original_name, force_refresh)
        all_links_data.append(links_data)

    return all_links_data


def build_knowledge_graph(force_refresh: bool = False) -> Dict:
    """Build the complete knowledge graph."""
    graph_builder = GraphBuilder()
    return graph_builder.build_complete_graph(force_refresh=force_refresh)


def get_post_graph(template_name: str, depth: int = 1) -> Dict:
    """Get graph data for a specific blog post and its connections."""
    graph_builder = GraphBuilder()
    return graph_builder.get_post_connections(template_name, depth)
