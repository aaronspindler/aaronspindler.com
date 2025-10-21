import json
import logging
import subprocess

from django.core.management.base import BaseCommand, CommandError

from utils.models import LighthouseAudit

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Run a Lighthouse audit and store the results in the database.
    Uses @lhci/cli to perform the audit and extracts all 5 category scores.
    """

    help = "Run a Lighthouse audit and store the results"

    # Default URL for audits
    DEFAULT_URL = "https://aaronspindler.com"

    def add_arguments(self, parser):
        parser.add_argument(
            "--async",
            action="store_true",
            dest="async_mode",
            help="Queue the audit task to Celery instead of running it directly",
        )

    def handle(self, *args, **options):
        async_mode = options["async_mode"]
        url = self.DEFAULT_URL

        # If async mode, queue the task to Celery
        if async_mode:
            from utils.tasks import run_lighthouse_audit as run_lighthouse_audit_task

            task = run_lighthouse_audit_task.delay()
            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ Lighthouse audit task queued to Celery!\n"
                    f"  URL: {url}\n"
                    f"  Task ID: {task.id}\n"
                    f"  Use 'celery -A config inspect active' to monitor task status"
                )
            )
            return

        # Otherwise, run the audit directly
        self.stdout.write(f"Running Lighthouse audit for {url}...")

        try:
            import glob
            import os
            import shutil

            # @lhci/cli saves to .lighthouseci directory by default
            output_dir = ".lighthouseci"

            # Clean up any existing reports
            if os.path.exists(output_dir):
                shutil.rmtree(output_dir)

            # Get Chrome path from environment or use default from Playwright image
            chrome_path = os.environ.get("CHROME_PATH", "/usr/bin/chromium")

            # Run Lighthouse using @lhci/cli with explicit Chrome path
            # Chrome flags for containerized environments:
            # --no-sandbox: Required when running as root in Docker
            # --disable-dev-shm-usage: Prevents /dev/shm issues in containers
            # --disable-gpu: Disables GPU hardware acceleration (not needed for headless)
            result = subprocess.run(
                [
                    "npx",
                    "@lhci/cli",
                    "collect",
                    f"--url={url}",
                    "--numberOfRuns=1",
                    f"--chromePath={chrome_path}",
                    "--chrome-flags=--no-sandbox --disable-dev-shm-usage --disable-gpu",
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=300,  # 5 minute timeout
            )

            if result.returncode != 0:
                logger.error(f"Lighthouse audit failed: {result.stderr}")
                raise CommandError(f"Lighthouse audit failed: {result.stderr}")

            # Find and parse the Lighthouse report JSON
            # @lhci/cli creates files with pattern: lhr-<timestamp>.json
            json_files = glob.glob(os.path.join(output_dir, "lhr-*.json"))

            if not json_files:
                raise CommandError("No Lighthouse report found in output directory")

            # Read the first JSON report
            with open(json_files[0], "r") as f:
                report = json.load(f)

            # Clean up the output directory
            shutil.rmtree(output_dir)

            # Extract category scores
            categories = report.get("categories", {})

            performance_score = int(categories.get("performance", {}).get("score", 0) * 100)
            accessibility_score = int(categories.get("accessibility", {}).get("score", 0) * 100)
            best_practices_score = int(categories.get("best-practices", {}).get("score", 0) * 100)
            seo_score = int(categories.get("seo", {}).get("score", 0) * 100)

            # Create metadata with additional useful information
            metadata = {
                "fetch_time": report.get("fetchTime"),
                "user_agent": report.get("userAgent"),
                "requested_url": report.get("requestedUrl"),
                "final_url": report.get("finalUrl"),
                "lighthouse_version": report.get("lighthouseVersion"),
            }

            # Store the audit result
            audit = LighthouseAudit.objects.create(
                url=url,
                performance_score=performance_score,
                accessibility_score=accessibility_score,
                best_practices_score=best_practices_score,
                seo_score=seo_score,
                metadata=metadata,
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ Lighthouse audit completed successfully!\n"
                    f"  Performance: {performance_score}\n"
                    f"  Accessibility: {accessibility_score}\n"
                    f"  Best Practices: {best_practices_score}\n"
                    f"  SEO: {seo_score}\n"
                    f"  Average: {audit.average_score}\n"
                    f"  Audit ID: {audit.id}"
                )
            )

        except subprocess.TimeoutExpired:
            logger.error("Lighthouse audit timed out after 5 minutes")
            raise CommandError("Lighthouse audit timed out after 5 minutes")
        except FileNotFoundError as e:
            logger.error(f"Command not found: {e}")
            raise CommandError(
                "Unable to run Lighthouse. Make sure @lhci/cli is installed:\n" "  npm install --save-dev @lhci/cli"
            )
        except Exception as e:
            logger.error(f"Unexpected error during Lighthouse audit: {e}")
            raise CommandError(f"Unexpected error: {e}")
