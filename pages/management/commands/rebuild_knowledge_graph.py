from django.core.management.base import BaseCommand
from django.core.cache import cache
from pages.knowledge_graph import build_knowledge_graph


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
        self.stdout.write(
            self.style.SUCCESS('Starting knowledge graph rebuild...')
        )
        
        try:
            # Clear all knowledge graph related cache
            self.stdout.write('Clearing knowledge graph cache...')
            
            # Clear main graph cache
            cache.delete('blog:graph:complete')
            
            # Clear all blog post link caches
            # Since Django cache doesn't support wildcard deletion, we'll clear the main ones
            # and let the system rebuild them as needed
            self.stdout.write('Clearing blog post link caches...')
            
            # Get all blog templates to clear their specific caches
            from pages.knowledge_graph import GraphBuilder
            graph_builder = GraphBuilder()
            blog_templates = graph_builder._get_all_blog_templates()
            
            cleared_count = 0
            for template_name in blog_templates:
                cache_key = f'blog:links:{template_name}'
                cache_meta_key = f'blog:links:{template_name}:meta'
                if cache.delete(cache_key):
                    cleared_count += 1
                cache.delete(cache_meta_key)
            
            self.stdout.write(f'Cleared {cleared_count} blog post link caches.')
            
            # Clear post-specific graph caches
            for template_name in blog_templates:
                for depth in [1, 2, 3]:  # Common depth values
                    cache_key = f'blog:graph:post:{template_name}:depth:{depth}'
                    cache.delete(cache_key)
            
            self.stdout.write('Knowledge graph cache cleared successfully.')
            
            # Rebuild the graph
            self.stdout.write('Rebuilding knowledge graph...')
            graph_data = build_knowledge_graph(force_refresh=True)
            
            # Get statistics from the graph
            metrics = graph_data.get('metrics', {})
            total_posts = metrics.get('total_posts', 0)
            total_links = metrics.get('total_internal_links', 0)
            total_external = metrics.get('total_external_links', 0)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Knowledge graph rebuild complete! '
                    f'Found {total_posts} posts, {total_links} internal links, and {total_external} external links.'
                )
            )
            
            # Show additional info if there are errors
            if graph_data.get('errors'):
                self.stdout.write(
                    self.style.WARNING(f'Encountered errors: {graph_data["errors"]}')
                )
            
            # Show some interesting metrics
            if metrics:
                most_linked = metrics.get('most_linked_posts', [])
                if most_linked:
                    self.stdout.write(
                        self.style.SUCCESS('Most connected posts:')
                    )
                    for post in most_linked[:3]:  # Show top 3
                        self.stdout.write(f'  - {post["label"]}: {post["connections"]} connections')
                
                orphan_posts = metrics.get('orphan_posts', [])
                if orphan_posts:
                    self.stdout.write(
                        self.style.WARNING(f'Found {len(orphan_posts)} posts with no connections:')
                    )
                    for post in orphan_posts:
                        self.stdout.write(f'  - {post["label"]}')
            
            # Test API endpoint if requested
            if options['test_api']:
                self.stdout.write('Testing knowledge graph API endpoint...')
                try:
                    from django.test import Client
                    from django.urls import reverse
                    
                    client = Client()
                    response = client.get('/api/knowledge-graph/')
                    
                    if response.status_code == 200:
                        self.stdout.write(
                            self.style.SUCCESS('API endpoint test successful!')
                        )
                    else:
                        self.stdout.write(
                            self.style.ERROR(f'API endpoint test failed with status {response.status_code}')
                        )
                except Exception as api_error:
                    self.stdout.write(
                        self.style.ERROR(f'API endpoint test error: {api_error}')
                    )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error rebuilding knowledge graph: {e}')
            )
