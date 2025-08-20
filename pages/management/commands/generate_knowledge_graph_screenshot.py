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
                    '--disable-web-security',  # Allow cross-origin requests
                    '--disable-features=IsolateOrigins',
                    '--disable-site-isolation-trials'
                ]
            )
            
            try:
                # Create a new page with specified viewport
                context = browser.new_context(
                    viewport={'width': width, 'height': height},
                    ignore_https_errors=True
                )
                page = context.new_page()
                
                # Enable console logging for debugging
                page.on("console", lambda msg: self.stdout.write(f"Browser console: {msg.text}"))
                page.on("pageerror", lambda err: self.stdout.write(self.style.WARNING(f"Page error: {err}")))
                
                # We need to use localhost since we're running this during build
                # The Django server needs to be running temporarily for this
                # In the Dockerfile, we'll start a temporary server
                base_url = "http://localhost:8000"
                
                self.stdout.write(f'Navigating to {base_url}...')
                
                try:
                    # Navigate to the home page with longer timeout
                    response = page.goto(f"{base_url}/", wait_until='domcontentloaded', timeout=60000)
                    
                    if response and not response.ok:
                        self.stdout.write(self.style.WARNING(f'Page returned status: {response.status}'))
                    
                    self.stdout.write('Page loaded, checking for knowledge graph...')
                    
                    # First check if the container exists at all
                    container_exists = page.evaluate("!!document.querySelector('#knowledge-graph-container')")
                    
                    if not container_exists:
                        self.stdout.write(self.style.WARNING('Knowledge graph container not found in DOM'))
                        self.stdout.write('Page HTML preview:')
                        html_preview = page.evaluate("document.body.innerHTML.substring(0, 500)")
                        self.stdout.write(html_preview)
                        
                        # Try to wait a bit more for dynamic content
                        self.stdout.write('Waiting for dynamic content to load...')
                        page.wait_for_timeout(10000)
                        
                        # Check again
                        container_exists = page.evaluate("!!document.querySelector('#knowledge-graph-container')")
                    
                    if container_exists:
                        self.stdout.write('Knowledge graph container found!')
                        
                        # Try to wait for the SVG with a shorter timeout
                        try:
                            page.wait_for_selector('#knowledge-graph-svg', state='attached', timeout=10000)
                            self.stdout.write('SVG element found!')
                            
                            # Check if there are any nodes
                            node_count = page.evaluate("document.querySelectorAll('#knowledge-graph-svg .node').length")
                            self.stdout.write(f'Found {node_count} nodes in the graph')
                            
                            if node_count == 0:
                                self.stdout.write('No nodes found, waiting longer for rendering...')
                                page.wait_for_timeout(5000)
                                node_count = page.evaluate("document.querySelectorAll('#knowledge-graph-svg .node').length")
                                self.stdout.write(f'After wait: {node_count} nodes')
                            
                        except Exception as e:
                            self.stdout.write(self.style.WARNING(f'SVG not fully loaded: {e}'))
                        
                        # Wait for stabilization
                        self.stdout.write(f'Waiting {wait_time}ms for graph to stabilize...')
                        page.wait_for_timeout(wait_time)
                        
                        # Try to trigger fit view
                        try:
                            page.evaluate("""
                                if (window.homepageGraph && typeof window.homepageGraph.fitGraphToView === 'function') {
                                    window.homepageGraph.fitGraphToView();
                                    console.log('Fit view triggered');
                                } else {
                                    console.log('Fit view function not available');
                                }
                            """)
                            page.wait_for_timeout(500)
                        except Exception as e:
                            self.stdout.write(f'Could not trigger fit view: {e}')
                        
                        # Take screenshot of the container
                        element = page.query_selector('#knowledge-graph-container')
                        if element:
                            self.stdout.write('Taking screenshot of knowledge graph container...')
                            screenshot = element.screenshot()
                        else:
                            self.stdout.write('Container lost, taking full page screenshot...')
                            screenshot = page.screenshot()
                    else:
                        # If no knowledge graph found, take a full page screenshot anyway
                        self.stdout.write(
                            self.style.WARNING('Knowledge graph not found, taking full page screenshot as fallback')
                        )
                        screenshot = page.screenshot()
                    
                    # Save the screenshot
                    with open(output_path, 'wb') as f:
                        f.write(screenshot)
                    
                    self.stdout.write(self.style.SUCCESS(f'Screenshot saved to {output_path}'))
                    
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Error during page interaction: {e}'))
                    # Take whatever screenshot we can
                    self.stdout.write('Attempting emergency screenshot...')
                    screenshot = page.screenshot()
                    with open(output_path, 'wb') as f:
                        f.write(screenshot)
                    self.stdout.write(f'Emergency screenshot saved to {output_path}')
                    
            finally:
                browser.close()
