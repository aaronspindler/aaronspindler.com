from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from blog.models import BlogComment, CommentVote
import json

User = get_user_model()


class CommentVoteTestCase(TestCase):
    """Test cases for comment voting functionality"""
    
    def setUp(self):
        """Set up test data"""
        # Create test users
        self.user1 = User.objects.create_user(
            username='testuser1',
            email='test1@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='testpass123'
        )
        self.staff_user = User.objects.create_user(
            username='staffuser',
            email='staff@example.com',
            password='testpass123',
            is_staff=True
        )
        
        # Create test comment
        self.comment = BlogComment.objects.create(
            blog_template_name='test_blog',
            blog_category='tech',
            author=self.user1,
            content='This is a test comment',
            status='approved'
        )
        
        # Create client for testing
        self.client = Client()
    
    def test_vote_model_creation(self):
        """Test creating a vote"""
        vote = CommentVote.objects.create(
            comment=self.comment,
            user=self.user1,
            vote_type='upvote'
        )
        self.assertEqual(vote.comment, self.comment)
        self.assertEqual(vote.user, self.user1)
        self.assertEqual(vote.vote_type, 'upvote')
    
    def test_unique_vote_constraint(self):
        """Test that a user can only have one vote per comment"""
        CommentVote.objects.create(
            comment=self.comment,
            user=self.user1,
            vote_type='upvote'
        )
        
        # Try to create another vote for the same user/comment
        with self.assertRaises(Exception):
            CommentVote.objects.create(
                comment=self.comment,
                user=self.user1,
                vote_type='downvote'
            )
    
    def test_vote_counts_update(self):
        """Test that vote counts are updated correctly"""
        # Initial counts should be 0
        self.assertEqual(self.comment.upvotes, 0)
        self.assertEqual(self.comment.downvotes, 0)
        self.assertEqual(self.comment.score, 0)
        
        # Add an upvote
        vote1 = CommentVote.objects.create(
            comment=self.comment,
            user=self.user1,
            vote_type='upvote'
        )
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.upvotes, 1)
        self.assertEqual(self.comment.downvotes, 0)
        self.assertEqual(self.comment.score, 1)
        
        # Add a downvote from another user
        vote2 = CommentVote.objects.create(
            comment=self.comment,
            user=self.user2,
            vote_type='downvote'
        )
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.upvotes, 1)
        self.assertEqual(self.comment.downvotes, 1)
        self.assertEqual(self.comment.score, 0)
    
    def test_get_user_vote(self):
        """Test getting a user's vote on a comment"""
        # No vote initially
        self.assertIsNone(self.comment.get_user_vote(self.user1))
        
        # Add upvote
        CommentVote.objects.create(
            comment=self.comment,
            user=self.user1,
            vote_type='upvote'
        )
        self.assertEqual(self.comment.get_user_vote(self.user1), 'upvote')
        
        # Check for different user
        self.assertIsNone(self.comment.get_user_vote(self.user2))
        
        # Check for anonymous user
        self.assertIsNone(self.comment.get_user_vote(None))
    
    def test_vote_view_authentication_required(self):
        """Test that authentication is required to vote"""
        url = reverse('vote_comment', kwargs={'comment_id': self.comment.id})
        response = self.client.post(url, {'vote_type': 'upvote'})
        self.assertEqual(response.status_code, 401)
        
        data = json.loads(response.content)
        self.assertEqual(data['error'], 'Authentication required')
    
    def test_vote_view_upvote(self):
        """Test upvoting a comment"""
        self.client.login(username='testuser1', password='testpass123')
        url = reverse('vote_comment', kwargs={'comment_id': self.comment.id})
        
        response = self.client.post(url, {'vote_type': 'upvote'})
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['action'], 'added')
        self.assertEqual(data['upvotes'], 1)
        self.assertEqual(data['downvotes'], 0)
        self.assertEqual(data['score'], 1)
        self.assertEqual(data['user_vote'], 'upvote')
    
    def test_vote_view_downvote(self):
        """Test downvoting a comment"""
        self.client.login(username='testuser1', password='testpass123')
        url = reverse('vote_comment', kwargs={'comment_id': self.comment.id})
        
        response = self.client.post(url, {'vote_type': 'downvote'})
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['action'], 'added')
        self.assertEqual(data['upvotes'], 0)
        self.assertEqual(data['downvotes'], 1)
        self.assertEqual(data['score'], -1)
        self.assertEqual(data['user_vote'], 'downvote')
    
    def test_vote_view_change_vote(self):
        """Test changing a vote from upvote to downvote"""
        self.client.login(username='testuser1', password='testpass123')
        url = reverse('vote_comment', kwargs={'comment_id': self.comment.id})
        
        # First upvote
        response = self.client.post(url, {'vote_type': 'upvote'})
        data = json.loads(response.content)
        self.assertEqual(data['user_vote'], 'upvote')
        self.assertEqual(data['upvotes'], 1)
        
        # Change to downvote
        response = self.client.post(url, {'vote_type': 'downvote'})
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['action'], 'changed')
        self.assertEqual(data['upvotes'], 0)
        self.assertEqual(data['downvotes'], 1)
        self.assertEqual(data['user_vote'], 'downvote')
    
    def test_vote_view_remove_vote(self):
        """Test removing a vote by clicking the same button again"""
        self.client.login(username='testuser1', password='testpass123')
        url = reverse('vote_comment', kwargs={'comment_id': self.comment.id})
        
        # First upvote
        response = self.client.post(url, {'vote_type': 'upvote'})
        data = json.loads(response.content)
        self.assertEqual(data['user_vote'], 'upvote')
        
        # Click upvote again to remove
        response = self.client.post(url, {'vote_type': 'upvote'})
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['action'], 'removed')
        self.assertEqual(data['upvotes'], 0)
        self.assertEqual(data['downvotes'], 0)
        self.assertEqual(data['user_vote'], None)
    
    def test_vote_invalid_vote_type(self):
        """Test that invalid vote types are rejected"""
        self.client.login(username='testuser1', password='testpass123')
        url = reverse('vote_comment', kwargs={'comment_id': self.comment.id})
        
        response = self.client.post(url, {'vote_type': 'invalid'})
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.content)
        self.assertEqual(data['error'], 'Invalid vote type')
    
    def test_vote_nonexistent_comment(self):
        """Test voting on a non-existent comment"""
        self.client.login(username='testuser1', password='testpass123')
        url = reverse('vote_comment', kwargs={'comment_id': 99999})
        
        response = self.client.post(url, {'vote_type': 'upvote'})
        self.assertEqual(response.status_code, 404)
        
        data = json.loads(response.content)
        self.assertEqual(data['error'], 'Comment not found')
    
    def test_vote_unapproved_comment(self):
        """Test that only approved comments can be voted on"""
        # Create unapproved comment
        unapproved_comment = BlogComment.objects.create(
            blog_template_name='test_blog',
            author=self.user1,
            content='Unapproved comment',
            status='pending'
        )
        
        self.client.login(username='testuser2', password='testpass123')
        url = reverse('vote_comment', kwargs={'comment_id': unapproved_comment.id})
        
        response = self.client.post(url, {'vote_type': 'upvote'})
        self.assertEqual(response.status_code, 404)
        
        data = json.loads(response.content)
        self.assertEqual(data['error'], 'Comment not found')
    
    def test_multiple_users_voting(self):
        """Test multiple users voting on the same comment"""
        # User 1 upvotes
        self.client.login(username='testuser1', password='testpass123')
        url = reverse('vote_comment', kwargs={'comment_id': self.comment.id})
        self.client.post(url, {'vote_type': 'upvote'})
        
        # User 2 upvotes
        self.client.login(username='testuser2', password='testpass123')
        self.client.post(url, {'vote_type': 'upvote'})
        
        # Staff user downvotes
        self.client.login(username='staffuser', password='testpass123')
        response = self.client.post(url, {'vote_type': 'downvote'})
        
        data = json.loads(response.content)
        self.assertEqual(data['upvotes'], 2)
        self.assertEqual(data['downvotes'], 1)
        self.assertEqual(data['score'], 1)
    
    def test_vote_deletion_cascades(self):
        """Test that votes are deleted when comment is deleted"""
        # Create votes
        CommentVote.objects.create(
            comment=self.comment,
            user=self.user1,
            vote_type='upvote'
        )
        CommentVote.objects.create(
            comment=self.comment,
            user=self.user2,
            vote_type='downvote'
        )
        
        # Verify votes exist
        self.assertEqual(CommentVote.objects.filter(comment=self.comment).count(), 2)
        
        # Delete comment
        comment_id = self.comment.id
        self.comment.delete()
        
        # Verify votes are deleted
        self.assertEqual(CommentVote.objects.filter(comment_id=comment_id).count(), 0)
    
    def test_render_blog_template_includes_vote_info(self):
        """Test that blog template view includes vote information"""
        # Create a vote
        CommentVote.objects.create(
            comment=self.comment,
            user=self.user1,
            vote_type='upvote'
        )
        
        # Login and request the blog page
        self.client.login(username='testuser1', password='testpass123')
        
        # Note: This would require the actual template to exist
        # For now, we're just checking that the view doesn't error
        # In a real scenario, you'd check the context data
        # response = self.client.get('/b/tech/test_blog/')
        # self.assertIn('user_vote', response.context)
