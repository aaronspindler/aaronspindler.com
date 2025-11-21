import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import Client, TestCase

from accounts.tests.factories import UserFactory
from blog.models import BlogComment
from blog.tests.factories import BlogCommentFactory, MockDataFactory

User = get_user_model()


class BlogViewsTest(TestCase):
    """Test blog rendering and basic view functionality."""

    def setUp(self):
        self.client = Client()
        self.setUp_users()
        self.setUp_blog_data()

    def setUp_users(self):
        """Set up common users for testing."""
        self.user = UserFactory.create_user()
        self.staff_user = UserFactory.create_staff_user()
        self.superuser = UserFactory.create_superuser()

    def setUp_blog_data(self):
        """Set up common blog data for testing."""
        self.comment_data = {
            "blog_template_name": "0001_test_post",
            "blog_category": "tech",
            "content": "This is a test comment",
            "author": self.user,
        }
        self.mock_blog_data = MockDataFactory.get_mock_blog_data()

    @patch("blog.views.get_blog_from_template_name")
    @patch("utils.models.RequestFingerprint")
    def test_render_blog_template_success(self, mock_request_fingerprint, mock_get_blog):
        """Test successful blog post rendering."""
        mock_get_blog.return_value = self.mock_blog_data
        mock_request_fingerprint.objects.filter.return_value.count.return_value = 42

        response = self.client.get("/b/tech/0001_test_post/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test content")
        self.assertIn("comments", response.context)
        self.assertIn("comment_form", response.context)
        self.assertEqual(response.context["views"], 42)

    @patch("blog.views.get_blog_from_template_name")
    def test_render_blog_template_with_category(self, mock_get_blog):
        """Test blog post rendering with category."""
        mock_get_blog.return_value = self.mock_blog_data

        response = self.client.get("/b/tech/0001_test_post/")

        self.assertEqual(response.status_code, 200)
        mock_get_blog.assert_called_with("0001_test_post", category="tech")

    @patch("blog.views.get_blog_from_template_name")
    @patch("utils.models.RequestFingerprint")
    def test_render_blog_with_comments(self, mock_request_fingerprint, mock_get_blog):
        """Test blog rendering includes approved comments."""
        mock_get_blog.return_value = {
            "entry_number": "0001",
            "template_name": "0001_test_post",
            "blog_title": "0001 test post",
            "blog_content": "<p>Test content</p>",
            "category": "tech",
            "github_link": "https://github.com/test",
        }
        mock_request_fingerprint.objects.filter.return_value.count.return_value = 0

        # Create comments with different statuses
        BlogCommentFactory.create_approved_comment(content="Approved comment")
        BlogCommentFactory.create_pending_comment(content="Pending comment")

        response = self.client.get("/b/tech/0001_test_post/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["comment_count"], 1)
        comments = response.context["comments"]
        self.assertEqual(len(comments), 1)
        self.assertEqual(comments[0].content, "Approved comment")

    @patch("blog.views.get_blog_from_template_name")
    @patch("utils.models.RequestFingerprint")
    def test_staff_sees_pending_count(self, mock_request_fingerprint, mock_get_blog):
        """Test that staff users see pending comment count."""
        mock_get_blog.return_value = {
            "entry_number": "0001",
            "template_name": "0001_test_post",
            "blog_title": "0001 test post",
            "blog_content": "<p>Test content</p>",
            "category": "tech",
            "github_link": "https://github.com/test",
        }
        mock_request_fingerprint.objects.filter.return_value.count.return_value = 0

        # Create pending comments for the specific blog post
        BlogCommentFactory.create_pending_comment(
            blog_template_name="0001_test_post",
            blog_category="tech",
            content="Pending 1",
        )
        BlogCommentFactory.create_pending_comment(
            blog_template_name="0001_test_post",
            blog_category="tech",
            content="Pending 2",
        )

        # Test as regular user - shouldn't see pending count
        response = self.client.get("/b/tech/0001_test_post/")
        self.assertNotIn("pending_comments_count", response.context)

        # Test as staff user - should see pending count
        self.client.login(username=self.staff_user.username, password="testpass123")
        response = self.client.get("/b/tech/0001_test_post/")
        self.assertEqual(response.context["pending_comments_count"], 2)


class CommentSubmissionTest(TestCase):
    """Test comment submission functionality."""

    def setUp(self):
        self.client = Client()
        self.setUp_users()
        self.setUp_blog_data()

    def setUp_users(self):
        """Set up common users for testing."""
        self.user = UserFactory.create_user()
        self.staff_user = UserFactory.create_staff_user()
        self.superuser = UserFactory.create_superuser()

    def setUp_blog_data(self):
        """Set up common blog data for testing."""
        self.comment_data = {
            "blog_template_name": "0001_test_post",
            "blog_category": "tech",
            "content": "This is a test comment",
            "author": self.user,
        }
        self.mock_blog_data = MockDataFactory.get_mock_blog_data()

    @patch("blog.views.get_blog_from_template_name")
    @patch("utils.models.RequestFingerprint")
    def test_submit_comment_authenticated(self, mock_request_fingerprint, mock_get_blog):
        """Test authenticated user submitting a comment."""
        mock_get_blog.return_value = self.mock_blog_data
        mock_request_fingerprint.objects.filter.return_value.count.return_value = 0

        self.client.login(username=self.user.username, password="testpass123")

        form_data = MockDataFactory.get_common_form_data()["comment_form"]
        form_data["content"] = "Great post!"
        response = self.client.post("/b/tech/0001_test_post/comment/", form_data)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, "/b/tech/0001_test_post/#comments")

        comment = BlogComment.objects.get(content="Great post!")
        self.assertEqual(comment.author, self.user)
        self.assertEqual(comment.blog_template_name, "0001_test_post")
        self.assertEqual(comment.blog_category, "tech")
        self.assertEqual(comment.status, "pending")

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn("submitted for review", str(messages[0]))

    @patch("blog.views.get_blog_from_template_name")
    @patch("utils.models.RequestFingerprint")
    @patch("blog.models.BlogComment.get_approved_comments")
    @patch("django.urls.reverse")
    def test_submit_comment_anonymous(self, mock_reverse, mock_get_approved, mock_request_fingerprint, mock_get_blog):
        """Test anonymous user submitting a comment."""
        mock_get_blog.return_value = self.mock_blog_data
        mock_request_fingerprint.objects.filter.return_value.count.return_value = 0
        mock_get_approved.return_value.count.return_value = 0
        mock_reverse.return_value = "/b/tech/0001_test_post/"

        form_data = MockDataFactory.get_common_form_data()["comment_form"]
        form_data.update(
            {
                "content": "Anonymous comment",
                "author_name": "John Doe",
                "author_email": "john@example.com",
            }
        )
        response = self.client.post("/b/tech/0001_test_post/comment/", form_data)

        # Debug: check what happened if not redirect
        if response.status_code != 302:
            print(f"Response status: {response.status_code}")
            if hasattr(response, "context") and response.context:
                if "comment_form" in response.context:
                    form = response.context["comment_form"]
                    print(f"Form errors: {form.errors}")  # noqa: T201
                    print(f"Form is_bound: {form.is_bound}")  # noqa: T201
                    if form.is_bound:
                        print(f"Form data: {form.data}")
                        print(f"Form cleaned_data: {getattr(form, 'cleaned_data', 'Not cleaned')}")

            # Try to create the comment manually to see if it works
            try:
                from blog.forms import CommentForm

                test_form = CommentForm(form_data, user=None)
                print(f"Manual form is_valid: {test_form.is_valid()}")
                print(f"Manual form errors: {test_form.errors}")
            except Exception as e:
                print(f"Manual form creation failed: {e}")

        self.assertEqual(response.status_code, 302)

        comment = BlogComment.objects.get(content="Anonymous comment")
        self.assertIsNone(comment.author)
        self.assertEqual(comment.author_name, "John Doe")
        self.assertEqual(comment.author_email, "john@example.com")
        self.assertEqual(comment.status, "pending")

    def test_honeypot_protection(self):
        """Test that honeypot field catches bots."""
        form_data = MockDataFactory.get_common_form_data()["comment_form"]
        form_data.update(
            {
                "content": "Spam comment",
                "website": "http://spam.com",  # Bot filled honeypot
            }
        )
        self.client.post("/b/tech/0001_test_post/comment/", form_data)

        # Should get form error, not create comment
        self.assertEqual(BlogComment.objects.filter(content="Spam comment").count(), 0)

    @patch("blog.views.get_blog_from_template_name")
    @patch("utils.models.RequestFingerprint")
    @patch("blog.models.BlogComment.get_approved_comments")
    def test_submit_invalid_comment(self, mock_get_approved, mock_request_fingerprint, mock_get_blog):
        """Test submitting invalid comment re-renders form with errors."""
        blog_data = {
            "entry_number": "0001",
            "template_name": "0001_test_post",
            "blog_title": "0001 test post",
            "blog_content": "<p>Test</p>",
            "category": "tech",
        }
        mock_get_blog.return_value = blog_data
        mock_request_fingerprint.objects.filter.return_value.count.return_value = 0
        mock_get_approved.return_value.count.return_value = 0

        form_data = MockDataFactory.get_common_form_data()["comment_form"]
        form_data.update(
            {
                "content": "",  # Empty content should cause validation error
                "author_name": "Test User",
                "author_email": "test@example.com",
            }
        )
        response = self.client.post("/b/tech/0001_test_post/comment/", form_data)

        self.assertEqual(response.status_code, 200)
        self.assertIn("comment_form", response.context)
        form = response.context["comment_form"]
        self.assertTrue(form.is_bound)
        self.assertIn("content", form.errors)


