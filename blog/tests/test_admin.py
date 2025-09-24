from django.test import TestCase, Client
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.urls import reverse
from unittest.mock import MagicMock, patch
from blog.models import BlogComment, CommentVote
from blog.admin import BlogCommentAdmin

User = get_user_model()


class BlogCommentAdminTest(TestCase):
    """Test BlogComment admin interface."""

    def setUp(self):
        self.site = AdminSite()
        self.admin = BlogCommentAdmin(BlogComment, self.site)
        self.superuser = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='admin123'
        )
        self.staff_user = User.objects.create_user(
            username='staff',
            email='staff@example.com',
            password='staff123',
            is_staff=True
        )
        self.regular_user = User.objects.create_user(
            username='regular',
            email='regular@example.com',
            password='regular123'
        )
        self.comment = BlogComment.objects.create(
            blog_template_name='0001_test_post',
            blog_category='tech',
            content='Test comment',
            author=self.regular_user,
            status='pending'
        )

    def test_list_display_fields(self):
        """Test that list display shows correct fields."""
        expected_fields = [
            'id', 
            'get_author_display', 
            'get_blog_post',
            'truncated_content', 
            'status_badge',
            'created_at',
            'is_reply',
            'replies_count'
        ]
        
        self.assertEqual(self.admin.list_display, expected_fields)

    def test_get_author_display_staff(self):
        """Test author display for staff users."""
        comment = BlogComment.objects.create(
            blog_template_name='test',
            content='Staff comment',
            author=self.staff_user
        )
        
        display = self.admin.get_author_display(comment)
        
        self.assertIn('staff', display)
        self.assertIn('👤', display)
        self.assertIn('color: #0066cc', display)  # Staff color

    def test_get_author_display_regular(self):
        """Test author display for regular users."""
        display = self.admin.get_author_display(self.comment)
        
        self.assertIn('regular', display)
        self.assertIn('👤', display)
        self.assertNotIn('color: #0066cc', display)  # No staff color

    def test_get_author_display_anonymous(self):
        """Test author display for anonymous users."""
        comment = BlogComment.objects.create(
            blog_template_name='test',
            content='Anonymous comment',
            author_name='John Doe'
        )
        
        display = self.admin.get_author_display(comment)
        
        self.assertIn('John Doe', display)
        self.assertIn('💭', display)  # Anonymous icon

    def test_get_blog_post_with_category(self):
        """Test blog post display with category."""
        display = self.admin.get_blog_post(self.comment)
        
        self.assertIn('tech/0001_test_post', display)
        self.assertIn('href="/b/tech/0001_test_post/"', display)

    def test_get_blog_post_without_category(self):
        """Test blog post display without category."""
        comment = BlogComment.objects.create(
            blog_template_name='test_post',
            content='Test'
        )
        
        display = self.admin.get_blog_post(comment)
        
        self.assertIn('test_post', display)
        self.assertIn('href="/b/test_post/"', display)

    def test_truncated_content(self):
        """Test content truncation in list view."""
        # Short content
        short_comment = BlogComment.objects.create(
            blog_template_name='test',
            content='Short'
        )
        self.assertEqual(self.admin.truncated_content(short_comment), 'Short')
        
        # Long content
        long_content = 'x' * 100
        long_comment = BlogComment.objects.create(
            blog_template_name='test',
            content=long_content
        )
        truncated = self.admin.truncated_content(long_comment)
        self.assertEqual(len(truncated), 53)  # 50 chars + '...'
        self.assertTrue(truncated.endswith('...'))

    def test_status_badge(self):
        """Test status badge display with colors."""
        # Pending
        self.comment.status = 'pending'
        badge = self.admin.status_badge(self.comment)
        self.assertIn('#FFA500', badge)  # Orange
        self.assertIn('Pending Review', badge)
        
        # Approved
        self.comment.status = 'approved'
        badge = self.admin.status_badge(self.comment)
        self.assertIn('#28a745', badge)  # Green
        self.assertIn('Approved', badge)
        
        # Rejected
        self.comment.status = 'rejected'
        badge = self.admin.status_badge(self.comment)
        self.assertIn('#dc3545', badge)  # Red
        self.assertIn('Rejected', badge)
        
        # Spam
        self.comment.status = 'spam'
        badge = self.admin.status_badge(self.comment)
        self.assertIn('#6c757d', badge)  # Gray
        self.assertIn('Spam', badge)

    def test_is_reply(self):
        """Test reply indicator."""
        # Not a reply
        self.assertEqual(self.admin.is_reply(self.comment), '✗')
        
        # Is a reply
        reply = BlogComment.objects.create(
            blog_template_name='test',
            content='Reply',
            parent=self.comment
        )
        self.assertEqual(self.admin.is_reply(reply), '✓')

    def test_replies_count(self):
        """Test replies count display."""
        # No replies
        self.assertEqual(self.admin.replies_count(self.comment), '0')
        
        # Add approved reply
        BlogComment.objects.create(
            blog_template_name='test',
            content='Reply',
            parent=self.comment,
            status='approved'
        )
        self.assertIn('<strong>1</strong>', self.admin.replies_count(self.comment))
        
        # Pending reply shouldn't count
        BlogComment.objects.create(
            blog_template_name='test',
            content='Pending reply',
            parent=self.comment,
            status='pending'
        )
        self.assertIn('<strong>1</strong>', self.admin.replies_count(self.comment))

    def test_approve_comments_action(self):
        """Test bulk approve action."""
        request = MagicMock()
        request.user = self.staff_user
        
        queryset = BlogComment.objects.filter(id=self.comment.id)
        self.admin.approve_comments(request, queryset)
        
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.status, 'approved')
        self.assertEqual(self.comment.moderated_by, self.staff_user)

    def test_reject_comments_action(self):
        """Test bulk reject action."""
        request = MagicMock()
        request.user = self.staff_user
        
        queryset = BlogComment.objects.filter(id=self.comment.id)
        self.admin.reject_comments(request, queryset)
        
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.status, 'rejected')

    def test_mark_as_spam_action(self):
        """Test bulk mark as spam action."""
        request = MagicMock()
        request.user = self.staff_user
        
        queryset = BlogComment.objects.filter(id=self.comment.id)
        self.admin.mark_as_spam(request, queryset)
        
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.status, 'spam')

    def test_get_queryset_optimization(self):
        """Test that queryset includes necessary optimizations."""
        request = MagicMock()
        queryset = self.admin.get_queryset(request)
        
        # Check that select_related is used
        self.assertIn('author', queryset._prefetch_related_lookups)
        
        # Check that annotations are added
        # Note: This is implementation-specific and might need adjustment

    def test_has_change_permission(self):
        """Test change permission based on user type."""
        request = MagicMock()
        
        # Staff should have permission
        request.user = self.staff_user
        self.assertTrue(self.admin.has_change_permission(request))
        
        # Regular user should not
        request.user = self.regular_user
        self.assertFalse(self.admin.has_change_permission(request))

    def test_has_add_permission(self):
        """Test that adding comments through admin is disabled."""
        request = MagicMock()
        
        # Even superuser shouldn't add comments through admin
        request.user = self.superuser
        self.assertFalse(self.admin.has_add_permission(request))

    def test_has_delete_permission(self):
        """Test delete permission is superuser only."""
        request = MagicMock()
        
        # Superuser should have permission
        request.user = self.superuser
        self.assertTrue(self.admin.has_delete_permission(request))
        
        # Staff should not
        request.user = self.staff_user
        self.assertFalse(self.admin.has_delete_permission(request))

    def test_list_filter(self):
        """Test available list filters."""
        expected_filters = [
            'status',
            'created_at',
            'blog_category',
        ]
        
        for filter_field in expected_filters:
            self.assertIn(filter_field, [f if isinstance(f, str) else f[0] for f in self.admin.list_filter])

    def test_search_fields(self):
        """Test searchable fields."""
        expected_search_fields = [
            'content',
            'author__username',
            'author__email',
            'author_name',
            'author_email',
            'blog_template_name',
            'ip_address'
        ]
        
        for field in expected_search_fields:
            self.assertIn(field, self.admin.search_fields)

    def test_readonly_fields(self):
        """Test that certain fields are read-only."""
        readonly_fields = [
            'created_at',
            'updated_at',
            'ip_address',
            'user_agent',
            'moderated_at',
            'moderated_by',
            'is_edited',
            'edited_at'
        ]
        
        for field in readonly_fields:
            self.assertIn(field, self.admin.readonly_fields)

    def test_fieldsets(self):
        """Test admin fieldset configuration."""
        fieldsets = dict(self.admin.fieldsets)
        
        # Check main sections exist
        self.assertIn('Blog Post', fieldsets)
        self.assertIn('Author Information', fieldsets)
        self.assertIn('Comment', fieldsets)
        self.assertIn('Moderation', fieldsets)
        self.assertIn('Metadata', fieldsets)
        
        # Check collapsible sections
        moderation_classes = fieldsets['Moderation'].get('classes', ())
        self.assertIn('collapse', moderation_classes)
        
        metadata_classes = fieldsets['Metadata'].get('classes', ())
        self.assertIn('collapse', metadata_classes)

    def test_date_hierarchy(self):
        """Test date hierarchy is set."""
        self.assertEqual(self.admin.date_hierarchy, 'created_at')

    def test_actions(self):
        """Test available admin actions."""
        expected_actions = [
            'approve_comments',
            'reject_comments', 
            'mark_as_spam'
        ]
        
        for action in expected_actions:
            self.assertIn(action, self.admin.actions)


