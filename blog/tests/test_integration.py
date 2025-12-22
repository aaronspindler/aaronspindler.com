import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase, TransactionTestCase

from accounts.tests.factories import UserFactory
from blog.models import BlogComment, CommentVote
from blog.tests.factories import BlogCommentFactory, MockDataFactory

User = get_user_model()


class BlogIntegrationTest(TransactionTestCase):
    def setUp(self):
        self.client = Client()
        self.setUp_users()
        self.setUp_blog_data()
        cache.clear()

    def setUp_users(self):
        self.user = UserFactory.create_user()
        self.staff_user = UserFactory.create_staff_user()
        self.superuser = UserFactory.create_superuser()

    def setUp_blog_data(self):
        self.comment_data = {
            "blog_template_name": "0001_test_post",
            "blog_category": "tech",
            "content": "This is a test comment",
            "author": self.user,
        }
        self.mock_blog_data = MockDataFactory.get_mock_blog_data()

    @patch("blog.views.get_blog_from_template_name")
    @patch("utils.models.TrackedRequest")
    def test_complete_comment_workflow(self, mock_request_fingerprint, mock_get_blog):
        mock_get_blog.return_value = self.mock_blog_data
        mock_request_fingerprint.objects.filter.return_value.count.return_value = 0

        self.client.login(username=self.user.username, password="testpass123")
        form_data = MockDataFactory.get_common_form_data()["comment_form"]
        response = self.client.post("/b/tech/0001_test_post/comment/", form_data)
        self.assertEqual(response.status_code, 302)

        comment = BlogComment.objects.get(content="This is a test comment")
        self.assertEqual(comment.status, "pending")
        comment_id = comment.id

        self.client.login(username=self.staff_user.username, password="testpass123")
        response = self.client.post(f"/comment/{comment_id}/moderate/", {"action": "approve"})
        self.assertEqual(response.status_code, 302)

        comment.refresh_from_db()
        self.assertEqual(comment.status, "approved")

        other_user = UserFactory.create_user(username="other")
        self.client.login(username=other_user.username, password="testpass123")
        response = self.client.post(f"/comment/{comment_id}/vote/", {"vote_type": "upvote"})

        data = json.loads(response.content)
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["upvotes"], 1)

        self.client.login(username=self.user.username, password="testpass123")
        reply_data = MockDataFactory.get_common_form_data()["comment_form"]
        reply_data["content"] = "This is a reply"
        response = self.client.post(f"/comment/{comment_id}/reply/", reply_data)
        self.assertEqual(response.status_code, 302)

        reply = BlogComment.objects.get(content="This is a reply")
        self.assertEqual(reply.parent_id, comment_id)

    @patch("blog.views.get_blog_from_template_name")
    @patch("utils.models.TrackedRequest")
    def test_nested_comment_thread(self, mock_request_fingerprint, mock_get_blog):
        mock_get_blog.return_value = {
            "entry_number": "0001",
            "template_name": "0001_test_post",
            "blog_title": "0001 test post",
            "blog_content": "<p>Test content</p>",
            "category": "tech",
        }
        mock_request_fingerprint.objects.filter.return_value.count.return_value = 0

        parent = BlogCommentFactory.create_approved_comment(content="Parent comment", author=self.user)

        child1 = BlogCommentFactory.create_approved_comment(content="Child 1", author=self.user, parent=parent)

        child2 = BlogCommentFactory.create_approved_comment(content="Child 2", author=self.staff_user, parent=parent)

        BlogCommentFactory.create_approved_comment(content="Grandchild", author=self.user, parent=child1)

        response = self.client.get("/b/tech/0001_test_post/")
        self.assertEqual(response.status_code, 200)

        comments = response.context["comments"]
        self.assertEqual(len(comments), 1)  # Only top-level
        self.assertEqual(comments[0].id, parent.id)

        replies = parent.get_replies()
        self.assertEqual(replies.count(), 2)
        self.assertIn(child1, replies)
        self.assertIn(child2, replies)

    def test_concurrent_voting(self):
        comment = BlogCommentFactory.create_approved_comment()

        users = []
        for i in range(5):
            user = UserFactory.create_user(username=f"user{i}")
            users.append(user)

        for user in users:
            self.client.login(username=user.username, password="testpass123")
            response = self.client.post(f"/comment/{comment.id}/vote/", {"vote_type": "upvote"})
            self.assertEqual(response.status_code, 200)

        comment.refresh_from_db()
        self.assertEqual(comment.upvotes, 5)
        self.assertEqual(comment.score, 5)

    def test_spam_detection_workflow(self):
        spam_content = "Buy cheap viagra at http://spam1.com http://spam2.com http://spam3.com http://spam4.com"

        form_data = MockDataFactory.get_common_form_data()["comment_form"]
        form_data.update({"content": spam_content, "author_name": "Spammer"})
        self.client.post("/b/tech/test_post/comment/", form_data)

        comments = BlogComment.objects.filter(content=spam_content)
        self.assertEqual(comments.count(), 0)

    def test_moderation_queue_workflow(self):
        for i in range(5):
            BlogCommentFactory.create_pending_comment(content=f"Comment {i}")

        self.client.login(username=self.staff_user.username, password="testpass123")

        pending_count = BlogComment.get_pending_count()
        self.assertEqual(pending_count, 5)

        comments = BlogComment.objects.filter(status="pending")
        for i, comment in enumerate(comments):
            if i % 2 == 0:
                comment.approve(user=self.staff_user)
            else:
                comment.reject(user=self.staff_user)

        approved = BlogComment.objects.filter(status="approved").count()
        rejected = BlogComment.objects.filter(status="rejected").count()
        self.assertEqual(approved, 3)
        self.assertEqual(rejected, 2)

    @patch("blog.views.get_blog_from_template_name")
    @patch("utils.models.TrackedRequest")
    def test_comment_deletion_cascade(self, mock_request_fingerprint, mock_get_blog):
        mock_get_blog.return_value = {
            "entry_number": "0001",
            "template_name": "0001_test_post",
            "blog_title": "0001 test post",
            "blog_content": "<p>Test</p>",
            "category": "tech",
        }
        mock_request_fingerprint.objects.filter.return_value.count.return_value = 0

        parent = BlogCommentFactory.create_approved_comment(content="Parent", author=self.user)

        child = BlogCommentFactory.create_approved_comment(content="Child", parent=parent)

        BlogCommentFactory.create_comment_vote(comment=parent, user=self.staff_user, vote_type="upvote")

        self.client.login(username=self.user.username, password="testpass123")
        self.client.get(f"/comment/{parent.id}/delete/")

        self.assertFalse(BlogComment.objects.filter(id=parent.id).exists())
        self.assertFalse(BlogComment.objects.filter(id=child.id).exists())
        self.assertFalse(CommentVote.objects.filter(comment=parent).exists())


