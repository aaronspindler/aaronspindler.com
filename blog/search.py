"""
Search utilities for blog posts, projects, and other content.
Provides full-text search.
"""

from blog.utils import get_all_blog_posts, get_blog_from_template_name
from pages.utils import get_books


def search_blog_posts(query=None, category=None):
    """
    Search blog posts by query string and/or category.

    Args:
        query: Search query string (searches titles and content)
        category: Blog category to filter by

    Returns:
        List of blog post dicts with metadata
    """
    all_posts = get_all_blog_posts()
    results = []

    for post_info in all_posts:
        template_name = post_info["template_name"]
        post_category = post_info["category"]

        # Category filter
        if category and post_category != category:
            continue

        # Get blog data
        try:
            blog_data = get_blog_from_template_name(
                template_name,
                load_content=bool(query),  # Only load content if searching text
                category=post_category,
            )
        except Exception:
            continue

        # Text search filter
        if query:
            query_lower = query.lower()
            title_match = query_lower in blog_data["blog_title"].lower()
            content_match = query_lower in blog_data["blog_content"].lower()

            if not (title_match or content_match):
                continue

        results.append(blog_data)

    # Sort by entry number (newest first)
    results.sort(key=lambda x: x["entry_number"], reverse=True)
    return results


def search_projects(query=None):
    """
    Search projects by query string.

    Args:
        query: Search query string (searches name and description)

    Returns:
        List of project dicts
    """
    # Get projects from the home view (hardcoded list)
    # In a real implementation, projects should be in a database
    projects = [
        {
            "name": "Team Bio",
            "description": "Team Bio is a platform to foster professional connections between coworkers within a company. This is done with profiles, trivia, coffee chats, and more.",
            "link": "https://github.com/aaronspindler/Team.Bio",
            "tech": ["Python", "Django", "PostgreSQL", "HTML", "JavaScript"],
        },
        {
            "name": "ActionsUptime",
            "description": "ActionsUptime is a platform to help you monitor your GitHub Actions and get notifications when they fail.",
            "tech": ["Django", "PostgreSQL", "Celery", "Redis"],
        },
        {
            "name": "Poseidon",
            "description": "Poseidon is a tool to help explore financial data, generate insights, and make trading decisions.",
            "link": "https://github.com/aaronspindler/Poseidon",
            "tech": [
                "Python",
                "Django",
                "PostgreSQL",
                "C#",
                "Prophet",
                "Various ML/AI models",
            ],
        },
        {
            "name": "Spindlers",
            "description": "Spindlers is a full service technology consulting company, specializing in custom software solutions, web development, and bringing small/medium businesses into the digital age.",
            "link": "https://spindlers.ca",
            "tech": [
                "Software Development",
                "Web Design",
                "Graphic Design",
                "SEO",
                "Marketing",
                "Consulting",
            ],
        },
        {
            "name": "iMessageLLM",
            "description": "iMessageLLM brings the power of large language models directly to your iMessage conversations, understand context, summarize years of message history, and extract key insights.",
            "link": "https://github.com/aaronspindler/iMessageLLM",
            "tech": ["Python", "LLMs", "Data Analysis", "iMessage"],
        },
        {
            "name": "Lightroom Blur",
            "description": "Clean up unintentionally blurry and duplicate photos in Lightroom and Apple Photos automatically with AI-powered image classification and blur detection.",
            "link": "https://github.com/aaronspindler/lightroom",
            "tech": [
                "Python",
                "Image Processing",
                "Machine Learning",
                "Blur Detection",
                "Apple Photos",
                "Lightroom",
            ],
        },
    ]

    results = []

    for project in projects:
        # Text search
        if query:
            query_lower = query.lower()
            name_match = query_lower in project["name"].lower()
            desc_match = query_lower in project["description"].lower()

            if not (name_match or desc_match):
                continue

        results.append(project)

    return results


def search_books(query=None):
    """
    Search books by query string.

    Args:
        query: Search query string (searches name, author, and quote)

    Returns:
        List of book dicts
    """
    try:
        all_books = get_books()
    except Exception:
        return []

    if not query:
        return all_books

    results = []
    query_lower = query.lower()

    for book in all_books:
        name_match = query_lower in book.get("name", "").lower()
        author_match = query_lower in book.get("author", "").lower()
        quote_match = query_lower in book.get("favourite_quote", "").lower()

        if name_match or author_match or quote_match:
            results.append(book)

    return results
