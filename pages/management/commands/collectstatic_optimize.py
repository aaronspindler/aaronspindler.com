import os
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings
from PIL import Image

class Command(BaseCommand):
    help = 'Collect static files and optimize images'

    def handle(self, *args, **options):
        # First, run the regular collectstatic command
        self.stdout.write('Running collectstatic...')
        call_command('collectstatic', interactive=False, verbosity=0)

        # Then, optimize images
        self.stdout.write('Optimizing images...')
        static_root = settings.STATIC_ROOT
        for root, dirs, files in os.walk(static_root):
            for file in files:
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                    file_path = os.path.join(root, file)
                    self.optimize_image(file_path)

        self.stdout.write(self.style.SUCCESS('Static files collected and images optimized successfully!'))

    def optimize_image(self, file_path):
        try:
            with Image.open(file_path) as img:
                # Get the image size before optimization
                original_size = os.path.getsize(file_path)
                # Perform optimization based on image format
                if file_path.lower().endswith(('.jpg', '.jpeg')):
                    img = img.convert('RGB')
                    img.save(file_path, optimize=True, quality=80)
                elif file_path.lower().endswith('.png'):
                    img = img.convert('RGBA')
                    img.save(file_path, optimize=True, compress_level=9)
                elif file_path.lower().endswith('.gif'):
                    img.save(file_path, optimize=True)
                
                # Get the image size after optimization
                optimized_size = os.path.getsize(file_path)
                # Calculate the percentage of size reduction
                size_reduction = (original_size - optimized_size) / original_size * 100
                self.stdout.write(f'Optimized: {os.path.basename(os.path.dirname(file_path))}/{os.path.basename(file_path)} - Size reduced by {size_reduction:.2f}%')
        except Exception as e:
            self.stderr.write(f'Error optimizing {file_path}: {str(e)}')
