"""
Simplified CSS build pipeline.

This command concatenates CSS files, runs PostCSS (with cssnano for minification),
optionally runs PurgeCSS, and creates compressed output files.

Versioning is handled automatically by WhiteNoise's ManifestStaticFilesStorage.
All CSS optimization is handled by cssnano - no custom parsing needed.
"""

import gzip
import re
import subprocess
import time
from functools import wraps
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand


def timer(func):
    """Decorator to time function execution"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print(f"  ⏱️  {func.__name__}: {end - start:.2f}s")
        return result

    return wrapper


class Command(BaseCommand):
    help = "Build and optimize CSS (simplified pipeline)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dev",
            action="store_true",
            help="Development mode: skip PurgeCSS for faster builds",
        )
        parser.add_argument(
            "--no-purge",
            action="store_true",
            help="Skip PurgeCSS step",
        )

    def handle(self, *args, **options):
        self.dev_mode = options.get("dev", False)
        # PurgeCSS now works correctly - templates are available during Docker build
        self.skip_purge = options.get("no_purge", False) or self.dev_mode

        mode = "development" if self.dev_mode else "production"
        self.stdout.write(self.style.SUCCESS(f"🚀 Building CSS in {mode} mode\n"))

        # Build pipeline
        combined_path = self._combine_css_files()
        processed_path = self._run_postcss(combined_path)

        if not self.skip_purge:
            processed_path = self._purge_css(processed_path)

        final_path = self._create_versioned_file(processed_path)
        self._create_compressed_versions(final_path)
        self._cleanup_temp_files(final_path)
        self._cleanup_old_versions()

        self.stdout.write(self.style.SUCCESS("\n✅ CSS build complete!\n"))

    @timer
    def _combine_css_files(self):
        """Combine all CSS files into one"""
        self.stdout.write("🔗 Combining CSS files...")

        static_dir = Path(settings.BASE_DIR) / "static" / "css"
        combined_path = static_dir / "combined.css"

        # CSS files in load order
        css_files = [
            "category-colors.css",
            "base.css",
            "theme-toggle.css",
            "books.css",
            "knowledge_graph.css",
            "photos.css",
            "blog.css",
            "autocomplete.css",
            "fast-font.css",
        ]

        with open(combined_path, "w") as combined_file:
            for css_file in css_files:
                file_path = static_dir / css_file
                if file_path.exists():
                    content = file_path.read_text()
                    # Normalize font URLs for WhiteNoise
                    content = self._normalize_font_urls(content)
                    combined_file.write(content)
                    combined_file.write("\n\n")

        size = combined_path.stat().st_size / 1024
        self.stdout.write(f"  ✓ Combined: {size:.1f}KB")
        return combined_path

    def _normalize_font_urls(self, content):
        """Normalize font URLs to absolute /static/fonts/ paths"""
        content = re.sub(
            r'url\(["\']?(?:\.\.\/)*fonts/([^"\']+)["\']?\)',
            r'url("/static/fonts/\1")',
            content,
        )
        content = re.sub(
            r'url\(["\']?static/fonts/([^"\']+)["\']?\)',
            r'url("/static/fonts/\1")',
            content,
        )
        return content

    @timer
    def _run_postcss(self, input_path):
        """Run PostCSS with cssnano for minification"""
        self.stdout.write("🎨 Running PostCSS + cssnano...")

        output_path = input_path.parent / "combined.processed.css"

        try:
            subprocess.run(
                [
                    "npx",
                    "postcss",
                    str(input_path),
                    "-o",
                    str(output_path),
                    "--config",
                    ".config/postcss.config.js",
                ],
                capture_output=True,
                text=True,
                check=True,
                cwd=settings.BASE_DIR,
            )

            size = output_path.stat().st_size / 1024
            self.stdout.write(f"  ✓ Minified: {size:.1f}KB")
            return output_path

        except subprocess.CalledProcessError as e:
            self.stdout.write(self.style.ERROR(f"  ✗ PostCSS failed: {e.stderr}"))
            return input_path

    @timer
    def _purge_css(self, input_path):
        """Remove unused CSS with PurgeCSS"""
        self.stdout.write("🧹 Purging unused CSS...")

        output_path = input_path.parent / "combined.purged.css"

        try:
            subprocess.run(
                [
                    "npx",
                    "purgecss",
                    "--css",
                    str(input_path),
                    "--config",
                    ".config/purgecss.config.js",
                    "--output",
                    str(output_path),
                ],
                capture_output=True,
                text=True,
                check=True,
                cwd=settings.BASE_DIR,
            )

            original_size = input_path.stat().st_size / 1024
            purged_size = output_path.stat().st_size / 1024
            reduction = ((original_size - purged_size) / original_size) * 100

            self.stdout.write(f"  ✓ Purged: {purged_size:.1f}KB (removed {reduction:.1f}%)")
            return output_path

        except subprocess.CalledProcessError as e:
            self.stdout.write(self.style.WARNING(f"  ⚠ PurgeCSS failed: {e.stderr}"))
            return input_path

    @timer
    def _create_versioned_file(self, input_path):
        """Create final CSS file (versioning handled by WhiteNoise)"""
        self.stdout.write("📌 Creating final file...")

        # Read content
        content = input_path.read_bytes()

        # Create final non-versioned file (WhiteNoise will handle versioning)
        final_path = input_path.parent / "combined.min.css"
        final_path.write_bytes(content)

        size = final_path.stat().st_size / 1024
        self.stdout.write(f"  ✓ Final CSS: {size:.1f}KB")
        self.stdout.write("  ℹ️  Versioning will be handled by WhiteNoise during collectstatic")

        return final_path

    @timer
    def _create_compressed_versions(self, file_path):
        """Create gzip and brotli compressed versions"""
        self.stdout.write("🗜️  Compressing...")

        content = file_path.read_bytes()

        # Gzip
        with gzip.open(str(file_path) + ".gz", "wb", compresslevel=9) as f:
            f.write(content)
        gz_size = Path(str(file_path) + ".gz").stat().st_size / 1024
        self.stdout.write(f"  ✓ Gzip: {gz_size:.1f}KB")

        # Brotli
        try:
            import brotli

            compressed = brotli.compress(content, quality=11)
            Path(str(file_path) + ".br").write_bytes(compressed)
            br_size = Path(str(file_path) + ".br").stat().st_size / 1024
            self.stdout.write(f"  ✓ Brotli: {br_size:.1f}KB")
        except ImportError:
            self.stdout.write("  ℹ️  Brotli not available")

    def _cleanup_temp_files(self, keep_file):
        """Remove intermediate build files"""
        self.stdout.write("🧹 Cleaning up...")

        static_dir = Path(settings.BASE_DIR) / "static" / "css"
        temp_files = [
            "combined.css",
            "combined.processed.css",
            "combined.purged.css",
        ]

        for temp_file in temp_files:
            temp_path = static_dir / temp_file
            if temp_path.exists() and temp_path != keep_file:
                temp_path.unlink()

        self.stdout.write("  ✓ Cleanup complete")

    def _cleanup_old_versions(self):
        """Remove manually-versioned CSS files from source directory"""
        static_dir = Path(settings.BASE_DIR) / "static" / "css"

        # Find any manually-versioned files (pattern: combined.min.*.css*)
        versioned_files = list(static_dir.glob("combined.min.*.css*"))

        if not versioned_files:
            return

        # Remove manually-versioned files (versioning is handled by WhiteNoise)
        removed_count = 0
        for file_path in versioned_files:
            file_path.unlink()
            removed_count += 1

        if removed_count > 0:
            self.stdout.write(f"  ✓ Removed {removed_count} manually-versioned files")
