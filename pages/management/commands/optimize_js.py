"""
Django management command to optimize JavaScript files.

This command minifies JavaScript files and creates compressed versions
(gzip and brotli) for efficient serving.
"""

import os
import subprocess

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Optimize JavaScript files (minify and compress)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-minify",
            action="store_true",
            help="Skip minification step",
        )
        parser.add_argument(
            "--skip-compress",
            action="store_true",
            help="Skip compression step",
        )

    def handle(self, *args, **options):
        static_dir = os.path.join(settings.BASE_DIR, "static")
        js_dir = os.path.join(static_dir, "js")

        if not options["skip_minify"]:
            self.stdout.write("Minifying JavaScript files...")
            try:
                # Run npm minification
                result = subprocess.run(
                    ["npm", "run", "minify:js"],
                    check=False,
                    capture_output=True,
                    text=True,
                    cwd=settings.BASE_DIR,
                )
                if result.returncode != 0:
                    self.stdout.write(self.style.ERROR(f"Minification failed: {result.stderr}"))
                    return
                self.stdout.write(self.style.SUCCESS("✓ JavaScript minified successfully"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error during minification: {str(e)}"))
                return

        if not options["skip_compress"]:
            self.stdout.write("Compressing JavaScript files...")
            try:
                # Run compression
                result = subprocess.run(
                    ["npm", "run", "compress:js"],
                    check=False,
                    capture_output=True,
                    text=True,
                    cwd=settings.BASE_DIR,
                )
                if result.returncode != 0:
                    self.stdout.write(self.style.ERROR(f"Compression failed: {result.stderr}"))
                    return
                self.stdout.write(self.style.SUCCESS("✓ JavaScript compressed successfully"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error during compression: {str(e)}"))
                return

        # Report final sizes
        self.stdout.write("\nOptimized JavaScript file sizes:")
        js_files = [
            "base-optimized.min.js",
            "knowledge_graph.min.js",
            "search-autocomplete.min.js",
        ]

        for filename in js_files:
            filepath = os.path.join(js_dir, filename)
            if os.path.exists(filepath):
                size = os.path.getsize(filepath) / 1024
                gz_path = filepath + ".gz"
                br_path = filepath + ".br"

                self.stdout.write(f"\n  {filename}:")
                self.stdout.write(f"    Original: {size:.2f} KB")

                if os.path.exists(gz_path):
                    gz_size = os.path.getsize(gz_path) / 1024
                    reduction = (1 - gz_size / size) * 100
                    self.stdout.write(f"    Gzip: {gz_size:.2f} KB ({reduction:.1f}% reduction)")

                if os.path.exists(br_path):
                    br_size = os.path.getsize(br_path) / 1024
                    reduction = (1 - br_size / size) * 100
                    self.stdout.write(f"    Brotli: {br_size:.2f} KB ({reduction:.1f}% reduction)")

        self.stdout.write(self.style.SUCCESS("\n✅ JavaScript optimization complete!"))