class CommentReplyTest(TestCase):
    """Test comment reply functionality."""

    def setUp(self):
        self.client = Client()
        self.setUp_users()
        self.setUp_blog_data()
        self.parent_comment = BlogCommentFactory.create_approved_comment(content="Parent comment", author=self.user)

    def setUp_users(self):
        """Set up common users for testing."""
        self.user = UserFactory.create_user()
        self.staff_user = UserFactory.create_staff_user()
        self.superuser = UserFactory.create_superuser()

    def setUp_blog_data(self):
        """Set up common blog data for testing."""
        self.comment_data = {
            "blog_template_name": "0001_test_post",
            "blog_category": "tech",
            "content": "This is a test comment",
            "author": self.user,
        }
        self.mock_blog_data = MockDataFactory.get_mock_blog_data()

    @patch("blog.views.get_blog_from_template_name")
    def test_reply_to_comment(self, mock_get_blog):
        """Test replying to a comment."""
        # Mock the blog template for the redirect target
        mock_get_blog.return_value = self.mock_blog_data

        self.client.login(username=self.user.username, password="testpass123")

        form_data = MockDataFactory.get_common_form_data()["comment_form"]
        form_data["content"] = "This is a reply"
        response = self.client.post(f"/comment/{self.parent_comment.id}/reply/", form_data)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, f"/b/tech/0001_test_post/#comment-{self.parent_comment.id}")

        reply = BlogComment.objects.get(content="This is a reply")
        self.assertEqual(reply.parent, self.parent_comment)
        self.assertEqual(reply.blog_template_name, "0001_test_post")
        self.assertEqual(reply.blog_category, "tech")

    def test_reply_to_non_approved_comment(self):
        """Test that replying to non-approved comments fails."""
        pending_comment = BlogCommentFactory.create_pending_comment(content="Pending comment")

        form_data = MockDataFactory.get_common_form_data()["comment_form"]
        form_data["content"] = "Reply attempt"
        response = self.client.post(f"/comment/{pending_comment.id}/reply/", form_data)

        self.assertEqual(response.status_code, 404)

    def test_reply_honeypot_protection(self):
        """Test honeypot protection in reply form."""
        form_data = MockDataFactory.get_common_form_data()["comment_form"]
        form_data.update(
            {
                "content": "Spam reply",
                "website": "http://spam.com",  # Bot filled honeypot
            }
        )
        response = self.client.post(f"/comment/{self.parent_comment.id}/reply/", form_data)

        messages = list(get_messages(response.wsgi_request))
        self.assertIn("Bot detection", str(messages[0]))
        self.assertEqual(BlogComment.objects.filter(content="Spam reply").count(), 0)


