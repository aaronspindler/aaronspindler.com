"""
Django management command to collect static files and optimize images.

This command runs collectstatic and then optimizes all image files in STATIC_ROOT
by compressing them based on their format.
"""

import json
import os

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from PIL import Image


class Command(BaseCommand):
    help = "Collect static files and optimize images"

    def add_arguments(self, parser):
        parser.add_argument(
            "--verbosity",
            type=int,
            default=1,
            help="Verbosity level (0=minimal, 1=normal, 2=verbose)",
        )

    def handle(self, *args, **options):
        verbosity = options.get("verbosity", 1)

        self.stdout.write("Running collectstatic...")
        try:
            call_command(
                "collectstatic",
                interactive=False,
                verbosity=verbosity,
            )
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed to collect static files: {str(e)}"))
            raise

        # Verify manifest was created
        static_root = settings.STATIC_ROOT
        manifest_path = os.path.join(static_root, "staticfiles.json")

        if not os.path.exists(manifest_path):
            error_msg = f"ERROR: Manifest file not found at {manifest_path}. Static file collection may have failed."
            self.stderr.write(self.style.ERROR(error_msg))
            raise FileNotFoundError(error_msg)

        # Verify manifest is valid JSON
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            if verbosity >= 1:
                self.stdout.write(f"Manifest file created with {len(manifest.get('paths', {}))} files")
        except json.JSONDecodeError as e:
            error_msg = f"ERROR: Manifest file is not valid JSON: {str(e)}"
            self.stderr.write(self.style.ERROR(error_msg))
            raise

        self.stdout.write("Optimizing images...")
        static_root = settings.STATIC_ROOT
        optimized_count = 0
        error_count = 0

        for root, _dirs, files in os.walk(static_root):
            for file in files:
                if file.lower().endswith((".png", ".jpg", ".jpeg", ".gif")):
                    file_path = os.path.join(root, file)
                    try:
                        self.optimize_image(file_path, verbosity)
                        optimized_count += 1
                    except Exception as e:
                        error_count += 1
                        self.stderr.write(self.style.WARNING(f"Failed to optimize {file_path}: {str(e)}"))

        if error_count > 0:
            self.stdout.write(self.style.WARNING(f"Optimized {optimized_count} images with {error_count} errors"))
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Static files collected and {optimized_count} images optimized successfully!")
            )

    def optimize_image(self, file_path, verbosity=1):
        """
        Optimize a single image file by applying format-specific compression.

        Args:
            file_path: Path to the image file to optimize
            verbosity: Verbosity level for output
        """
        with Image.open(file_path) as img:
            original_size = os.path.getsize(file_path)

            if file_path.lower().endswith((".jpg", ".jpeg")):
                converted_img = img.convert("RGB")
                converted_img.save(file_path, optimize=True, quality=80)
            elif file_path.lower().endswith(".png"):
                converted_img = img.convert("RGBA")
                converted_img.save(file_path, optimize=True, compress_level=9)
            elif file_path.lower().endswith(".gif"):
                img.save(file_path, optimize=True)

            optimized_size = os.path.getsize(file_path)
            size_reduction = (original_size - optimized_size) / original_size * 100

            if verbosity >= 2:
                self.stdout.write(
                    f"Optimized: {os.path.basename(os.path.dirname(file_path))}/{os.path.basename(file_path)} - Size reduced by {size_reduction:.2f}%"
                )
