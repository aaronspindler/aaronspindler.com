import asyncio
import hashlib
import json
import logging

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from pyppeteer import launch

from blog.knowledge_graph import build_knowledge_graph
from blog.models import KnowledgeGraphScreenshot

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Generate a screenshot of the knowledge graph and save to database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--url",
            type=str,
            default="http://localhost:8000",
            help="Base URL to screenshot (default: http://localhost:8000)",
        )

    def handle(self, *args, **options):
        self.stdout.write("Starting knowledge graph screenshot generation...")

        try:
            # Generate the screenshot with the specified URL
            base_url = options["url"]
            # Run the async function in a sync context
            screenshot_data = asyncio.run(self._generate_screenshot_async(base_url))

            # Generate hash of current graph data
            self.stdout.write("Building knowledge graph data...")
            graph_data = build_knowledge_graph()
            graph_hash = hashlib.sha256(json.dumps(graph_data, sort_keys=True).encode()).hexdigest()

            # Check if a screenshot with this hash already exists
            self.stdout.write("Checking for existing screenshot with same hash...")
            try:
                screenshot_obj = KnowledgeGraphScreenshot.objects.get(graph_data_hash=graph_hash)
                self.stdout.write(f"Found existing screenshot with hash {graph_hash[:8]}, updating image...")
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

    async def _generate_screenshot_async(self, base_url):
        """Generate the screenshot using pyppeteer with high quality settings and return the screenshot data."""
        # Hardcoded defaults
        width = 2400
        height = 1600
        device_scale_factor = 2.0
        wait_time = 10000
        transparent = True  # Always use transparent background

        # Launch headless browser with Docker-compatible settings
        browser = await launch(
            headless=True,
            args=[
                "--no-sandbox",  # Required for Docker
                "--disable-setuid-sandbox",  # Required for Docker
                "--disable-dev-shm-usage",  # Overcome limited resource problems
                "--disable-gpu",  # Disable GPU hardware acceleration
                "--disable-web-security",  # Allow cross-origin requests
                "--disable-features=IsolateOrigins",
                "--disable-site-isolation-trials",
                f"--force-device-scale-factor={device_scale_factor}",  # Force high DPI
                "--high-dpi-support=1",  # Enable high DPI support
                "--force-color-profile=srgb",  # Ensure consistent color profile
            ],
            # pyppeteer auto-downloads chromium if not present
            handleSIGINT=False,
            handleSIGTERM=False,
            handleSIGHUP=False,
        )

        try:
            # Create a new page with specified viewport and device scale factor
            page = await browser.newPage()
            await page.setViewport(
                {
                    "width": width,
                    "height": height,
                    "deviceScaleFactor": device_scale_factor,
                }
            )

            # Enable console logging for debugging
            page.on("console", lambda msg: self.stdout.write(f"Browser console: {msg.text}"))
            page.on("pageerror", lambda err: self.stdout.write(self.style.WARNING(f"Page error: {err}")))

            self.stdout.write(f"Navigating to {base_url}...")

            try:
                # Navigate to the home page with longer timeout
                response = await page.goto(f"{base_url}/", options={"waitUntil": "domcontentloaded", "timeout": 60000})

                if response and not response.ok:
                    self.stdout.write(self.style.WARNING(f"Page returned status: {response.status}"))

                self.stdout.write("Page loaded, checking for knowledge graph...")

                # First check if the container exists at all
                container_exists = await page.evaluate("!!document.querySelector('#knowledge-graph-container')")

                if not container_exists:
                    self.stdout.write(self.style.WARNING("Knowledge graph container not found in DOM"))
                    self.stdout.write("Page HTML preview:")
                    html_preview = await page.evaluate("document.body.innerHTML.substring(0, 500)")
                    self.stdout.write(html_preview)

                    # Try to wait a bit more for dynamic content
                    self.stdout.write("Waiting for dynamic content to load...")
                    await page.waitFor(10000)

                    # Check again
                    container_exists = await page.evaluate("!!document.querySelector('#knowledge-graph-container')")

                if container_exists:
                    self.stdout.write("Knowledge graph container found!")

                    # Try to wait for the SVG with a shorter timeout
                    try:
                        await page.waitForSelector("#knowledge-graph-svg", options={"visible": True, "timeout": 10000})
                        self.stdout.write("SVG element found!")

                        # Check if there are any nodes
                        node_count = await page.evaluate(
                            "document.querySelectorAll('#knowledge-graph-svg .node').length"
                        )
                        self.stdout.write(f"Found {node_count} nodes in the graph")

                        if node_count == 0:
                            self.stdout.write("No nodes found, waiting longer for rendering...")
                            await page.waitFor(5000)
                            node_count = await page.evaluate(
                                "document.querySelectorAll('#knowledge-graph-svg .node').length"
                            )
                            self.stdout.write(f"After wait: {node_count} nodes")

                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f"SVG not fully loaded: {e}"))

                    # Wait for stabilization
                    self.stdout.write(f"Waiting {wait_time}ms for graph to stabilize...")
                    await page.waitFor(wait_time)

                    # Try to trigger fit view
                    try:
                        await page.evaluate(
                            """
                            if (window.homepageGraph && typeof window.homepageGraph.fitGraphToView === 'function') {
                                window.homepageGraph.fitGraphToView();
                                console.log('Fit view triggered');
                            } else {
                                console.log('Fit view function not available');
                            }
                        """
                        )
                        await page.waitFor(500)
                    except Exception as e:
                        self.stdout.write(f"Could not trigger fit view: {e}")

                    # Take screenshot of the container
                    element = await page.querySelector("#knowledge-graph-container")
                    if element:
                        self.stdout.write("Taking high-quality screenshot of knowledge graph container...")
                        # Get element bounds for better positioning
                        box = await element.boundingBox()
                        if box:
                            self.stdout.write(f"Container dimensions: {box['width']}x{box['height']}")

                        screenshot = await element.screenshot(
                            {
                                "omitBackground": transparent,  # Transparent background if requested
                            }
                        )
                    else:
                        self.stdout.write("Container lost, taking full page screenshot...")
                        screenshot = await page.screenshot(
                            {
                                "fullPage": True,
                                "omitBackground": transparent,  # Transparent background if requested
                            }
                        )
                else:
                    # If no knowledge graph found, take a full page screenshot anyway
                    self.stdout.write(
                        self.style.WARNING("Knowledge graph not found, taking full page screenshot as fallback")
                    )
                    screenshot = await page.screenshot(
                        {
                            "fullPage": True,
                            "omitBackground": transparent,  # Transparent background if requested
                        }
                    )

                # Return the screenshot data
                self.stdout.write(self.style.SUCCESS("Screenshot generated successfully"))
                return screenshot

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error during page interaction: {e}"))
                # Take whatever screenshot we can
                self.stdout.write("Attempting emergency screenshot...")
                screenshot = await page.screenshot(
                    {
                        "fullPage": True,
                        "omitBackground": transparent,  # Transparent background if requested
                    }
                )
                self.stdout.write("Emergency screenshot generated")
                return screenshot

        finally:
            await browser.close()
