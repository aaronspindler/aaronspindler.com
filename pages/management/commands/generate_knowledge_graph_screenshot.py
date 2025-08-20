from django.core.management.base import BaseCommand
from django.conf import settings
from playwright.sync_api import sync_playwright
from pathlib import Path
import os
import shutil
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Generate a static screenshot of the knowledge graph for caching'

    def add_arguments(self, parser):
        parser.add_argument(
            '--width',
            type=int,
            default=1200,
            help='Width of the screenshot',
        )
        parser.add_argument(
            '--height',
            type=int,
            default=800,
            help='Height of the screenshot',
        )
        parser.add_argument(
            '--wait-time',
            type=int,
            default=5000,
            help='Milliseconds to wait for graph rendering',
        )
        parser.add_argument(
            '--output-dir',
            type=str,
            default=None,
            help='Output directory for the screenshot (defaults to staticfiles/images)',
        )

    def handle(self, *args, **options):
        self.stdout.write('Starting knowledge graph screenshot generation...')
        
        try:
            # Determine output directory
            if options['output_dir']:
                output_dir = Path(options['output_dir'])
            else:
                # Use staticfiles directory which is populated during collectstatic
                output_dir = Path(settings.STATIC_ROOT) / 'images'
            
            # Create directory if it doesn't exist
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Path for the screenshot
            screenshot_path = output_dir / 'knowledge_graph_cached.png'
            
            # Generate the screenshot
            self._generate_screenshot(
                screenshot_path,
                width=options['width'],
                height=options['height'],
                wait_time=options['wait_time']
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully generated knowledge graph screenshot at: {screenshot_path}'
                )
            )
            
            # Also copy to static directory for development if different
            static_dir = Path(settings.BASE_DIR) / 'static' / 'images'
            static_screenshot_path = static_dir / 'knowledge_graph_cached.png'
            
            if static_screenshot_path != screenshot_path and static_dir.exists():
                try:
                    shutil.copy2(screenshot_path, static_screenshot_path)
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Also copied screenshot to static directory: {static_screenshot_path}'
                        )
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Could not copy to static directory: {e}'
                        )
                    )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error generating knowledge graph screenshot: {e}')
            )
            raise
    
    def _generate_screenshot(self, output_path, width=1200, height=800, wait_time=5000):
        """Generate the screenshot using Playwright."""
        with sync_playwright() as p:
            # Launch headless browser with Docker-compatible settings
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',  # Required for Docker
                    '--disable-setuid-sandbox',  # Required for Docker
                    '--disable-dev-shm-usage',  # Overcome limited resource problems
                    '--disable-gpu',  # Disable GPU hardware acceleration
                    '--single-process'  # Run in single process mode for containers
                ]
            )
            
            try:
                # Create a new page with specified viewport
                page = browser.new_page(viewport={'width': width, 'height': height})
                
                # We need to use localhost since we're running this during build
                # The Django server needs to be running temporarily for this
                # In the Dockerfile, we'll start a temporary server
                base_url = "http://127.0.0.1:8000"
                
                self.stdout.write(f'Navigating to {base_url}...')
                
                # Navigate to the home page (where the knowledge graph is)
                page.goto(f"{base_url}/", wait_until='networkidle', timeout=30000)
                
                self.stdout.write('Waiting for knowledge graph container...')
                
                # Wait for the knowledge graph container to be visible
                page.wait_for_selector('#knowledge-graph-container', state='visible', timeout=15000)
                
                # Wait for the SVG element to be present
                page.wait_for_selector('#knowledge-graph-svg', state='visible', timeout=15000)
                
                # Wait for the graph to render (check for nodes)
                page.wait_for_selector('#knowledge-graph-svg .node', state='visible', timeout=15000)
                
                self.stdout.write(f'Waiting {wait_time}ms for graph to stabilize...')
                
                # Additional wait to ensure animation and layout stabilization
                page.wait_for_timeout(wait_time)
                
                # Trigger the fit view function to ensure everything is visible
                page.evaluate("""
                    if (window.homepageGraph && typeof window.homepageGraph.fitGraphToView === 'function') {
                        window.homepageGraph.fitGraphToView();
                    }
                """)
                
                # Wait a bit for the zoom animation
                page.wait_for_timeout(500)
                
                self.stdout.write('Taking screenshot...')
                
                # Get the knowledge graph element specifically
                element = page.query_selector('#knowledge-graph-container')
                if element:
                    screenshot = element.screenshot()
                else:
                    # Fallback to full page if element not found
                    self.stdout.write(
                        self.style.WARNING('Knowledge graph container not found, taking full page screenshot')
                    )
                    screenshot = page.screenshot()
                
                # Save the screenshot
                with open(output_path, 'wb') as f:
                    f.write(screenshot)
                
                self.stdout.write(f'Screenshot saved to {output_path}')
                
            finally:
                browser.close()
