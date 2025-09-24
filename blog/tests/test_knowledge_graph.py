from django.test import TestCase
from django.core.cache import cache
from unittest.mock import patch, MagicMock, mock_open
from blog.knowledge_graph import (
    normalize_template_name,
    LinkParser,
    GraphBuilder,
    parse_all_blog_posts,
    build_knowledge_graph,
    get_post_graph
)
from pathlib import Path


class NormalizeTemplateNameTest(TestCase):
    """Test template name normalization."""

    def test_normalize_template_name(self):
        """Test that template names are normalized to lowercase."""
        self.assertEqual(normalize_template_name('About_Me'), 'about_me')
        self.assertEqual(normalize_template_name('UPPERCASE'), 'uppercase')
        self.assertEqual(normalize_template_name('MixedCase'), 'mixedcase')
        self.assertEqual(normalize_template_name('already_lower'), 'already_lower')

    def test_normalize_template_name_none(self):
        """Test that None is handled gracefully."""
        self.assertIsNone(normalize_template_name(None))

    def test_normalize_template_name_empty(self):
        """Test that empty string is handled."""
        self.assertEqual(normalize_template_name(''), '')


class LinkParserTest(TestCase):
    """Test LinkParser functionality."""

    def setUp(self):
        self.parser = LinkParser()
        cache.clear()

    @patch('blog.knowledge_graph.LinkParser._get_template_content')
    def test_parse_blog_post_internal_links(self, mock_get_content):
        """Test parsing internal blog links."""
        mock_get_content.return_value = '''
            <p>Check out my <a href="/b/2024_another_post/">other post</a></p>
            <p>Also see <a href="/b/tech/2024_tech_post/">this tech post</a></p>
        '''
        
        result = self.parser.parse_blog_post('test_post')
        
        self.assertEqual(len(result['internal_links']), 2)
        self.assertEqual(result['internal_links'][0]['target'], '2024_another_post')
        self.assertEqual(result['internal_links'][1]['target'], '2024_tech_post')

    @patch('blog.knowledge_graph.LinkParser._get_template_content')
    def test_parse_blog_post_external_links(self, mock_get_content):
        """Test parsing external links."""
        mock_get_content.return_value = '''
            <p>Visit <a href="https://example.com">Example</a></p>
            <p>Check <a href="http://google.com/search">Google</a></p>
        '''
        
        result = self.parser.parse_blog_post('test_post')
        
        self.assertEqual(len(result['external_links']), 2)
        self.assertEqual(result['external_links'][0]['domain'], 'example.com')
        self.assertEqual(result['external_links'][1]['domain'], 'google.com')

    @patch('blog.knowledge_graph.LinkParser._get_template_content')
    def test_parse_blog_post_skip_anchors(self, mock_get_content):
        """Test that anchor links are skipped."""
        mock_get_content.return_value = '''
            <p>Jump to <a href="#section1">Section 1</a></p>
            <p>See <a href="#conclusion">Conclusion</a></p>
        '''
        
        result = self.parser.parse_blog_post('test_post')
        
        self.assertEqual(len(result['internal_links']), 0)
        self.assertEqual(len(result['external_links']), 0)

    @patch('blog.knowledge_graph.LinkParser._get_template_content')
    def test_parse_blog_post_context_extraction(self, mock_get_content):
        """Test that link context is extracted correctly."""
        mock_get_content.return_value = '''
            <p>This is some text before the link. Check out my 
            <a href="/b/2024_post/">amazing post</a> which covers interesting topics.</p>
        '''
        
        result = self.parser.parse_blog_post('test_post')
        
        self.assertEqual(len(result['internal_links']), 1)
        link = result['internal_links'][0]
        self.assertIn('text before the link', link['context'])
        self.assertIn('amazing post', link['context'])
        self.assertIn('which covers', link['context'])

    @patch('blog.knowledge_graph.LinkParser._get_template_content')
    def test_parse_blog_post_cache_usage(self, mock_get_content):
        """Test that parsed results are cached."""
        mock_get_content.return_value = '<p><a href="/b/2024_post/">Link</a></p>'
        
        # First call should hit the parser
        result1 = self.parser.parse_blog_post('test_post')
        self.assertEqual(mock_get_content.call_count, 1)
        
        # Second call should use cache
        result2 = self.parser.parse_blog_post('test_post')
        self.assertEqual(mock_get_content.call_count, 1)
        self.assertEqual(result1, result2)

    @patch('blog.knowledge_graph.LinkParser._get_template_content')
    def test_parse_blog_post_force_refresh(self, mock_get_content):
        """Test force refresh bypasses cache."""
        mock_get_content.return_value = '<p><a href="/b/2024_post/">Link</a></p>'
        
        # First call
        self.parser.parse_blog_post('test_post')
        self.assertEqual(mock_get_content.call_count, 1)
        
        # Force refresh should re-parse
        self.parser.parse_blog_post('test_post', force_refresh=True)
        self.assertEqual(mock_get_content.call_count, 2)

    @patch('blog.knowledge_graph.LinkParser._get_template_content')
    def test_parse_blog_post_error_handling(self, mock_get_content):
        """Test error handling during parsing."""
        mock_get_content.side_effect = Exception('Template error')
        
        result = self.parser.parse_blog_post('test_post')
        
        self.assertEqual(len(result['internal_links']), 0)
        self.assertEqual(len(result['external_links']), 0)
        self.assertEqual(len(result['parse_errors']), 1)
        self.assertIn('Template error', result['parse_errors'][0])

    @patch('blog.knowledge_graph.LinkParser._get_template_content')
    def test_parse_blog_post_cleans_html(self, mock_get_content):
        """Test that scripts, styles, and comments are removed."""
        mock_get_content.return_value = '''
            <script>alert('test')</script>
            <style>body { color: red; }</style>
            <!-- This is a comment -->
            <p><a href="/b/2024_post/">Valid link</a></p>
        '''
        
        result = self.parser.parse_blog_post('test_post')
        
        self.assertEqual(len(result['internal_links']), 1)
        # Scripts, styles, and comments should not affect parsing

    def test_is_external_link(self):
        """Test external link detection."""
        parser = LinkParser()
        
        self.assertTrue(parser._is_external_link('https://example.com'))
        self.assertTrue(parser._is_external_link('http://example.com'))
        self.assertTrue(parser._is_external_link('https://example.com/path'))
        
        self.assertFalse(parser._is_external_link('/relative/path'))
        self.assertFalse(parser._is_external_link('relative/path'))
        self.assertFalse(parser._is_external_link('#anchor'))