class CommentModerationTest(TestCase):
    """Test comment moderation functionality."""

    def setUp(self):
        self.client = Client()
        self.setUp_users()
        self.comment = BlogCommentFactory.create_pending_comment()

    def setUp_users(self):
        """Set up common users for testing."""
        self.user = UserFactory.create_user()
        self.staff_user = UserFactory.create_staff_user()
        self.superuser = UserFactory.create_superuser()

    def test_moderate_comment_approve(self):
        """Test staff approving a comment."""
        self.client.login(username=self.staff_user.username, password="testpass123")

        response = self.client.post(f"/comment/{self.comment.id}/moderate/", {"action": "approve"})

        self.assertEqual(response.status_code, 302)
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.status, "approved")
        self.assertEqual(self.comment.moderated_by, self.staff_user)

    def test_moderate_comment_reject(self):
        """Test staff rejecting a comment."""
        self.client.login(username=self.staff_user.username, password="testpass123")

        response = self.client.post(
            f"/comment/{self.comment.id}/moderate/",
            {"action": "reject", "note": "Inappropriate content"},
        )

        self.assertEqual(response.status_code, 302)
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.status, "rejected")
        self.assertEqual(self.comment.moderation_note, "Inappropriate content")

    def test_moderate_comment_spam(self):
        """Test marking comment as spam."""
        self.client.login(username=self.staff_user.username, password="testpass123")

        response = self.client.post(f"/comment/{self.comment.id}/moderate/", {"action": "spam"})

        self.assertEqual(response.status_code, 302)
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.status, "spam")

    def test_moderate_comment_non_staff(self):
        """Test that non-staff cannot moderate comments."""
        self.client.login(username=self.user.username, password="testpass123")

        response = self.client.post(f"/comment/{self.comment.id}/moderate/", {"action": "approve"})

        self.assertEqual(response.status_code, 403)
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.status, "pending")

    def test_moderate_ajax_request(self):
        """Test AJAX moderation returns JSON response."""
        self.client.login(username=self.staff_user.username, password="testpass123")

        response = self.client.post(
            f"/comment/{self.comment.id}/moderate/",
            {"action": "approve"},
            headers={"x-requested-with": "XMLHttpRequest"},
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["new_status"], "approved")


