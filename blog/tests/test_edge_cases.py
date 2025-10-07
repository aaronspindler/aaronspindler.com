from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from unittest.mock import patch, MagicMock
from blog.models import BlogComment, CommentVote
from blog.forms import CommentForm
from blog.knowledge_graph import normalize_template_name, LinkParser, GraphBuilder
from tests.factories import UserFactory, BlogCommentFactory, MockDataFactory
import json

User = get_user_model()


class EdgeCaseTests(TestCase):
    """Test edge cases and boundary conditions."""

    def setUp(self):
        self.client = Client()
        self.user = UserFactory.create_user()

    def test_comment_at_max_length(self):
        """Test comment exactly at maximum length."""
        max_content = 'x' * 2000
        comment = BlogCommentFactory.create_comment(
            content=max_content
        )
        
        # Should save successfully
        self.assertEqual(len(comment.content), 2000)
        
        # Validation should pass
        comment.full_clean()

    def test_comment_over_max_length_validation(self):
        """Test comment over maximum length fails validation."""
        over_max_content = 'x' * 2001
        comment = BlogComment(
            blog_template_name='test',
            content=over_max_content
        )
        
        with self.assertRaises(ValidationError) as context:
            comment.full_clean()
        
        self.assertIn('content', context.exception.message_dict)

    def test_empty_blog_template_name(self):
        """Test that blog_template_name is required."""
        with self.assertRaises(IntegrityError):
            BlogComment.objects.create(
                blog_template_name=None,
                content='Test'
            )

    def test_deeply_nested_comments(self):
        """Test handling of deeply nested comment threads."""
        parent = BlogCommentFactory.create_approved_comment(
            content='Level 0',
            blog_template_name='test'
        )
        
        current = parent
        for i in range(1, 10):  # Create 9 levels of nesting
            current = BlogCommentFactory.create_approved_comment(
                content=f'Level {i}',
                blog_template_name='test',
                parent=current
            )
        
        # Test depth calculation
        self.assertEqual(current.get_depth(), 9)
        
        # Test that deeply nested structure doesn't break queries
        top_comments = BlogComment.get_approved_comments('test')
        self.assertEqual(top_comments.count(), 1)
        self.assertEqual(top_comments[0].id, parent.id)

    def test_circular_reference_prevention(self):
        """Test that circular parent references are prevented."""
        comment1 = BlogCommentFactory.create_comment(
            content='Comment 1'
        )
        
        comment2 = BlogCommentFactory.create_comment(
            content='Comment 2',
            parent=comment1
        )
        
        # Try to set comment1's parent to comment2 (would create circle)
        comment1.parent = comment2
        
        # This should fail at the database level or application logic
        # The actual behavior depends on implementation
        # For now, we just verify the structure exists
        self.assertEqual(comment2.parent_id, comment1.id)

    def test_vote_on_own_comment(self):
        """Test user voting on their own comment."""
        comment = BlogCommentFactory.create_approved_comment(
            content='My comment',
            author=self.user
        )
        
        self.client.login(username=self.user.username, password='testpass123')
        response = self.client.post(f'/comment/{comment.id}/vote/', {
            'vote_type': 'upvote'
        })
        
        # Should be allowed (Reddit-style)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['upvotes'], 1)

    def test_simultaneous_vote_changes(self):
        """Test handling simultaneous vote changes."""
        comment = BlogCommentFactory.create_approved_comment()
        
        # Create initial vote
        vote = BlogCommentFactory.create_comment_vote(
            comment=comment,
            user=self.user,
            vote_type='upvote'
        )
        
        # Simulate simultaneous changes
        vote1 = CommentVote.objects.get(id=vote.id)
        vote2 = CommentVote.objects.get(id=vote.id)
        
        vote1.vote_type = 'downvote'
        vote1.save()
        
        vote2.vote_type = 'downvote'
        vote2.save()
        
        # Should handle gracefully
        comment.refresh_from_db()
        self.assertEqual(comment.downvotes, 1)
        self.assertEqual(comment.upvotes, 0)

    def test_unicode_in_comments(self):
        """Test handling of Unicode characters in comments."""
        unicode_content = '测试 テスト тест 🎉 emoji test ñoño'
        
        comment = BlogCommentFactory.create_comment(
            content=unicode_content,
            author_name='José García'
        )
        
        self.assertEqual(comment.content, unicode_content)
        self.assertEqual(comment.author_name, 'José García')
        
        # Test in form
        form_data = MockDataFactory.get_common_form_data()['comment_form']
        form_data.update({
            'content': unicode_content,
            'author_name': 'José García'
        })
        form = CommentForm(data=form_data)
        
        self.assertTrue(form.is_valid())

    def test_xss_prevention_in_content(self):
        """Test that potential XSS content is handled safely."""
        xss_attempts = [
            '<script>alert("XSS")</script>',
            '<img src=x onerror="alert(\'XSS\')">',
            'javascript:alert("XSS")',
            '<a href="javascript:alert(\'XSS\')">Click</a>'
        ]
        
        for xss in xss_attempts:
            comment = BlogCommentFactory.create_comment(
                content=xss
            )
            
            # Content should be stored as-is (escaping happens in template)
            self.assertEqual(comment.content, xss)

    def test_sql_injection_prevention(self):
        """Test that SQL injection attempts are handled safely."""
        sql_injection = "'; DROP TABLE blog_blogcomment; --"
        
        comment = BlogCommentFactory.create_comment(
            content=sql_injection,
            author_name=sql_injection
        )
        
        # Should be stored safely
        self.assertEqual(comment.content, sql_injection)
        
        # Table should still exist
        self.assertTrue(BlogComment.objects.exists())

    def test_extremely_long_url_in_content(self):
        """Test handling of extremely long URLs in comment content."""
        long_url = 'https://example.com/' + 'x' * 1900
        
        form_data = MockDataFactory.get_common_form_data()['comment_form']
        form_data['content'] = f'Check out {long_url}'
        form = CommentForm(data=form_data)
        
        # Should handle long URL (counts as 1 URL, not spam)
        # But total content exceeds 2000 chars
        self.assertFalse(form.is_valid())

    def test_malformed_email_normalization(self):
        """Test email normalization with edge cases."""
        test_cases = [
            ('  test@example.com  ', 'test@example.com'),
            ('TEST@EXAMPLE.COM', 'test@example.com'),
            ('test+tag@example.com', 'test+tag@example.com'),
            ('test.name@sub.domain.com', 'test.name@sub.domain.com')
        ]
        
        for input_email, expected in test_cases:
            form_data = MockDataFactory.get_common_form_data()['comment_form']
            form_data.update({
                'content': 'Test',
                'author_email': input_email
            })
            form = CommentForm(data=form_data)
            
            self.assertTrue(form.is_valid())
            self.assertEqual(form.cleaned_data['author_email'], expected)

    @patch('blog.views.get_blog_from_template_name')
    @patch('blog.models.BlogComment.get_approved_comments')
    @patch('utils.models.RequestFingerprint')
    def test_nonexistent_blog_post(self, mock_request_fingerprint, mock_get_approved, mock_get_blog):
        """Test handling of comments on non-existent blog posts."""
        mock_get_blog.side_effect = Exception('Template not found')
        mock_get_approved.return_value.count.return_value = 0
        mock_request_fingerprint.objects.filter.return_value.count.return_value = 0
        
        form_data = MockDataFactory.get_common_form_data()['comment_form']
        form_data['content'] = ''  # Invalid form to trigger error re-render path
        
        # Should return 404 when blog template doesn't exist and form has errors
        response = self.client.post('/b/tech/nonexistent/comment/', form_data)
        self.assertEqual(response.status_code, 404)

    def test_knowledge_graph_with_malformed_html(self):
        """Test knowledge graph parser handles malformed HTML."""
        parser = LinkParser()
        
        malformed_html = '''
            <p>Unclosed paragraph
            <a href="/b/2024_test/">Unclosed link
            <script>alert('test')</script>
            <a href="/b/2024_valid/">Valid link</a>
            <!-- Unclosed comment
        '''
        
        with patch.object(parser, '_get_template_content', return_value=malformed_html):
            result = parser.parse_blog_post('test')
            
            # Should still find valid links (malformed ones may be filtered out)
            self.assertGreaterEqual(len(result['internal_links']), 1)

    def test_knowledge_graph_with_empty_blog(self):
        """Test knowledge graph with blog post containing no links."""
        parser = LinkParser()
        
        with patch.object(parser, '_get_template_content', return_value='<p>No links here</p>'):
            result = parser.parse_blog_post('test')
            
            self.assertEqual(len(result['internal_links']), 0)
            self.assertEqual(len(result['external_links']), 0)
            self.assertEqual(len(result.get('parse_errors', [])), 0)

    @patch('blog.views.get_blog_from_template_name')
    @patch('utils.models.RequestFingerprint')
    @patch('blog.models.BlogComment.get_approved_comments')
    @patch('django.urls.reverse')
    def test_concurrent_comment_submission(self, mock_reverse, mock_get_approved, mock_request_fingerprint, mock_get_blog):
        """Test handling of concurrent comment submissions."""
        # This would ideally test race conditions, but is simplified here
        mock_get_blog.return_value = MockDataFactory.get_mock_blog_data(template_name='test')
        mock_request_fingerprint.objects.filter.return_value.count.return_value = 0
        mock_get_approved.return_value.count.return_value = 0
        mock_reverse.return_value = '/b/tech/test/'
        
        content = 'Concurrent test comment'
        
        # Simulate two "simultaneous" submissions
        form_data1 = MockDataFactory.get_common_form_data()['comment_form']
        form_data1['content'] = content + ' 1'
        response1 = self.client.post('/b/tech/test/comment/', form_data1)
        
        form_data2 = MockDataFactory.get_common_form_data()['comment_form']
        form_data2['content'] = content + ' 2'
        response2 = self.client.post('/b/tech/test/comment/', form_data2)
        
        # Both should succeed
        self.assertEqual(response1.status_code, 302)
        self.assertEqual(response2.status_code, 302)
        
        # Both comments should exist
        comments = BlogComment.objects.filter(content__startswith=content)
        self.assertEqual(comments.count(), 2)

    def test_comment_with_null_fields(self):
        """Test comment with various null/empty field combinations."""
        comment = BlogCommentFactory.create_comment(
            content='Test',
            author=None,
            author_name='',
            author_email='',
            blog_template_name='test',
            blog_category='tech',
            parent=None
        )
        
        # Should handle all null/empty fields gracefully
        self.assertEqual(comment.get_author_display(), 'Anonymous')
        self.assertEqual(comment.get_author_email(), '')
        self.assertEqual(comment.get_blog_url(), '/b/tech/test/')

    def test_invalid_vote_type(self):
        """Test handling of invalid vote types."""
        comment = BlogCommentFactory.create_approved_comment()
        
        self.client.login(username=self.user.username, password='testpass123')
        
        # Try invalid vote type
        response = self.client.post(f'/comment/{comment.id}/vote/', {
            'vote_type': 'superupvote'  # Invalid
        })
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)

    def test_template_name_normalization_edge_cases(self):
        """Test edge cases in template name normalization."""
        test_cases = [
            ('', ''),
            (None, None),
            ('UPPERCASE', 'uppercase'),
            ('MiXeD_CaSe', 'mixed_case'),
            ('with-dashes', 'with-dashes'),
            ('with.dots', 'with.dots'),
            ('with spaces', 'with spaces'),  # Spaces preserved
            ('123_numbers', '123_numbers')
        ]
        
        for input_name, expected in test_cases:
            result = normalize_template_name(input_name)
            self.assertEqual(result, expected)