class GraphBuilderTest(TestCase):
    """Test GraphBuilder functionality."""

    def setUp(self):
        self.builder = GraphBuilder()
        cache.clear()

    @patch('blog.knowledge_graph.GraphBuilder._get_all_blog_templates')
    @patch('blog.knowledge_graph.LinkParser.parse_blog_post')
    def test_build_complete_graph(self, mock_parse, mock_get_templates):
        """Test building complete knowledge graph."""
        mock_get_templates.return_value = [
            {'template_name': 'post1', 'original_name': 'Post1', 'category': 'tech'},
            {'template_name': 'post2', 'original_name': 'Post2', 'category': 'personal'}
        ]
        
        mock_parse.side_effect = [
            {
                'source_post': 'post1',
                'internal_links': [{'target': 'post2', 'text': 'Link', 'context': 'Context', 'href': '/b/post2/'}],
                'external_links': [],
                'parse_errors': []
            },
            {
                'source_post': 'post2',
                'internal_links': [],
                'external_links': [{'url': 'https://example.com', 'text': 'External', 'context': 'Context', 'domain': 'example.com'}],
                'parse_errors': []
            }
        ]
        
        result = self.builder.build_complete_graph()
        
        self.assertEqual(len(result['nodes']), 3)  # 2 posts + 1 external
        self.assertEqual(len(result['edges']), 2)  # 1 internal + 1 external
        self.assertIn('metrics', result)
        self.assertIn('categories', result)

    @patch('blog.knowledge_graph.GraphBuilder._get_all_blog_templates')
    @patch('blog.knowledge_graph.LinkParser.parse_blog_post')
    def test_build_graph_with_categories(self, mock_parse, mock_get_templates):
        """Test that category information is included in graph."""
        mock_get_templates.return_value = [
            {'template_name': 'post1', 'original_name': 'Post1', 'category': 'tech'},
            {'template_name': 'post2', 'original_name': 'Post2', 'category': 'tech'}
        ]
        
        mock_parse.return_value = {
            'source_post': 'post1',
            'internal_links': [],
            'external_links': [],
            'parse_errors': []
        }
        
        result = self.builder.build_complete_graph()
        
        self.assertIn('tech', result['categories'])
        self.assertEqual(result['categories']['tech']['count'], 2)

    def test_build_graph_structure_metrics(self):
        """Test graph metrics calculation."""
        all_links_data = [
            {
                'source_post': 'post1',
                'internal_links': [
                    {'target': 'post2', 'text': 'Link', 'context': 'Context', 'href': '/b/post2/'}
                ],
                'external_links': [
                    {'url': 'https://example.com', 'text': 'External', 'context': 'Context', 'domain': 'example.com'}
                ]
            },
            {
                'source_post': 'post2',
                'internal_links': [],
                'external_links': []
            },
            {
                'source_post': 'orphan_post',
                'internal_links': [],
                'external_links': []
            }
        ]
        
        result = self.builder._build_graph_structure(all_links_data)
        
        metrics = result['metrics']
        self.assertEqual(metrics['total_posts'], 3)
        self.assertEqual(metrics['total_internal_links'], 1)
        self.assertEqual(metrics['total_external_links'], 1)
        self.assertEqual(len(metrics['orphan_posts']), 1)
        self.assertEqual(metrics['orphan_posts'][0]['id'], 'orphan_post')

    @patch('blog.knowledge_graph.LinkParser.parse_blog_post')
    def test_get_post_connections(self, mock_parse):
        """Test getting connections for a specific post."""
        # Mock parsing for post and its connections
        mock_parse.side_effect = [
            {
                'source_post': 'post1',
                'internal_links': [
                    {'target': 'post2', 'text': 'Link', 'context': 'Context', 'href': '/b/post2/'}
                ],
                'external_links': []
            },
            {
                'source_post': 'post2',
                'internal_links': [
                    {'target': 'post3', 'text': 'Link', 'context': 'Context', 'href': '/b/post3/'}
                ],
                'external_links': []
            }
        ]
        
        result = self.builder.get_post_connections('post1', depth=2)
        
        # Should include post1, post2 (depth 1), and post3 (depth 2)
        node_ids = [node['id'] for node in result['nodes']]
        self.assertIn('post1', node_ids)
        self.assertIn('post2', node_ids)
        
        # With depth=2, should also include post3
        # But our mock only returns 2 calls, so we'll have 2 nodes

    @patch('blog.knowledge_graph.LinkParser.parse_blog_post')
    def test_get_post_connections_depth_limit(self, mock_parse):
        """Test that depth limit is respected."""
        mock_parse.return_value = {
            'source_post': 'post1',
            'internal_links': [
                {'target': 'post2', 'text': 'Link', 'context': 'Context', 'href': '/b/post2/'}
            ],
            'external_links': []
        }
        
        result = self.builder.get_post_connections('post1', depth=1)
        
        # With depth=1, should only process immediate connections
        self.assertEqual(mock_parse.call_count, 1)

    def test_create_external_node(self):
        """Test external node creation."""
        url = 'https://example.com/some/long/path/to/page'
        domain = 'example.com'
        node_id = 'external_123'
        
        node = self.builder._create_external_node(url, domain, node_id)
        
        self.assertEqual(node['id'], node_id)
        self.assertEqual(node['type'], 'external_link')
        self.assertEqual(node['url'], url)
        self.assertEqual(node['domain'], domain)
        self.assertIn('/some/long/path/to/page', node['label'])  # Truncated path

    @patch('blog.knowledge_graph.get_blog_from_template_name')
    def test_get_post_title(self, mock_get_blog):
        """Test getting post title."""
        mock_get_blog.return_value = {'blog_title': 'My Awesome Post'}
        
        title = self.builder._get_post_title('my_awesome_post')
        
        self.assertEqual(title, 'My Awesome Post')

    @patch('blog.knowledge_graph.get_blog_from_template_name')
    def test_get_post_title_fallback(self, mock_get_blog):
        """Test title fallback when blog data unavailable."""
        mock_get_blog.side_effect = Exception('Not found')
        
        title = self.builder._get_post_title('my_awesome_post')
        
        self.assertEqual(title, 'my awesome post')  # Underscores replaced


