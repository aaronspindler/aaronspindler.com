from django.test import TestCase
from unittest.mock import patch, MagicMock, mock_open
from blog.utils import (
    get_blog_from_template_name,
    find_blog_template,
    get_all_blog_posts
)
from tests.factories import MockDataFactory
import os


class BlogUtilsTest(TestCase):
    """Test blog utility functions."""

    @patch('blog.utils.render_to_string')
    @patch('blog.utils.find_blog_template')
    def test_get_blog_from_template_name_with_category(self, mock_find, mock_render):
        """Test getting blog data with category specified."""
        # Use consistent mock blog data structure
        mock_blog_data = MockDataFactory.get_mock_blog_data()
        mock_render.return_value = mock_blog_data['blog_content']
        
        result = get_blog_from_template_name('0001_test_post', category='tech')
        
        self.assertEqual(result['entry_number'], '0001')
        self.assertEqual(result['template_name'], '0001_test_post')
        self.assertEqual(result['blog_title'], '0001 test post')
        self.assertEqual(result['blog_content'], mock_blog_data['blog_content'])
        self.assertEqual(result['category'], 'tech')
        self.assertIn('github.com', result['github_link'])
        self.assertIn('tech/0001_test_post.html', result['github_link'])
        
        mock_render.assert_called_with('blog/tech/0001_test_post.html')

    @patch('blog.utils.render_to_string')
    @patch('blog.utils.find_blog_template')
    def test_get_blog_from_template_name_without_category(self, mock_find, mock_render):
        """Test getting blog data without category, using search."""
        mock_find.return_value = 'blog/personal/0001_test_post.html'
        mock_render.return_value = '<p>Blog content</p>'
        
        result = get_blog_from_template_name('0001_test_post')
        
        self.assertEqual(result['category'], 'personal')
        mock_find.assert_called_with('0001_test_post')
        mock_render.assert_called_with('blog/personal/0001_test_post.html')

    @patch('blog.utils.render_to_string')
    @patch('blog.utils.find_blog_template')
    def test_get_blog_from_template_name_no_content(self, mock_find, mock_render):
        """Test getting blog metadata without loading content."""
        result = get_blog_from_template_name('0001_test_post', load_content=False, category='tech')
        
        self.assertEqual(result['blog_content'], '')
        mock_render.assert_not_called()

    @patch('blog.utils.render_to_string')
    @patch('blog.utils.find_blog_template')
    def test_get_blog_from_template_name_fallback(self, mock_find, mock_render):
        """Test fallback when template not found via search."""
        mock_find.return_value = None
        mock_render.return_value = '<p>Blog content</p>'
        
        result = get_blog_from_template_name('0001_test_post')
        
        self.assertIsNone(result['category'])
        mock_render.assert_called_with('blog/0001_test_post.html')

    @patch('blog.utils.os.path.exists')
    @patch('blog.utils.os.listdir')
    def test_find_blog_template_in_root(self, mock_listdir, mock_exists):
        """Test finding template in root blog directory."""
        # Mock file exists in root
        mock_exists.side_effect = lambda path: '0001_test_post.html' in path and 'blog/' in path and 'tech' not in path
        
        result = find_blog_template('0001_test_post')
        
        self.assertEqual(result, 'blog/0001_test_post.html')

    @patch('blog.utils.os.path.exists')
    @patch('blog.utils.os.listdir')
    @patch('blog.utils.os.path.isdir')
    def test_find_blog_template_in_category(self, mock_isdir, mock_listdir, mock_exists):
        """Test finding template in category subdirectory."""
        mock_listdir.return_value = ['tech', 'personal']
        mock_isdir.return_value = True
        
        # Mock file exists only in tech category
        def exists_side_effect(path):
            return '0001_test_post.html' in path and 'tech' in path
        
        mock_exists.side_effect = exists_side_effect
        
        result = find_blog_template('0001_test_post')
        
        self.assertEqual(result, 'blog/tech/0001_test_post.html')

    @patch('blog.utils.os.path.exists')
    @patch('blog.utils.os.listdir')
    def test_find_blog_template_not_found(self, mock_listdir, mock_exists):
        """Test when template is not found anywhere."""
        mock_exists.return_value = False
        mock_listdir.return_value = []
        
        result = find_blog_template('nonexistent_post')
        
        self.assertIsNone(result)

    @patch('blog.utils.os.walk')
    @patch('blog.utils.os.path.relpath')
    def test_get_all_blog_posts(self, mock_relpath, mock_walk):
        """Test getting all blog posts from directory structure."""
        # Mock os.walk to return blog structure
        mock_walk.return_value = [
            ('/path/to/templates/blog', ['tech', 'personal'], ['0001_root.html']),
            ('/path/to/templates/blog/tech', [], ['0002_tech_post.html', '0003_another_tech.html']),
            ('/path/to/templates/blog/personal', [], ['0004_personal.html'])
        ]
        
        # Mock os.path.relpath to return appropriate relative paths
        def mock_relpath_side_effect(path, start):
            if path == '/path/to/templates/blog':
                return '.'
            elif path == '/path/to/templates/blog/tech':
                return 'tech'
            elif path == '/path/to/templates/blog/personal':
                return 'personal'
            return path
        
        mock_relpath.side_effect = mock_relpath_side_effect
        
        result = get_all_blog_posts()
        
        self.assertEqual(len(result), 4)
        
        # Check root level post
        root_post = next(p for p in result if p['template_name'] == '0001_root')
        self.assertIsNone(root_post['category'])  # Root level posts have no category
        
        # Check categorized posts
        tech_posts = [p for p in result if p['category'] == 'tech']
        self.assertEqual(len(tech_posts), 2)
        
        personal_posts = [p for p in result if p['category'] == 'personal']
        self.assertEqual(len(personal_posts), 1)

    @patch('blog.utils.os.walk')
    def test_get_all_blog_posts_nested_categories(self, mock_walk):
        """Test that nested category directories are handled correctly."""
        mock_walk.return_value = [
            ('/path/to/templates/blog', ['tech'], []),
            ('/path/to/templates/blog/tech', ['subcategory'], ['0001_tech.html']),
            ('/path/to/templates/blog/tech/subcategory', [], ['0002_nested.html'])
        ]
        
        # Mock os.path.relpath to return the expected relative paths
        with patch('blog.utils.os.path.relpath') as mock_relpath:
            mock_relpath.side_effect = [
                '.',  # Root directory
                'tech',  # Tech category
                'tech/subcategory'  # Nested category
            ]
            
            result = get_all_blog_posts()
            
            # First-level category
            tech_post = next(p for p in result if p['template_name'] == '0001_tech')
            self.assertEqual(tech_post['category'], 'tech')
            
            # Nested category should use first-level category
            nested_post = next(p for p in result if p['template_name'] == '0002_nested')
            self.assertEqual(nested_post['category'], 'tech')

    @patch('blog.utils.os.walk')
    def test_get_all_blog_posts_ignores_non_html(self, mock_walk):
        """Test that non-HTML files are ignored."""
        mock_walk.return_value = [
            ('/path/to/templates/blog', [], [
                '0001_post.html',
                'README.md',
                'style.css',
                '.DS_Store'
            ])
        ]
        
        result = get_all_blog_posts()
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['template_name'], '0001_post')
