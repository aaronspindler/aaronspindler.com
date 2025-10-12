from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from blog.models import BlogComment, CommentVote
from tests.factories import BlogCommentFactory, TestDataMixin

User = get_user_model()


class BlogCommentModelTest(TestCase, TestDataMixin):
    """Test BlogComment model functionality including moderation and threading."""

    def setUp(self):
        self.setUp_users()
        self.setUp_blog_data()

    def test_comment_creation_with_user(self):
        """Test creating a comment with an authenticated user."""
        comment = BlogCommentFactory.create_comment(**self.comment_data)
        
        self.assertEqual(comment.blog_template_name, '0001_test_post')
        self.assertEqual(comment.blog_category, 'tech')
        self.assertEqual(comment.content, 'This is a test comment')
        self.assertEqual(comment.author, self.user)
        self.assertEqual(comment.status, 'pending')
        self.assertEqual(str(comment), f'Comment by {self.user.username} on tech/0001_test_post')

    def test_comment_creation_anonymous(self):
        """Test creating a comment as an anonymous user."""
        comment = BlogCommentFactory.create_anonymous_comment(
            content='Anonymous comment'
        )
        
        self.assertIsNone(comment.author)
        self.assertEqual(comment.author_name, 'John Doe')
        self.assertEqual(comment.author_email, 'john@example.com')
        self.assertEqual(comment.get_author_display(), 'John Doe')

    def test_comment_moderation_approve(self):
        """Test approving a comment."""
        comment = BlogComment.objects.create(**self.comment_data)
        self.assertEqual(comment.status, 'pending')
        
        comment.approve(user=self.staff_user)
        comment.refresh_from_db()
        
        self.assertEqual(comment.status, 'approved')
        self.assertIsNotNone(comment.moderated_at)
        self.assertEqual(comment.moderated_by, self.staff_user)

    def test_comment_moderation_reject(self):
        """Test rejecting a comment with a note."""
        comment = BlogComment.objects.create(**self.comment_data)
        
        comment.reject(user=self.staff_user, note='Contains inappropriate content')
        comment.refresh_from_db()
        
        self.assertEqual(comment.status, 'rejected')
        self.assertIsNotNone(comment.moderated_at)
        self.assertEqual(comment.moderated_by, self.staff_user)
        self.assertEqual(comment.moderation_note, 'Contains inappropriate content')

    def test_comment_mark_as_spam(self):
        """Test marking a comment as spam."""
        comment = BlogComment.objects.create(**self.comment_data)
        
        comment.mark_as_spam(user=self.staff_user)
        comment.refresh_from_db()
        
        self.assertEqual(comment.status, 'spam')
        self.assertIsNotNone(comment.moderated_at)
        self.assertEqual(comment.moderated_by, self.staff_user)

    def test_threaded_comments(self):
        """Test nested comment functionality."""
        parent = BlogComment.objects.create(**self.comment_data, status='approved')
        
        child1 = BlogComment.objects.create(
            blog_template_name='0001_test_post',
            blog_category='tech',
            content='First reply',
            author=self.user,
            parent=parent,
            status='approved'
        )
        
        child2 = BlogComment.objects.create(
            blog_template_name='0001_test_post',
            blog_category='tech',
            content='Second reply',
            author_name='Anonymous',
            parent=parent,
            status='approved'
        )
        
        # Test parent-child relationship
        replies = parent.get_replies()
        self.assertEqual(replies.count(), 2)
        self.assertIn(child1, replies)
        self.assertIn(child2, replies)
        
        # Test depth calculation
        self.assertEqual(parent.get_depth(), 0)
        self.assertEqual(child1.get_depth(), 1)
        
        # Test nested reply
        grandchild = BlogComment.objects.create(
            blog_template_name='0001_test_post',
            blog_category='tech',
            content='Nested reply',
            author=self.user,
            parent=child1,
            status='approved'
        )
        self.assertEqual(grandchild.get_depth(), 2)

    def test_comment_url_generation(self):
        """Test blog URL generation for comments."""
        comment_with_category = BlogComment.objects.create(
            blog_template_name='0001_test_post',
            blog_category='tech',
            content='Test comment'
        )
        self.assertEqual(comment_with_category.get_blog_url(), '/b/tech/0001_test_post/')

    def test_get_approved_comments(self):
        """Test retrieving approved comments for a blog post."""
        # Create mixed status comments
        approved1 = BlogComment.objects.create(**self.comment_data, status='approved')
        BlogComment.objects.create(**self.comment_data, status='pending')
        approved2 = BlogComment.objects.create(**self.comment_data, status='approved')
        BlogComment.objects.create(**self.comment_data, status='spam')
        
        # Get approved comments
        approved_comments = BlogComment.get_approved_comments('0001_test_post', 'tech')
        
        self.assertEqual(approved_comments.count(), 2)
        self.assertIn(approved1, approved_comments)
        self.assertIn(approved2, approved_comments)

    def test_pending_count(self):
        """Test getting count of pending comments."""
        BlogComment.objects.create(**self.comment_data, status='pending')
        BlogComment.objects.create(**self.comment_data, status='pending')
        BlogComment.objects.create(**self.comment_data, status='approved')
        
        self.assertEqual(BlogComment.get_pending_count(), 2)

    def test_content_length_validation(self):
        """Test that content length is validated."""
        comment = BlogComment(
            blog_template_name='0001_test_post',
            content='x' * 2001  # Over 2000 character limit
        )
        
        with self.assertRaises(ValidationError):
            comment.full_clean()


