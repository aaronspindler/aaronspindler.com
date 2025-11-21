import os

from django.conf import settings
from django.template.loader import render_to_string


def get_blog_from_template_name(template_name, load_content=True, category=None):
    """
    Get blog data from template name.

    Args:
        template_name: Name of the blog template (without .html extension)
        load_content: Whether to render the template content (False for metadata only)
        category: Category of the blog post (required)

    Returns:
        Dict with blog metadata including title, content, category, and GitHub link
    """
    if not category:
        raise ValueError("Category is required for blog posts")

    entry_number = template_name.split("_")[0]
    blog_title = template_name.replace("_", " ")  # Preserve original case from filename

    template_path = f"blog/{category}/{template_name}.html"
    blog_content = render_to_string(template_path) if load_content else ""

    github_path = f"blog/templates/blog/{category}/{template_name}.html"

    return {
        "entry_number": entry_number,
        "template_name": template_name,
        "blog_title": blog_title,
        "blog_content": blog_content,
        "category": category,
        "github_link": f"https://github.com/aaronspindler/aaronspindler.com/commits/main/{github_path}",
    }


def get_all_blog_posts():
    """
    Scan the blog templates directory to find all blog posts.

    All blog posts must be in category subdirectories.

    Returns:
        List of dicts with template_name, category, and full_path for each blog post
    """
    blog_posts = []
    blog_templates_path = os.path.join(settings.BASE_DIR, "blog", "templates", "blog")

    for root, _dirs, files in os.walk(blog_templates_path):
        rel_path = os.path.relpath(root, blog_templates_path)

        # Skip root level - all posts must be in categories
        if rel_path == ".":
            continue

        category = rel_path.split(os.sep)[0]  # First directory is the category

        for file in files:
            if file.endswith(".html"):
                template_name = file[:-5]  # Remove .html extension, preserves original casing
                blog_posts.append(
                    {
                        "template_name": template_name,
                        "category": category,
                        "full_path": os.path.join(root, file),
                    }
                )

    return blog_posts
