from django.core.management.base import BaseCommand
import os
import subprocess
from django.conf import settings


class Command(BaseCommand):
    help = 'Build combined and minified CSS file from individual CSS files'

    def handle(self, *args, **options):
        self.stdout.write('Building combined CSS...')
        
        # Get the static directory path
        static_dir = os.path.join(settings.BASE_DIR, 'static', 'css')
        
        # Define CSS files to combine (in order of dependency)
        css_files = [
            'base.css',
            'books.css', 
            'knowledge_graph.css',
            'photos.css'
        ]
        
        # Combine CSS files
        combined_path = os.path.join(static_dir, 'combined.css')
        with open(combined_path, 'w') as combined_file:
            for css_file in css_files:
                file_path = os.path.join(static_dir, css_file)
                if os.path.exists(file_path):
                    with open(file_path, 'r') as f:
                        combined_file.write(f.read())
                        combined_file.write('\n')
                else:
                    self.stdout.write(
                        self.style.WARNING(f'Warning: {css_file} not found')
                    )
        
        # Minify using cssnano if available
        minified_path = os.path.join(static_dir, 'combined.min.css')
        
        # Record the combined file size before processing
        combined_size = os.path.getsize(combined_path)
        combined_size_kb = combined_size / 1024
        
        try:
            result = subprocess.run(
                ['cssnano', combined_path],
                capture_output=True,
                text=True,
                check=True
            )
            
            with open(minified_path, 'w') as f:
                f.write(result.stdout)
                
            self.stdout.write(
                self.style.SUCCESS('Successfully created combined.min.css')
            )
            
            # Remove the intermediate combined.css file after successful minification
            os.remove(combined_path)
            self.stdout.write('Removed intermediate combined.css file')
            
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.stdout.write(
                self.style.WARNING(
                    'cssnano not available, skipping minification. '
                    'Install with: npm install -g cssnano-cli'
                )
            )
            # If minification fails, copy combined.css as minified
            import shutil
            shutil.copy2(combined_path, minified_path)
            self.stdout.write('Copied combined.css as combined.min.css')
            
            # Remove the intermediate combined.css file after copying
            os.remove(combined_path)
            self.stdout.write('Removed intermediate combined.css file')
        
        # Show file sizes with comparison
        self.stdout.write('\nCSS file sizes:')
        self.stdout.write(f'  Combined (before minification): {combined_size_kb:.1f}KB')
        
        minified_size = os.path.getsize(minified_path)
        minified_size_kb = minified_size / 1024
        self.stdout.write(f'  Minified: {minified_size_kb:.1f}KB')
        
        # Calculate and show compression ratio
        compression_ratio = ((combined_size - minified_size) / combined_size) * 100
        self.stdout.write(f'  Compression: {compression_ratio:.1f}%')
        
        self.stdout.write(
            self.style.SUCCESS('\nCSS build complete!')
        )
