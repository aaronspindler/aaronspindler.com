import json
import subprocess
import tempfile
import logging
from django.core.management.base import BaseCommand, CommandError
from lighthouse_monitor.models import LighthouseAudit

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Run a Lighthouse audit and store the results in the database.
    Uses @lhci/cli to perform the audit and extracts all 5 category scores.
    """
    help = 'Run a Lighthouse audit and store the results'

    def add_arguments(self, parser):
        parser.add_argument(
            '--url',
            type=str,
            default='https://aaronspindler.com',
            help='URL to audit (default: https://aaronspindler.com)'
        )

    def handle(self, *args, **options):
        url = options['url']
        self.stdout.write(f'Running Lighthouse audit for {url}...')

        try:
            # Create a temporary directory for Lighthouse output
            with tempfile.TemporaryDirectory() as tmpdir:
                # Run Lighthouse using @lhci/cli
                result = subprocess.run(
                    [
                        'npx',
                        '@lhci/cli',
                        'collect',
                        f'--url={url}',
                        '--numberOfRuns=1',
                        f'--settings.output-dir={tmpdir}',
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=300  # 5 minute timeout
                )

                if result.returncode != 0:
                    logger.error(f'Lighthouse audit failed: {result.stderr}')
                    raise CommandError(f'Lighthouse audit failed: {result.stderr}')

                # Find and parse the Lighthouse report JSON
                import os
                import glob
                
                # Find the manifest.json file which contains the report path
                json_files = glob.glob(os.path.join(tmpdir, '*.report.json'))
                
                if not json_files:
                    raise CommandError('No Lighthouse report found in output directory')
                
                # Read the first JSON report
                with open(json_files[0], 'r') as f:
                    report = json.load(f)

                # Extract category scores
                categories = report.get('categories', {})
                
                performance_score = int(categories.get('performance', {}).get('score', 0) * 100)
                accessibility_score = int(categories.get('accessibility', {}).get('score', 0) * 100)
                best_practices_score = int(categories.get('best-practices', {}).get('score', 0) * 100)
                seo_score = int(categories.get('seo', {}).get('score', 0) * 100)
                pwa_score = int(categories.get('pwa', {}).get('score', 0) * 100)

                # Create metadata with additional useful information
                metadata = {
                    'fetch_time': report.get('fetchTime'),
                    'user_agent': report.get('userAgent'),
                    'requested_url': report.get('requestedUrl'),
                    'final_url': report.get('finalUrl'),
                    'lighthouse_version': report.get('lighthouseVersion'),
                }

                # Store the audit result
                audit = LighthouseAudit.objects.create(
                    url=url,
                    performance_score=performance_score,
                    accessibility_score=accessibility_score,
                    best_practices_score=best_practices_score,
                    seo_score=seo_score,
                    pwa_score=pwa_score,
                    metadata=metadata,
                )

                self.stdout.write(self.style.SUCCESS(
                    f'✓ Lighthouse audit completed successfully!\n'
                    f'  Performance: {performance_score}\n'
                    f'  Accessibility: {accessibility_score}\n'
                    f'  Best Practices: {best_practices_score}\n'
                    f'  SEO: {seo_score}\n'
                    f'  PWA: {pwa_score}\n'
                    f'  Average: {audit.average_score}\n'
                    f'  Audit ID: {audit.id}'
                ))

        except subprocess.TimeoutExpired:
            logger.error('Lighthouse audit timed out after 5 minutes')
            raise CommandError('Lighthouse audit timed out after 5 minutes')
        except FileNotFoundError as e:
            logger.error(f'Command not found: {e}')
            raise CommandError(
                'Unable to run Lighthouse. Make sure @lhci/cli is installed:\n'
                '  npm install --save-dev @lhci/cli'
            )
        except Exception as e:
            logger.error(f'Unexpected error during Lighthouse audit: {e}')
            raise CommandError(f'Unexpected error: {e}')