class CommentVotingTest(TestCase):
    """Test comment voting functionality."""

    def setUp(self):
        self.client = Client()
        self.setUp_users()
        self.comment = BlogCommentFactory.create_approved_comment()

    def setUp_users(self):
        """Set up common users for testing."""
        self.user = UserFactory.create_user()
        self.staff_user = UserFactory.create_staff_user()
        self.superuser = UserFactory.create_superuser()

    def test_vote_comment_authenticated(self):
        """Test authenticated user voting on a comment."""
        self.client.login(username=self.user.username, password="testpass123")

        response = self.client.post(f"/comment/{self.comment.id}/vote/", {"vote_type": "upvote"})

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["action"], "added")
        self.assertEqual(data["upvotes"], 1)
        self.assertEqual(data["score"], 1)
        self.assertEqual(data["user_vote"], "upvote")

    def test_vote_toggle(self):
        """Test toggling vote (clicking same vote type removes it)."""
        self.client.login(username=self.user.username, password="testpass123")

        # Add upvote
        self.client.post(f"/comment/{self.comment.id}/vote/", {"vote_type": "upvote"})

        # Toggle off
        response = self.client.post(f"/comment/{self.comment.id}/vote/", {"vote_type": "upvote"})

        data = json.loads(response.content)
        self.assertEqual(data["action"], "removed")
        self.assertEqual(data["upvotes"], 0)
        self.assertIsNone(data["user_vote"])

    def test_vote_change(self):
        """Test changing vote from upvote to downvote."""
        self.client.login(username=self.user.username, password="testpass123")

        # Add upvote
        self.client.post(f"/comment/{self.comment.id}/vote/", {"vote_type": "upvote"})

        # Change to downvote
        response = self.client.post(f"/comment/{self.comment.id}/vote/", {"vote_type": "downvote"})

        data = json.loads(response.content)
        self.assertEqual(data["action"], "changed")
        self.assertEqual(data["upvotes"], 0)
        self.assertEqual(data["downvotes"], 1)
        self.assertEqual(data["score"], -1)
        self.assertEqual(data["user_vote"], "downvote")

    def test_vote_unauthenticated(self):
        """Test that unauthenticated users cannot vote."""
        response = self.client.post(f"/comment/{self.comment.id}/vote/", {"vote_type": "upvote"})

        self.assertEqual(response.status_code, 401)
        data = json.loads(response.content)
        self.assertEqual(data["error"], "Authentication required")

    def test_vote_non_approved_comment(self):
        """Test voting on non-approved comments fails."""
        pending_comment = BlogCommentFactory.create_pending_comment()

        self.client.login(username=self.user.username, password="testpass123")

        response = self.client.post(f"/comment/{pending_comment.id}/vote/", {"vote_type": "upvote"})

        self.assertEqual(response.status_code, 404)

    def test_invalid_vote_type(self):
        """Test invalid vote type returns error."""
        self.client.login(username=self.user.username, password="testpass123")

        response = self.client.post(f"/comment/{self.comment.id}/vote/", {"vote_type": "invalid"})

        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertEqual(data["error"], "Invalid vote type")