class CommentVoteModelTest(TestCase):
    """Test CommentVote model and voting functionality."""

    def setUp(self):
        self.user1 = User.objects.create_user('user1', 'user1@test.com', 'pass')
        self.user2 = User.objects.create_user('user2', 'user2@test.com', 'pass')
        self.comment = BlogComment.objects.create(
            blog_template_name='0001_test_post',
            content='Test comment',
            author=self.user1,
            status='approved'
        )

    def test_vote_creation(self):
        """Test creating a vote."""
        vote = CommentVote.objects.create(
            comment=self.comment,
            user=self.user2,
            vote_type='upvote'
        )
        
        self.assertEqual(vote.comment, self.comment)
        self.assertEqual(vote.user, self.user2)
        self.assertEqual(vote.vote_type, 'upvote')

    def test_vote_uniqueness(self):
        """Test that a user can only vote once per comment."""
        CommentVote.objects.create(
            comment=self.comment,
            user=self.user1,
            vote_type='upvote'
        )
        
        # Try to create another vote from same user
        with self.assertRaises(Exception):
            CommentVote.objects.create(
                comment=self.comment,
                user=self.user1,
                vote_type='downvote'
            )

    def test_vote_count_updates(self):
        """Test that vote counts are updated correctly."""
        # Initial state
        self.assertEqual(self.comment.upvotes, 0)
        self.assertEqual(self.comment.downvotes, 0)
        self.assertEqual(self.comment.score, 0)
        
        # Add upvote
        vote1 = CommentVote.objects.create(
            comment=self.comment,
            user=self.user1,
            vote_type='upvote'
        )
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.upvotes, 1)
        self.assertEqual(self.comment.downvotes, 0)
        self.assertEqual(self.comment.score, 1)
        
        # Add downvote
        vote2 = CommentVote.objects.create(
            comment=self.comment,
            user=self.user2,
            vote_type='downvote'
        )
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.upvotes, 1)
        self.assertEqual(self.comment.downvotes, 1)
        self.assertEqual(self.comment.score, 0)
        
        # Change vote
        vote1.vote_type = 'downvote'
        vote1.save()
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.upvotes, 0)
        self.assertEqual(self.comment.downvotes, 2)
        self.assertEqual(self.comment.score, -2)
        
        # Delete vote
        vote2.delete()
        self.comment.update_vote_counts()
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.upvotes, 0)
        self.assertEqual(self.comment.downvotes, 1)
        self.assertEqual(self.comment.score, -1)

    def test_get_user_vote(self):
        """Test checking a user's vote on a comment."""
        # No vote yet
        self.assertIsNone(self.comment.get_user_vote(self.user1))
        
        # Add upvote
        CommentVote.objects.create(
            comment=self.comment,
            user=self.user1,
            vote_type='upvote'
        )
        self.assertEqual(self.comment.get_user_vote(self.user1), 'upvote')
        
        # Check non-authenticated user
        self.assertIsNone(self.comment.get_user_vote(None))

    def test_vote_with_ip_address(self):
        """Test storing IP address with vote."""
        vote = CommentVote.objects.create(
            comment=self.comment,
            user=self.user1,
            vote_type='upvote',
            ip_address='192.168.1.1'
        )
        
        self.assertEqual(vote.ip_address, '192.168.1.1')
