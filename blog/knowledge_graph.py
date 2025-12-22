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
    return template_name.lower() if template_name else template_name


class LinkParser:
    INTERNAL_BLOG_PATTERN = re.compile(r"/b/(?:[^/]+/)?(\d{4}_[^/]+)/?")
    CACHE_TIMEOUT = CACHE_TIMEOUT
    CONTEXT_LENGTH = 100  # Characters of context to extract around each link

    def __init__(self, base_url: str = ""):
        self.base_url = base_url.rstrip("/")

    def parse_blog_post(self, template_name: str, force_refresh: bool = False) -> Dict:
        normalized_name = normalize_template_name(template_name)
        cache_key = f"blog:links:{normalized_name}"

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

            try:
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
        all_posts = get_all_blog_posts()
        for post in all_posts:
            if post["template_name"] == template_name:
                try:
                    template_path = f"blog/{post['category']}/{template_name}.html"
                    return render_to_string(template_path)
                except Exception as e:
                    logger.warning(f"Could not render template {template_name}, reading raw file: {str(e)}")
                    with open(post["full_path"], "r", encoding="utf-8") as f:
                        return f.read()

        raise FileNotFoundError(f"Blog template not found: {template_name}")

    def _parse_html_content(self, html_content: str, source_post: str, source_post_normalized: str = None) -> Dict:
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

                match = self.INTERNAL_BLOG_PATTERN.search(href)
                if match:
                    target_raw = match.group(1)
                    target_normalized = normalize_template_name(target_raw)

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
        try:
            parent = link_element.parent
            if not parent:
                return ""

            parent_text = parent.get_text()
            link_text = link_element.get_text()

            link_start = parent_text.find(link_text)
            if link_start == -1:
                return parent_text[: self.CONTEXT_LENGTH * 2]

            context_start = max(0, link_start - self.CONTEXT_LENGTH)
            context_end = min(len(parent_text), link_start + len(link_text) + self.CONTEXT_LENGTH)

            context = parent_text[context_start:context_end].strip()
            return re.sub(r"\s+", " ", context)

        except Exception as e:
            logger.warning(f"Error extracting link context: {str(e)}")
            return ""

    def _is_cache_stale(self, template_name: str, cache_key: str) -> bool:
        try:
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

            if file_mtime > cache_meta.get("file_mtime", 0):
                logger.debug(f"Cache stale for {template_name}")
                return True

            return False

        except Exception as e:
            logger.warning(f"Error checking cache staleness for {template_name}: {e}")
            return True  # Assume stale on error


class GraphBuilder:
    GRAPH_CACHE_TIMEOUT = CACHE_TIMEOUT
    SUBGRAPH_CACHE_TIMEOUT = CACHE_TIMEOUT
    TOP_ITEMS_LIMIT = 5  # Number of top items to show in metrics

    def __init__(self, link_parser: LinkParser = None):
        self.link_parser = link_parser or LinkParser()

    def build_complete_graph(self, force_refresh: bool = False) -> Dict:
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

                current_normalized = normalize_template_name(current_template)

                if current_normalized in visited or current_depth >= depth:
                    continue

                visited.add(current_normalized)

                links_data = self.link_parser.parse_blog_post(current_template)
                all_links_data.append(links_data)

                for link in links_data["internal_links"]:
                    target = link["target"]  # Already normalized in parse_blog_post
                    if target not in visited:
                        to_process.append((target, current_depth + 1))

            subgraph = self._build_graph_structure(all_links_data)

            cache.set(cache_key, subgraph, self.SUBGRAPH_CACHE_TIMEOUT)

            return subgraph

        except Exception as e:
            safe_template_name = str(template_name).replace("\n", "").replace("\r", "")[:100]
            logger.error(f"Error getting post connections for {safe_template_name}: {str(e)}", exc_info=True)
            return {
                "nodes": [],
                "edges": [],
                "metrics": {},
                "errors": ["A server error occurred while getting post connections."],
            }

    def _get_all_blog_templates(self) -> List[Dict[str, str]]:
        all_posts = get_all_blog_posts()
        blog_templates = []

        for post in all_posts:
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
        all_posts = get_all_blog_posts()
        normalized_input = normalize_template_name(template_name)

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
                    return post["template_name"].replace("_", " ")

        # Fallback: convert underscores to spaces (preserves whatever casing was provided)
        return template_name.replace("_", " ")

    def _calculate_graph_metrics(self, nodes: Dict, edges: List[Dict]) -> Dict:
        blog_nodes = [n for n in nodes.values() if n["type"] == "blog_post"]
        total_posts = len(blog_nodes)
        total_internal_links = len([edge for edge in edges if edge["type"] == "internal"])

        most_linked_posts = sorted(blog_nodes, key=lambda x: x["in_degree"] + x["out_degree"], reverse=True)[
            : self.TOP_ITEMS_LIMIT
        ]

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


def parse_all_blog_posts(force_refresh: bool = False) -> List[Dict]:
    graph_builder = GraphBuilder()
    blog_templates = graph_builder._get_all_blog_templates()

    all_links_data = []
    for template_info in blog_templates:
        original_name = template_info.get("original_name", template_info["template_name"])
        links_data = graph_builder.link_parser.parse_blog_post(original_name, force_refresh)
        all_links_data.append(links_data)

    return all_links_data


def build_knowledge_graph(force_refresh: bool = False) -> Dict:
    graph_builder = GraphBuilder()
    return graph_builder.build_complete_graph(force_refresh=force_refresh)


def get_post_graph(template_name: str, depth: int = 1) -> Dict:
    graph_builder = GraphBuilder()
    return graph_builder.get_post_connections(template_name, depth)
