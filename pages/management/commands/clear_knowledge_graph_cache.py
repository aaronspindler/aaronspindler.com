import logging
from django.core.management.base import BaseCommand, CommandError
from django.core.cache import cache

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Clear knowledge graph cache entries and optionally rebuild the graph'

    def add_arguments(self, parser):
        parser.add_argument(
            '--rebuild',
            action='store_true',
            help='Rebuild the knowledge graph after clearing cache',
        )
        parser.add_argument(
            '--template',
            type=str,
            help='Clear cache for a specific blog template only',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force clearing without confirmation prompts',
        )
        parser.add_argument(
            '--status',
            action='store_true',
            help='Show current cache status instead of clearing',
        )

    def handle(self, *args, **options):
        try:
            from pages.knowledge_graph import clear_knowledge_graph_cache, build_knowledge_graph
        except ImportError as e:
            raise CommandError(f"Could not import required modules: {e}")

        template_name = options.get('template')
        rebuild = options.get('rebuild', False)
        force = options.get('force', False)
        show_status = options.get('status', False)

        if show_status:
            self.get_cache_status()
            return

        if template_name:
            # Clear cache for specific template
            self.clear_template_cache(template_name, force)
        else:
            # Clear all knowledge graph caches
            self.clear_all_cache(force)
        
        if rebuild:
            self.stdout.write(self.style.SUCCESS('Rebuilding knowledge graph...'))
            try:
                graph = build_knowledge_graph(force_refresh=True)
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully rebuilt knowledge graph with {len(graph.get("nodes", []))} nodes '
                        f'and {len(graph.get("edges", []))} edges'
                    )
                )
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Failed to rebuild knowledge graph: {e}'))
                logger.error(f'Knowledge graph rebuild failed: {e}')

    def clear_template_cache(self, template_name, force=False):
        """Clear cache for a specific blog template."""
        if not force:
            confirm = input(f'Clear cache for template "{template_name}"? [y/N]: ')
            if confirm.lower() not in ['y', 'yes']:
                self.stdout.write('Cancelled.')
                return

        try:
            # Clear individual post link cache
            post_cache_key = f'blog:links:{template_name}'
            cache.delete(post_cache_key)
            cache.delete(f'{post_cache_key}:meta')
            
            # Clear post-specific graph caches (all depths)
            for depth in range(1, 4):
                post_graph_key = f'blog:graph:post:{template_name}:depth:{depth}'
                cache.delete(post_graph_key)
            
            # Clear complete graph cache since it depends on all templates
            cache.delete('blog:graph:complete')
            
            self.stdout.write(
                self.style.SUCCESS(f'Successfully cleared cache for template: {template_name}')
            )
            logger.info(f'Manually cleared cache for template: {template_name}')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error clearing cache for template {template_name}: {e}'))
            logger.error(f'Failed to clear cache for template {template_name}: {e}')

    def clear_all_cache(self, force=False):
        """Clear all knowledge graph related caches."""
        if not force:
            confirm = input('Clear all knowledge graph caches? [y/N]: ')
            if confirm.lower() not in ['y', 'yes']:
                self.stdout.write('Cancelled.')
                return

        try:
            from pages.knowledge_graph import clear_knowledge_graph_cache
            clear_knowledge_graph_cache()
            
            self.stdout.write(
                self.style.SUCCESS('Successfully cleared all knowledge graph caches')
            )
            logger.info('Manually cleared all knowledge graph caches')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error clearing all caches: {e}'))
            logger.error(f'Failed to clear all caches: {e}')

    def get_cache_status(self):
        """Get current cache status information."""
        try:
            from pages.knowledge_graph import GraphBuilder
            
            graph_builder = GraphBuilder()
            blog_templates = graph_builder._get_all_blog_templates()
            
            self.stdout.write(self.style.HTTP_INFO('Current cache status:'))
            
            # Check complete graph cache
            complete_graph = cache.get('blog:graph:complete')
            if complete_graph:
                self.stdout.write('  Complete graph: CACHED')
            else:
                self.stdout.write('  Complete graph: NOT CACHED')
            
            # Check individual post caches
            cached_posts = 0
            for template_name in blog_templates:
                post_cache_key = f'blog:links:{template_name}'
                if cache.get(post_cache_key):
                    cached_posts += 1
            
            self.stdout.write(f'  Individual posts: {cached_posts}/{len(blog_templates)} cached')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error checking cache status: {e}'))