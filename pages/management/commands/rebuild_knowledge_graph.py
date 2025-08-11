from django.core.management.base import BaseCommand
from pages.knowledge_graph import build_knowledge_graph


class Command(BaseCommand):
    help = 'Rebuild the knowledge graph from blog posts'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force rebuild even if no changes detected',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting knowledge graph rebuild...')
        )
        
        try:
            # Rebuild the graph
            graph_data = build_knowledge_graph(force_refresh=True)
            
            # Get statistics from the graph
            metrics = graph_data.get('metrics', {})
            total_posts = metrics.get('total_posts', 0)
            total_links = metrics.get('total_internal_links', 0)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Knowledge graph rebuild complete! '
                    f'Found {total_posts} posts and {total_links} internal links.'
                )
            )
            
            # Show additional info if there are errors
            if graph_data.get('errors'):
                self.stdout.write(
                    self.style.WARNING(f'Encountered errors: {graph_data["errors"]}')
                )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error rebuilding knowledge graph: {e}')
            )
