from django.contrib.postgres.search import SearchVector
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string

from blog.utils import get_all_blog_posts
from pages.utils import get_books, get_projects
from photos.models import Photo, PhotoAlbum
from utils.models import SearchableContent


class Command(BaseCommand):
    help = "Rebuild search index for full-text search (blog posts, photos, albums, books, projects)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear the search index before rebuilding",
        )
        parser.add_argument(
            "--content-type",
            type=str,
            choices=["blog", "photos", "albums", "books", "projects", "all"],
            default="all",
            help="Type of content to rebuild (default: all)",
        )

    def handle(self, *args, **options):
        clear_index = options["clear"]
        content_type = options["content_type"]

        self.stdout.write(self.style.SUCCESS("Starting search index rebuild..."))

        if clear_index:
            self.stdout.write("Clearing existing search index...")
            SearchableContent.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("✓ Search index cleared"))

        if content_type in ["blog", "all"]:
            self._rebuild_blog_posts()

        if content_type in ["photos", "all"]:
            self._rebuild_photos()

        if content_type in ["albums", "all"]:
            self._rebuild_albums()

        if content_type in ["books", "all"]:
            self._rebuild_books()

        if content_type in ["projects", "all"]:
            self._rebuild_projects()

        self.stdout.write(self.style.SUCCESS("\n✓ Search index rebuild complete!"))

        total_count = SearchableContent.objects.count()
        blog_count = SearchableContent.objects.filter(content_type="blog_post").count()
        project_count = SearchableContent.objects.filter(content_type="project").count()
        book_count = SearchableContent.objects.filter(content_type="book").count()

        self.stdout.write(
            f"\nSearch Index Statistics:\n"
            f"  Total: {total_count}\n"
            f"  Blog Posts: {blog_count}\n"
            f"  Projects: {project_count}\n"
            f"  Books: {book_count}\n"
        )

    def _rebuild_blog_posts(self):
        self.stdout.write("\nIndexing blog posts...")

        blog_posts = get_all_blog_posts()
        indexed_count = 0

        for post_info in blog_posts:
            template_name = post_info["template_name"]
            category = post_info["category"]

            try:
                template_path = f"blog/{category}/{template_name}.html"
                content = render_to_string(template_path)

                title = template_name.replace("_", " ").title()

                obj, created = SearchableContent.objects.update_or_create(
                    content_type="blog_post",
                    template_name=template_name,
                    category=category,
                    defaults={
                        "title": title,
                        "description": "",  # Could be extracted from meta tags if needed
                        "content": content,
                        "url": f"/b/{category}/{template_name}/",
                    },
                )

                SearchableContent.update_search_vector(obj.id)
                indexed_count += 1

                action = "Created" if created else "Updated"
                self.stdout.write(f"  {action}: {category}/{template_name}")

            except Exception as e:
                self.stdout.write(self.style.WARNING(f"  ✗ Failed to index {category}/{template_name}: {str(e)}"))

        self.stdout.write(self.style.SUCCESS(f"✓ Indexed {indexed_count} blog posts"))

    def _rebuild_photos(self):
        self.stdout.write("\nIndexing photos...")

        photos = Photo.objects.all()
        count = 0

        for photo in photos:
            Photo.objects.filter(pk=photo.pk).update(
                search_vector=SearchVector("title", weight="A") + SearchVector("description", weight="B")
            )
            count += 1

        self.stdout.write(self.style.SUCCESS(f"✓ Indexed {count} photos"))

    def _rebuild_albums(self):
        self.stdout.write("\nIndexing photo albums...")

        albums = PhotoAlbum.objects.all()
        count = 0

        for album in albums:
            PhotoAlbum.objects.filter(pk=album.pk).update(
                search_vector=SearchVector("title", weight="A") + SearchVector("description", weight="B")
            )
            count += 1

        self.stdout.write(self.style.SUCCESS(f"✓ Indexed {count} photo albums"))

    def _rebuild_books(self):
        self.stdout.write("\nIndexing books...")

        try:
            books = get_books()
            indexed_count = 0

            for book in books:
                name = book.get("name", "")
                author = book.get("author", "")
                quote = book.get("favourite_quote", "")

                if not name:
                    continue

                obj, created = SearchableContent.objects.update_or_create(
                    content_type="book",
                    title=name,
                    defaults={
                        "description": f"by {author}" if author else "",
                        "content": quote,
                        "url": "/#books",
                        "category": "",
                        "template_name": "",
                    },
                )

                SearchableContent.update_search_vector(obj.id)
                indexed_count += 1

                action = "Created" if created else "Updated"
                self.stdout.write(f"  {action}: {name}")

            self.stdout.write(self.style.SUCCESS(f"✓ Indexed {indexed_count} books"))

        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  ✗ Failed to index books: {str(e)}"))

    def _rebuild_projects(self):
        self.stdout.write("\nIndexing projects...")

        try:
            projects = get_projects()
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  ✗ Failed to get projects: {str(e)}"))
            return

        indexed_count = 0

        for project in projects:
            name = project["name"]
            description = project["description"]
            link = project.get("link", "#")

            obj, created = SearchableContent.objects.update_or_create(
                content_type="project",
                title=name,
                defaults={
                    "description": description,
                    "content": description,  # Use description as content for now
                    "url": link,
                    "category": "",
                    "template_name": "",
                },
            )

            SearchableContent.update_search_vector(obj.id)
            indexed_count += 1

            action = "Created" if created else "Updated"
            self.stdout.write(f"  {action}: {name}")

        self.stdout.write(self.style.SUCCESS(f"✓ Indexed {indexed_count} projects"))