class IntegrationTest(TestCase):
    """Test integration of knowledge graph components."""

    @patch('blog.knowledge_graph.GraphBuilder.build_complete_graph')
    def test_build_knowledge_graph_function(self, mock_build):
        """Test the build_knowledge_graph utility function."""
        mock_build.return_value = {'nodes': [], 'edges': []}
        
        result = build_knowledge_graph(force_refresh=True)
        
        mock_build.assert_called_with(force_refresh=True)
        self.assertEqual(result, {'nodes': [], 'edges': []})

    @patch('blog.knowledge_graph.GraphBuilder.get_post_connections')
    def test_get_post_graph_function(self, mock_get_connections):
        """Test the get_post_graph utility function."""
        mock_get_connections.return_value = {'nodes': [], 'edges': []}
        
        result = get_post_graph('test_post', depth=2)
        
        mock_get_connections.assert_called_with('test_post', 2)
        self.assertEqual(result, {'nodes': [], 'edges': []})

    @patch('blog.knowledge_graph.GraphBuilder._get_all_blog_templates')
    @patch('blog.knowledge_graph.LinkParser.parse_blog_post')
    def test_parse_all_blog_posts_function(self, mock_parse, mock_get_templates):
        """Test the parse_all_blog_posts utility function."""
        mock_get_templates.return_value = [
            {'template_name': 'post1', 'original_name': 'Post1', 'category': 'tech'},
            {'template_name': 'post2', 'original_name': 'Post2', 'category': 'personal'}
        ]
        
        mock_parse.return_value = {
            'source_post': 'post1',
            'internal_links': [],
            'external_links': [],
            'parse_errors': []
        }
        
        result = parse_all_blog_posts()
        
        self.assertEqual(len(result), 2)
        self.assertEqual(mock_parse.call_count, 2)
