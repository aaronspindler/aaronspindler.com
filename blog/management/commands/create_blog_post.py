"""
Django management command to create a new blog post.

Usage:
    python manage.py create_blog_post --title "My Blog Post" --category tech
    python manage.py create_blog_post --title "Another Post" --category personal
"""

import os
import re

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create a new blog post with the next available blog number"

    # Valid blog post categories
    VALID_CATEGORIES = ["hobbies", "personal", "projects", "reviews", "tech"]

    def add_arguments(self, parser):
        parser.add_argument(
            "--title",
            type=str,
            required=True,
            help='Title of the blog post (e.g., "My Blog Post")',
        )
        parser.add_argument(
            "--category",
            type=str,
            required=True,
            choices=self.VALID_CATEGORIES,
            help=f'Category for the blog post. Valid options: {", ".join(self.VALID_CATEGORIES)}',
        )

    def handle(self, *args, **options):
        title = options["title"]
        category = options["category"]

        self.stdout.write(f'Creating new blog post: "{title}" in category "{category}"')

        try:
            # Get next blog number
            next_number = self._get_next_blog_number()

            # Format filename
            filename = self._format_filename(next_number, title)

            # Create the blog post file
            file_path = self._create_blog_post_file(filename, category, title)

            self.stdout.write(self.style.SUCCESS(f"Successfully created blog post: {file_path}"))
            self.stdout.write(self.style.SUCCESS(f"Blog number: {next_number:04d}"))

        except Exception as e:
            raise CommandError(f"Error creating blog post: {e}")

    def _get_next_blog_number(self):
        """
        Scan all blog post files across all categories to find the highest
        blog number and return the next available number.
        """
        blog_templates_path = os.path.join(settings.BASE_DIR, "blog", "templates", "blog")

        max_number = 0

        # Walk through all category directories
        for category in self.VALID_CATEGORIES:
            category_path = os.path.join(blog_templates_path, category)

            if not os.path.exists(category_path):
                continue

            # Look for blog post files
            for filename in os.listdir(category_path):
                if filename.endswith(".html"):
                    # Extract number from filename (e.g., "0001_Title.html" -> 1)
                    match = re.match(r"^(\d+)_", filename)
                    if match:
                        number = int(match.group(1))
                        max_number = max(max_number, number)

        return max_number + 1

    def _format_filename(self, number, title):
        """
        Format the filename from the blog number and title.

        Args:
            number: The blog post number (integer)
            title: The blog post title (string)

        Returns:
            Formatted filename (e.g., "0001_My_Blog_Post.html")
        """
        # Convert title to filename format:
        # - Replace spaces with underscores
        # - Keep original capitalization
        # - Remove special characters except underscores
        title_formatted = re.sub(r"[^\w\s-]", "", title)
        title_formatted = re.sub(r"[\s]+", "_", title_formatted)

        return f"{number:04d}_{title_formatted}.html"

    def _create_blog_post_file(self, filename, category, title):
        """
        Create the blog post file with a basic template.

        Args:
            filename: The formatted filename
            category: The blog post category
            title: The blog post title

        Returns:
            The full path to the created file
        """
        # Determine the full path
        category_path = os.path.join(settings.BASE_DIR, "blog", "templates", "blog", category)

        # Ensure category directory exists
        os.makedirs(category_path, exist_ok=True)

        file_path = os.path.join(category_path, filename)

        # Check if file already exists
        if os.path.exists(file_path):
            raise CommandError(f"Blog post file already exists: {file_path}")

        # Create the basic blog post template
        template_content = self._get_template_content(title)

        # Write the file
        with open(file_path, "w") as f:
            f.write(template_content)

        return file_path

    def _get_template_content(self, title):
        """
        Generate the basic HTML template content for a new blog post.

        Args:
            title: The blog post title

        Returns:
            The HTML template content as a string
        """
        return f"""<h2>{title}</h2>

<p>Write your blog post content here...</p>

<p>You can use HTML tags to format your content:</p>

<ul>
    <li>Use &lt;h2&gt; for headings</li>
    <li>Use &lt;p&gt; for paragraphs</li>
    <li>Use &lt;code&gt; for inline code</li>
    <li>Use &lt;pre&gt;&lt;code&gt; for code blocks</li>
    <li>Use &lt;a href="/b/..."&gt; for internal links</li>
</ul>

<p>Example code block:</p>

<pre><code class="language-python">
def hello_world():
    print("Hello, World!")
</code></pre>

<p>Remember to link to other blog posts using the format:
<code>&lt;a href="/b/&lt;entry_number&gt;_&lt;title&gt;/"&gt;link text&lt;/a&gt;</code></p>
"""