class KnowledgeGraphIntegrationTest(TestCase):
    def setUp(self):
        cache.clear()

    @patch("blog.knowledge_graph.get_all_blog_posts")
    @patch("blog.knowledge_graph.LinkParser.parse_blog_post")
    def test_full_graph_generation(self, mock_parse, mock_get_posts):
        mock_get_posts.return_value = [
            {
                "template_name": "post1",
                "category": "tech",
                "full_path": "/path/post1.html",
            },
            {
                "template_name": "post2",
                "category": "tech",
                "full_path": "/path/post2.html",
            },
            {
                "template_name": "post3",
                "category": "personal",
                "full_path": "/path/post3.html",
            },
        ]

        mock_parse.side_effect = [
            {
                "source_post": "post1",
                "internal_links": [
                    {
                        "target": "post2",
                        "text": "Link to post2",
                        "context": "Context",
                        "href": "/b/post2/",
                    }
                ],
                "external_links": [
                    {
                        "url": "https://example.com",
                        "text": "Example",
                        "context": "Context",
                        "domain": "example.com",
                    }
                ],
            },
            {
                "source_post": "post2",
                "internal_links": [
                    {
                        "target": "post3",
                        "text": "Link to post3",
                        "context": "Context",
                        "href": "/b/post3/",
                    }
                ],
                "external_links": [],
            },
            {"source_post": "post3", "internal_links": [], "external_links": []},
        ]

        from blog.knowledge_graph import build_knowledge_graph

        graph = build_knowledge_graph(force_refresh=True)

        self.assertIn("nodes", graph)
        self.assertIn("edges", graph)
        self.assertIn("metrics", graph)

        metrics = graph["metrics"]
        self.assertEqual(metrics["total_posts"], 3)
        self.assertEqual(metrics["total_internal_links"], 2)

    @patch("blog.views.build_knowledge_graph")
    def test_knowledge_graph_api_caching(self, mock_build):
        mock_build.return_value = {
            "nodes": [{"id": "test"}],
            "edges": [],
            "metrics": {},
        }

        client = Client()

        response = client.get("/api/knowledge-graph/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_build.call_count, 1)

        response = client.get("/api/knowledge-graph/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_build.call_count, 2)  # Called again but might use cache internally

        response = client.get("/api/knowledge-graph/?refresh=true")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(mock_build.called)


class PerformanceTest(TestCase):
    def test_comment_query_optimization(self):
        user = UserFactory.create_user()

        for i in range(10):
            comment = BlogCommentFactory.create_approved_comment(
                content=f"Comment {i}", author=user if i % 2 == 0 else None
            )

            for j in range(3):
                BlogCommentFactory.create_approved_comment(content=f"Reply {i}-{j}", parent=comment)

        with self.assertNumQueries(1):  # Optimized to use select_related
            comments = BlogComment.get_approved_comments("test_post")
            list(comments)
            for comment in comments:
                list(comment.get_replies())

    def test_knowledge_graph_cache_performance(self):
        from blog.knowledge_graph import LinkParser

        parser = LinkParser()

        with patch.object(parser, "_get_template_content") as mock_content:
            mock_content.return_value = '<p><a href="/b/test/">Link</a></p>'

            # First parse
            result1 = parser.parse_blog_post("test_post")
            self.assertEqual(mock_content.call_count, 1)

            # Second parse should use cache
            result2 = parser.parse_blog_post("test_post")
            self.assertLessEqual(mock_content.call_count, 2)

            self.assertEqual(result1, result2)
