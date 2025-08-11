from django.core.management.base import BaseCommand
from django.core.cache import cache
from pages.knowledge_graph import build_knowledge_graph, GraphBuilder


class Command(BaseCommand):
    help = 'Rebuild the knowledge graph from blog posts'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force rebuild even if no changes detected',
        )
        parser.add_argument(
            '--test-api',
            action='store_true',
            help='Test the knowledge graph API endpoint after rebuild',
        )

    def handle(self, *args, **options):
        self.stdout.write('Starting knowledge graph rebuild...')
        
        try:
            self._clear_caches()
            graph_data = self._rebuild_graph()
            self._display_results(graph_data)
            
            if options['test_api']:
                self._test_api_endpoint()
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error rebuilding knowledge graph: {e}')
            )
    
    def _clear_caches(self):
        """Clear all knowledge graph related caches."""
        cache.delete('blog:graph:complete')
        
        graph_builder = GraphBuilder()
        blog_templates = graph_builder._get_all_blog_templates()
        
        for template_name in blog_templates:
            cache.delete(f'blog:links:{template_name}')
            cache.delete(f'blog:links:{template_name}:meta')
            
            for depth in [1, 2, 3]:
                cache.delete(f'blog:graph:post:{template_name}:depth:{depth}')
    
    def _rebuild_graph(self):
        """Rebuild the knowledge graph."""
        return build_knowledge_graph(force_refresh=True)
    
    def _display_results(self, graph_data):
        """Display rebuild results."""
        metrics = graph_data.get('metrics', {})
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Rebuild complete: '
                f'{metrics.get("total_posts", 0)} posts, '
                f'{metrics.get("total_internal_links", 0)} internal links, '
                f'{metrics.get("total_external_links", 0)} external links'
            )
        )
        
        if graph_data.get('errors'):
            self.stdout.write(
                self.style.WARNING(f'Errors: {graph_data["errors"]}')
            )
        
        orphan_posts = metrics.get('orphan_posts', [])
        if orphan_posts:
            self.stdout.write(
                self.style.WARNING(f'{len(orphan_posts)} orphaned posts found')
            )
    
    def _test_api_endpoint(self):
        """Test the knowledge graph API endpoint."""
        try:
            from django.test import Client
            
            client = Client()
            response = client.get('/api/knowledge-graph/')
            
            status = 'SUCCESS' if response.status_code == 200 else 'ERROR'
            message = 'API test passed' if response.status_code == 200 else f'API test failed (status {response.status_code})'
            
            self.stdout.write(getattr(self.style, status)(message))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'API test error: {e}'))
