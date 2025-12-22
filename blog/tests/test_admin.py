from unittest.mock import MagicMock

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from accounts.tests.factories import UserFactory
from blog.admin import BlogCommentAdmin
from blog.models import BlogComment
from blog.tests.factories import BlogCommentFactory

User = get_user_model()


class BlogCommentAdminTest(TestCase):
    def setUp(self):
        self.site = AdminSite()
        self.admin = BlogCommentAdmin(BlogComment, self.site)
        self.user = UserFactory.create_user()
        self.staff_user = UserFactory.create_staff_user()
        self.superuser = UserFactory.create_superuser()
        self.comment = BlogCommentFactory.create_comment(author=self.user, status="pending")

    def test_list_display_fields(self):
        expected_fields = [
            "id",
            "get_author_display",
            "get_blog_post",
            "truncated_content",
            "status_badge",
            "created_at",
            "is_reply",
            "replies_count",
        ]

        self.assertEqual(self.admin.list_display, expected_fields)

    def test_get_author_display_staff(self):
        comment = BlogCommentFactory.create_comment(author=self.staff_user, content="Staff comment")

        display = self.admin.get_author_display(comment)

        self.assertIn(self.staff_user.username, display)
        self.assertIn("👤", display)
        self.assertIn("color: #0066cc", display)  # Staff color

    def test_get_author_display_regular(self):
        display = self.admin.get_author_display(self.comment)

        self.assertIn(self.user.username, display)
        self.assertIn("👤", display)
        self.assertNotIn("color: #0066cc", display)  # No staff color

    def test_get_author_display_anonymous(self):
        comment = BlogCommentFactory.create_anonymous_comment(content="Anonymous comment")

        display = self.admin.get_author_display(comment)

        self.assertIn("John Doe", display)
        self.assertIn("💭", display)  # Anonymous icon

    def test_get_blog_post_with_category(self):
        display = self.admin.get_blog_post(self.comment)

        self.assertIn("tech/0001_test_post", display)
        self.assertIn('href="/b/tech/0001_test_post/"', display)

    def test_truncated_content(self):
        short_comment = BlogCommentFactory.create_comment(content="Short")
        self.assertEqual(self.admin.truncated_content(short_comment), "Short")

        long_content = "x" * 100
        long_comment = BlogCommentFactory.create_comment(content=long_content)
        truncated = self.admin.truncated_content(long_comment)
        self.assertEqual(len(truncated), 53)  # 50 chars + '...'
        self.assertTrue(truncated.endswith("..."))

    def test_status_badge(self):
        self.comment.status = "pending"
        badge = self.admin.status_badge(self.comment)
        self.assertIn("#FFA500", badge)  # Orange
        self.assertIn("Pending Review", badge)

        self.comment.status = "approved"
        badge = self.admin.status_badge(self.comment)
        self.assertIn("#28a745", badge)  # Green
        self.assertIn("Approved", badge)

        self.comment.status = "rejected"
        badge = self.admin.status_badge(self.comment)
        self.assertIn("#dc3545", badge)  # Red
        self.assertIn("Rejected", badge)

        self.comment.status = "spam"
        badge = self.admin.status_badge(self.comment)
        self.assertIn("#6c757d", badge)  # Gray
        self.assertIn("Spam", badge)

    def test_is_reply(self):
        self.assertEqual(self.admin.is_reply(self.comment), "✗")

        reply = BlogCommentFactory.create_comment(content="Reply", parent=self.comment)
        self.assertEqual(self.admin.is_reply(reply), "✓")

    def test_replies_count(self):
        self.assertEqual(self.admin.replies_count(self.comment), "0")

        BlogCommentFactory.create_approved_comment(content="Reply", parent=self.comment)
        self.assertIn("<strong>1</strong>", self.admin.replies_count(self.comment))

        BlogCommentFactory.create_pending_comment(content="Pending reply", parent=self.comment)
        self.assertIn("<strong>1</strong>", self.admin.replies_count(self.comment))

    def test_approve_comments_action(self):
        request = MagicMock()
        request.user = self.staff_user

        queryset = BlogComment.objects.filter(id=self.comment.id)
        self.admin.approve_comments(request, queryset)

        self.comment.refresh_from_db()
        self.assertEqual(self.comment.status, "approved")
        self.assertEqual(self.comment.moderated_by, self.staff_user)

    def test_reject_comments_action(self):
        request = MagicMock()
        request.user = self.staff_user

        queryset = BlogComment.objects.filter(id=self.comment.id)
        self.admin.reject_comments(request, queryset)

        self.comment.refresh_from_db()
        self.assertEqual(self.comment.status, "rejected")

    def test_mark_as_spam_action(self):
        request = MagicMock()
        request.user = self.staff_user

        queryset = BlogComment.objects.filter(id=self.comment.id)
        self.admin.mark_as_spam(request, queryset)

        self.comment.refresh_from_db()
        self.assertEqual(self.comment.status, "spam")

    def test_get_queryset_optimization(self):
        request = MagicMock()
        queryset = self.admin.get_queryset(request)

        query_str = str(queryset.query)
        self.assertIn("JOIN", query_str.upper())

        list(queryset)  # Force evaluation

    def test_has_change_permission(self):
        request = MagicMock()

        request.user = self.staff_user
        self.assertTrue(self.admin.has_change_permission(request))

        request.user = self.user
        self.assertFalse(self.admin.has_change_permission(request))

    def test_has_add_permission(self):
        request = MagicMock()

        request.user = self.superuser
        self.assertFalse(self.admin.has_add_permission(request))

    def test_has_delete_permission(self):
        request = MagicMock()

        request.user = self.superuser
        self.assertTrue(self.admin.has_delete_permission(request))

        request.user = self.staff_user
        self.assertFalse(self.admin.has_delete_permission(request))

    def test_list_filter(self):
        expected_filters = [
            "status",
            "created_at",
            "blog_category",
        ]

        for filter_field in expected_filters:
            self.assertIn(
                filter_field,
                [f if isinstance(f, str) else f[0] for f in self.admin.list_filter],
            )

    def test_search_fields(self):
        expected_search_fields = [
            "content",
            "author__username",
            "author__email",
            "author_name",
            "author_email",
            "blog_template_name",
            "ip_address",
        ]

        for field in expected_search_fields:
            self.assertIn(field, self.admin.search_fields)

    def test_readonly_fields(self):
        readonly_fields = [
            "created_at",
            "updated_at",
            "ip_address",
            "user_agent",
            "moderated_at",
            "moderated_by",
            "is_edited",
            "edited_at",
        ]

        for field in readonly_fields:
            self.assertIn(field, self.admin.readonly_fields)

    def test_fieldsets(self):
        fieldsets = dict(self.admin.fieldsets)

        self.assertIn("Blog Post", fieldsets)
        self.assertIn("Author Information", fieldsets)
        self.assertIn("Comment", fieldsets)
        self.assertIn("Moderation", fieldsets)
        self.assertIn("Metadata", fieldsets)

        moderation_classes = fieldsets["Moderation"].get("classes", ())
        self.assertIn("collapse", moderation_classes)

        metadata_classes = fieldsets["Metadata"].get("classes", ())
        self.assertIn("collapse", metadata_classes)

    def test_date_hierarchy(self):
        self.assertEqual(self.admin.date_hierarchy, "created_at")

    def test_actions(self):
        expected_actions = ["approve_comments", "reject_comments", "mark_as_spam"]

        for action in expected_actions:
            self.assertIn(action, self.admin.actions)


class AdminIntegrationTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = UserFactory.create_user()
        self.staff_user = UserFactory.create_staff_user()
        self.superuser = UserFactory.create_superuser()
        self.comment = BlogCommentFactory.create_pending_comment()

    def test_admin_changelist_view(self):
        self.client.login(username=self.superuser.username, password="testpass123")

        url = reverse("admin:blog_blogcomment_changelist")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Blog Comments")
        self.assertContains(response, "This is a test comment")

    def test_admin_change_view(self):
        self.client.login(username=self.superuser.username, password="testpass123")

        url = reverse("admin:blog_blogcomment_change", args=[self.comment.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This is a test comment")
        self.assertContains(response, "0001_test_post")

    def test_admin_actions_in_changelist(self):
        self.client.login(username=self.superuser.username, password="testpass123")

        url = reverse("admin:blog_blogcomment_changelist")
        response = self.client.get(url)

        self.assertContains(response, "Approve selected comments")
        self.assertContains(response, "Reject selected comments")
        self.assertContains(response, "Mark selected as spam")

    def test_admin_cannot_add_comment(self):
        self.client.login(username=self.superuser.username, password="testpass123")

        url = reverse("admin:blog_blogcomment_changelist")
        response = self.client.get(url)

        self.assertNotContains(response, "Add blog comment")

    def test_admin_filters_work(self):
        BlogCommentFactory.create_approved_comment(content="Approved comment")
        BlogCommentFactory.create_comment(content="Spam comment", status="spam")

        self.client.login(username=self.superuser.username, password="testpass123")

        url = reverse("admin:blog_blogcomment_changelist") + "?status__exact=pending"
        response = self.client.get(url)

        self.assertContains(response, "This is a test comment")
        self.assertNotContains(response, "Approved comment")
        self.assertNotContains(response, "Spam comment")

    def test_admin_search(self):
        BlogCommentFactory.create_comment(content="Unique search term xyz123")

        self.client.login(username=self.superuser.username, password="testpass123")

        url = reverse("admin:blog_blogcomment_changelist") + "?q=xyz123"
        response = self.client.get(url)

        self.assertContains(response, "Unique search term")
        self.assertNotContains(response, "This is a test comment")
