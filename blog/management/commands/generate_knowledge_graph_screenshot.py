import hashlib
import json
import logging

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from playwright.sync_api import sync_playwright

from blog.knowledge_graph import build_knowledge_graph
from blog.models import KnowledgeGraphScreenshot

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Generate a screenshot of the knowledge graph and save to database"

    def handle(self, *args, **options):
        self.stdout.write("Starting knowledge graph screenshot generation...")

        try:
            # Generate the screenshot with hardcoded defaults
            screenshot_data = self._generate_screenshot()

            # Generate hash of current graph data
            self.stdout.write("Building knowledge graph data...")
            graph_data = build_knowledge_graph()
            graph_hash = hashlib.sha256(json.dumps(graph_data, sort_keys=True).encode()).hexdigest()

            # Check if a screenshot with this hash already exists
            self.stdout.write("Checking for existing screenshot with same hash...")
            try:
                screenshot_obj = KnowledgeGraphScreenshot.objects.get(graph_data_hash=graph_hash)
                self.stdout.write(f"Found existing screenshot with hash {graph_hash[:8]}, updating image...")
                # Delete the old image file if it exists
                if screenshot_obj.image:
                    screenshot_obj.image.delete(save=False)
            except KnowledgeGraphScreenshot.DoesNotExist:
                self.stdout.write(f"No existing screenshot with hash {graph_hash[:8]}, creating new entry...")
                screenshot_obj = KnowledgeGraphScreenshot()
                screenshot_obj.graph_data_hash = graph_hash

            # Save the new image
            self.stdout.write("Saving screenshot to database...")
            screenshot_obj.image.save(
                f"knowledge_graph_{graph_hash[:8]}.png",
                ContentFile(screenshot_data),
                save=True,
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully generated and saved knowledge graph screenshot with hash: {graph_hash[:8]}"
                )
            )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error generating knowledge graph screenshot: {e}"))
            raise

    def _generate_screenshot(self):
        """Generate the screenshot using Playwright with high quality settings and return the screenshot data."""
        # Hardcoded defaults
        width = 2400
        height = 1600
        device_scale_factor = 2.0
        wait_time = 10000
        full_page = False
        transparent = True  # Always use transparent background
        with sync_playwright() as p:
            # Launch headless browser with Docker-compatible settings
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",  # Required for Docker
                    "--disable-setuid-sandbox",  # Required for Docker
                    "--disable-dev-shm-usage",  # Overcome limited resource problems
                    "--disable-gpu",  # Disable GPU hardware acceleration
                    "--disable-web-security",  # Allow cross-origin requests
                    "--disable-features=IsolateOrigins",
                    "--disable-site-isolation-trials",
                    "--force-device-scale-factor=" + str(device_scale_factor),  # Force high DPI
                    "--high-dpi-support=1",  # Enable high DPI support
                    "--force-color-profile=srgb",  # Ensure consistent color profile
                ],
            )

            try:
                # Create a new page with specified viewport and device scale factor
                context = browser.new_context(
                    viewport={"width": width, "height": height},
                    device_scale_factor=device_scale_factor,  # High DPI for better quality
                    ignore_https_errors=True,
                    screen={
                        "width": width,
                        "height": height,
                    },  # Set screen size as well
                )
                page = context.new_page()

                # Enable console logging for debugging
                page.on(
                    "console",
                    lambda msg: self.stdout.write(f"Browser console: {msg.text}"),
                )
                page.on(
                    "pageerror",
                    lambda err: self.stdout.write(self.style.WARNING(f"Page error: {err}")),
                )

                # We need to use localhost since we're running this during build
                # The Django server needs to be running temporarily for this
                # In the Dockerfile, we'll start a temporary server
                base_url = "http://localhost:8000"

                self.stdout.write(f"Navigating to {base_url}...")

                try:
                    # Navigate to the home page with longer timeout
                    response = page.goto(f"{base_url}/", wait_until="domcontentloaded", timeout=60000)

                    if response and not response.ok:
                        self.stdout.write(self.style.WARNING(f"Page returned status: {response.status}"))

                    self.stdout.write("Page loaded, checking for knowledge graph...")

                    # First check if the container exists at all
                    container_exists = page.evaluate("!!document.querySelector('#knowledge-graph-container')")

                    if not container_exists:
                        self.stdout.write(self.style.WARNING("Knowledge graph container not found in DOM"))
                        self.stdout.write("Page HTML preview:")
                        html_preview = page.evaluate("document.body.innerHTML.substring(0, 500)")
                        self.stdout.write(html_preview)

                        # Try to wait a bit more for dynamic content
                        self.stdout.write("Waiting for dynamic content to load...")
                        page.wait_for_timeout(10000)

                        # Check again
                        container_exists = page.evaluate("!!document.querySelector('#knowledge-graph-container')")

                    if container_exists:
                        self.stdout.write("Knowledge graph container found!")

                        # Try to wait for the SVG with a shorter timeout
                        try:
                            page.wait_for_selector("#knowledge-graph-svg", state="attached", timeout=10000)
                            self.stdout.write("SVG element found!")

                            # Check if there are any nodes
                            node_count = page.evaluate("document.querySelectorAll('#knowledge-graph-svg .node').length")
                            self.stdout.write(f"Found {node_count} nodes in the graph")

                            if node_count == 0:
                                self.stdout.write("No nodes found, waiting longer for rendering...")
                                page.wait_for_timeout(5000)
                                node_count = page.evaluate(
                                    "document.querySelectorAll('#knowledge-graph-svg .node').length"
                                )
                                self.stdout.write(f"After wait: {node_count} nodes")

                        except Exception as e:
                            self.stdout.write(self.style.WARNING(f"SVG not fully loaded: {e}"))

                        # Wait for stabilization
                        self.stdout.write(f"Waiting {wait_time}ms for graph to stabilize...")
                        page.wait_for_timeout(wait_time)

                        # Try to trigger fit view
                        try:
                            page.evaluate(
                                """
                                if (window.homepageGraph && typeof window.homepageGraph.fitGraphToView === 'function') {
                                    window.homepageGraph.fitGraphToView();
                                    console.log('Fit view triggered');
                                } else {
                                    console.log('Fit view function not available');
                                }
                            """
                            )
                            page.wait_for_timeout(500)
                        except Exception as e:
                            self.stdout.write(f"Could not trigger fit view: {e}")

                        # Take screenshot of the container or full page
                        if full_page:
                            self.stdout.write("Taking full page screenshot...")
                            screenshot = page.screenshot(
                                full_page=True,
                                animations="disabled",  # Disable animations for cleaner screenshot
                                scale="device",  # Use device scale factor
                                omit_background=transparent,  # Transparent background if requested
                            )
                        else:
                            element = page.query_selector("#knowledge-graph-container")
                            if element:
                                self.stdout.write("Taking high-quality screenshot of knowledge graph container...")
                                # Get element bounds for better positioning
                                box = element.bounding_box()
                                if box:
                                    self.stdout.write(f'Container dimensions: {box["width"]}x{box["height"]}')

                                screenshot = element.screenshot(
                                    animations="disabled",  # Disable animations
                                    scale="device",  # Use device scale factor
                                    timeout=30000,  # Longer timeout for large screenshots
                                    omit_background=transparent,  # Transparent background if requested
                                )
                            else:
                                self.stdout.write("Container lost, taking full page screenshot...")
                                screenshot = page.screenshot(
                                    full_page=True,
                                    animations="disabled",
                                    scale="device",
                                    omit_background=transparent,  # Transparent background if requested
                                )
                    else:
                        # If no knowledge graph found, take a full page screenshot anyway
                        self.stdout.write(
                            self.style.WARNING("Knowledge graph not found, taking full page screenshot as fallback")
                        )
                        screenshot = page.screenshot(
                            full_page=True,
                            animations="disabled",
                            scale="device",
                            omit_background=transparent,  # Transparent background if requested
                        )

                    # Return the screenshot data
                    self.stdout.write(self.style.SUCCESS("Screenshot generated successfully"))
                    return screenshot

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error during page interaction: {e}"))
                    # Take whatever screenshot we can
                    self.stdout.write("Attempting emergency screenshot...")
                    screenshot = page.screenshot(
                        full_page=True,
                        animations="disabled",
                        scale="device",
                        omit_background=transparent,  # Transparent background if requested
                    )
                    self.stdout.write("Emergency screenshot generated")
                    return screenshot

            finally:
                browser.close()