class CommentDeletionTest(TestCase):
    """Test comment deletion functionality."""

    def setUp(self):
        self.client = Client()
        self.setUp_users()
        self.author = UserFactory.create_user(username="author")
        self.other_user = UserFactory.create_user(username="other")
        self.comment = BlogCommentFactory.create_approved_comment(author=self.author)

    def setUp_users(self):
        """Set up common users for testing."""
        self.user = UserFactory.create_user()
        self.staff_user = UserFactory.create_staff_user()
        self.superuser = UserFactory.create_superuser()

    def test_author_can_delete_own_comment(self):
        """Test that comment authors can delete their own comments."""
        self.client.login(username=self.author.username, password="testpass123")

        response = self.client.get(f"/comment/{self.comment.id}/delete/")

        self.assertEqual(response.status_code, 302)
        self.assertFalse(BlogComment.objects.filter(id=self.comment.id).exists())

    def test_staff_can_delete_any_comment(self):
        """Test that staff can delete any comment."""
        self.client.login(username=self.staff_user.username, password="testpass123")

        response = self.client.get(f"/comment/{self.comment.id}/delete/")

        self.assertEqual(response.status_code, 302)
        self.assertFalse(BlogComment.objects.filter(id=self.comment.id).exists())

    def test_other_user_cannot_delete_comment(self):
        """Test that other users cannot delete comments."""
        self.client.login(username=self.other_user.username, password="testpass123")

        response = self.client.get(f"/comment/{self.comment.id}/delete/")

        self.assertEqual(response.status_code, 302)
        self.assertTrue(BlogComment.objects.filter(id=self.comment.id).exists())
        messages = list(get_messages(response.wsgi_request))
        self.assertIn("permission", str(messages[0]))

    def test_deleting_parent_deletes_replies(self):
        """Test that deleting parent comment cascades to replies."""
        reply = BlogCommentFactory.create_approved_comment(content="Reply", parent=self.comment)

        self.client.login(username=self.staff_user.username, password="testpass123")
        self.client.get(f"/comment/{self.comment.id}/delete/")

        self.assertFalse(BlogComment.objects.filter(id=self.comment.id).exists())
        self.assertFalse(BlogComment.objects.filter(id=reply.id).exists())


class KnowledgeGraphAPITest(TestCase):
    """Test knowledge graph API endpoints."""

    def setUp(self):
        self.client = Client()

    @patch("blog.views.build_knowledge_graph")
    def test_knowledge_graph_api_get(self, mock_build_graph):
        """Test GET request to knowledge graph API."""
        mock_build_graph.return_value = {
            "nodes": [{"id": "test", "label": "Test"}],
            "edges": [],
            "metrics": {"total_posts": 1},
        }

        response = self.client.get("/api/knowledge-graph/")

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["metadata"]["nodes_count"], 1)
        mock_build_graph.assert_called_with(False)

    @patch("blog.views.build_knowledge_graph")
    def test_knowledge_graph_api_refresh(self, mock_build_graph):
        """Test forcing refresh of knowledge graph."""
        mock_build_graph.return_value = {"nodes": [], "edges": [], "metrics": {}}

        response = self.client.get("/api/knowledge-graph/?refresh=true")

        self.assertEqual(response.status_code, 200)
        mock_build_graph.assert_called_with(True)

    @patch("blog.views.get_post_graph")
    def test_knowledge_graph_post_specific(self, mock_get_post):
        """Test getting graph for specific post."""
        mock_get_post.return_value = {
            "nodes": [{"id": "post1"}],
            "edges": [],
            "metrics": {},
        }

        response = self.client.get("/api/knowledge-graph/?post=0001_test_post&depth=2")

        self.assertEqual(response.status_code, 200)
        mock_get_post.assert_called_with("0001_test_post", 2)

    @patch("blog.views.build_knowledge_graph")
    def test_knowledge_graph_api_post_request(self, mock_build_graph):
        """Test POST request to knowledge graph API."""
        mock_build_graph.return_value = {"nodes": [], "edges": [], "metrics": {}}

        response = self.client.post(
            "/api/knowledge-graph/",
            json.dumps({"operation": "refresh"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        mock_build_graph.assert_called_with(force_refresh=True)

    @patch("blog.views.build_knowledge_graph")
    def test_knowledge_graph_api_error_handling(self, mock_build_graph):
        """Test error handling in knowledge graph API."""
        mock_build_graph.side_effect = Exception("Test error")

        response = self.client.get("/api/knowledge-graph/")

        self.assertEqual(response.status_code, 500)
        data = json.loads(response.content)
        self.assertEqual(data["status"], "error")
        # After security fix, error messages are generic
        self.assertEqual(data["error"], "An error occurred while processing your request")