class AdminIntegrationTest(TestCase):
    """Test admin interface integration."""

    def setUp(self):
        self.client = Client()
        self.superuser = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='admin123'
        )
        self.comment = BlogComment.objects.create(
            blog_template_name='0001_test_post',
            blog_category='tech',
            content='Test comment',
            status='pending'
        )

    def test_admin_changelist_view(self):
        """Test admin changelist view renders."""
        self.client.login(username='admin', password='admin123')
        
        url = reverse('admin:blog_blogcomment_changelist')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Blog Comments')
        self.assertContains(response, 'Test comment')

    def test_admin_change_view(self):
        """Test admin change view for a comment."""
        self.client.login(username='admin', password='admin123')
        
        url = reverse('admin:blog_blogcomment_change', args=[self.comment.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test comment')
        self.assertContains(response, '0001_test_post')

    def test_admin_actions_in_changelist(self):
        """Test that custom actions appear in changelist."""
        self.client.login(username='admin', password='admin123')
        
        url = reverse('admin:blog_blogcomment_changelist')
        response = self.client.get(url)
        
        self.assertContains(response, 'Approve selected comments')
        self.assertContains(response, 'Reject selected comments')
        self.assertContains(response, 'Mark selected as spam')

    def test_admin_cannot_add_comment(self):
        """Test that add button is not available."""
        self.client.login(username='admin', password='admin123')
        
        url = reverse('admin:blog_blogcomment_changelist')
        response = self.client.get(url)
        
        # Add button should not be present
        self.assertNotContains(response, 'Add blog comment')

    def test_admin_filters_work(self):
        """Test that filters in admin work correctly."""
        # Create comments with different statuses
        BlogComment.objects.create(
            blog_template_name='test',
            content='Approved',
            status='approved'
        )
        BlogComment.objects.create(
            blog_template_name='test',
            content='Spam',
            status='spam'
        )
        
        self.client.login(username='admin', password='admin123')
        
        # Filter by pending status
        url = reverse('admin:blog_blogcomment_changelist') + '?status=pending'
        response = self.client.get(url)
        
        self.assertContains(response, 'Test comment')
        self.assertNotContains(response, 'Approved')
        self.assertNotContains(response, 'Spam')

    def test_admin_search(self):
        """Test admin search functionality."""
        BlogComment.objects.create(
            blog_template_name='test',
            content='Unique search term xyz123'
        )
        
        self.client.login(username='admin', password='admin123')
        
        url = reverse('admin:blog_blogcomment_changelist') + '?q=xyz123'
        response = self.client.get(url)
        
        self.assertContains(response, 'Unique search term')
        self.assertNotContains(response, 'Test comment')
