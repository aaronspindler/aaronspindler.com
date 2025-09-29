from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MaxLengthValidator
from django.db.models import Sum
from django.core.files.base import ContentFile


class BlogComment(models.Model):
    """Model for blog comments with moderation support and threaded discussions."""
    
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('spam', 'Spam'),
    ]
    
    blog_template_name = models.CharField(
        max_length=255,
        help_text="Template name of the blog post (e.g., '0001_what_even_is_this')"
    )
    blog_category = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Category of the blog post (e.g., 'tech', 'personal')"
    )
    
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='blog_comments',
        help_text="Registered user who made the comment"
    )
    
    author_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Name for anonymous commenters"
    )
    author_email = models.EmailField(
        blank=True,
        help_text="Email for anonymous commenters (not displayed publicly)"
    )
    
    content = models.TextField(
        validators=[MaxLengthValidator(2000)],
        help_text="Comment content (max 2000 characters)"
    )
    
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies'
    )
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Moderation status of the comment"
    )
    moderated_at = models.DateTimeField(null=True, blank=True)
    moderated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='moderated_comments'
    )
    moderation_note = models.TextField(
        blank=True,
        help_text="Internal note about moderation decision"
    )
    
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of commenter for spam detection"
    )
    user_agent = models.TextField(
        blank=True,
        help_text="Browser user agent for spam detection"
    )
    
    is_edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)
    
    # Cached vote counts for performance (updated via update_vote_counts())
    upvotes = models.IntegerField(default=0, help_text="Cached count of upvotes")
    downvotes = models.IntegerField(default=0, help_text="Cached count of downvotes")
    score = models.IntegerField(default=0, help_text="Net score (upvotes - downvotes)")
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['blog_template_name', 'blog_category', 'status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['author']),
            models.Index(fields=['status']),
        ]
        verbose_name = 'Blog Comment'
        verbose_name_plural = 'Blog Comments'
    
    def __str__(self):
        author_display = self.get_author_display()
        blog_display = f"{self.blog_category}/{self.blog_template_name}" if self.blog_category else self.blog_template_name
        return f"Comment by {author_display} on {blog_display}"
    
    def get_author_display(self):
        """Get the display name for the comment author (username or anonymous name)."""
        if self.author:
            return self.author.username
        elif self.author_name:
            return self.author_name
        else:
            return "Anonymous"
    
    def get_author_email(self):
        """Get the email address of the comment author."""
        if self.author:
            return self.author.email
        return self.author_email
    
    def approve(self, user=None):
        """Approve the comment and record moderation metadata."""
        self.status = 'approved'
        self.moderated_at = timezone.now()
        self.moderated_by = user
        self.save(update_fields=['status', 'moderated_at', 'moderated_by'])
    
    def reject(self, user=None, note=''):
        """Reject the comment with optional moderation note."""
        self.status = 'rejected'
        self.moderated_at = timezone.now()
        self.moderated_by = user
        self.moderation_note = note
        self.save(update_fields=['status', 'moderated_at', 'moderated_by', 'moderation_note'])
    
    def mark_as_spam(self, user=None):
        """Mark the comment as spam and record who made the decision."""
        self.status = 'spam'
        self.moderated_at = timezone.now()
        self.moderated_by = user
        self.save(update_fields=['status', 'moderated_at', 'moderated_by'])
    
    def get_replies(self):
        """
        Get approved replies with optimized prefetching for nested structure.
        Includes author data and nested replies for performance.
        """
        return self.replies.filter(status='approved').select_related('author').prefetch_related('replies').order_by('created_at')
    
    def get_blog_url(self):
        """Generate the URL for the blog post this comment belongs to"""
        if self.blog_category:
            return f"/b/{self.blog_category}/{self.blog_template_name}/"
        return f"/b/{self.blog_template_name}/"
    
    def get_depth(self):
        """Calculate the depth of this comment in the thread"""
        depth = 0
        current = self
        while current.parent:
            depth += 1
            current = current.parent
        return depth
    
    @classmethod
    def get_approved_comments(cls, template_name, category=None):
        """
        Get all approved comments for a blog post with optimized nested prefetching.
        
        This method uses recursive prefetching to load nested replies efficiently,
        avoiding N+1 query problems for threaded comment structures.
        
        Args:
            template_name: The blog template name
            category: Optional blog category
            
        Returns:
            QuerySet of top-level approved comments with prefetched replies
        """
        from django.db.models import Prefetch
        
        # Build recursive prefetch for nested reply structure (2 levels deep)
        replies_prefetch = Prefetch(
            'replies',
            queryset=cls.objects.filter(status='approved').select_related('author').prefetch_related(
                Prefetch('replies', queryset=cls.objects.filter(status='approved').select_related('author'))
            ),
        )
        
        queryset = cls.objects.filter(
            blog_template_name=template_name,
            status='approved',
            parent__isnull=True  # Top-level comments only
        ).select_related('author', 'moderated_by').prefetch_related(replies_prefetch)
        
        if category:
            queryset = queryset.filter(blog_category=category)
        
        return queryset
    
    @classmethod
    def get_pending_count(cls):
        """Get the count of pending comments for admin notification badge."""
        return cls.objects.filter(status='pending').count()
    
    def update_vote_counts(self):
        """
        Recalculate and cache vote counts from the CommentVote table.
        Called automatically when votes are added/removed/changed.
        """
        from django.db.models import Count, Q
        
        votes = CommentVote.objects.filter(comment=self).aggregate(
            upvotes=Count('id', filter=Q(vote_type='upvote')),
            downvotes=Count('id', filter=Q(vote_type='downvote'))
        )
        
        self.upvotes = votes['upvotes'] or 0
        self.downvotes = votes['downvotes'] or 0
        self.score = self.upvotes - self.downvotes
        self.save(update_fields=['upvotes', 'downvotes', 'score'])
    
    def get_user_vote(self, user):
        """Check if a user has voted on this comment and return the vote type."""
        if not user or not user.is_authenticated:
            return None
        
        try:
            vote = CommentVote.objects.get(comment=self, user=user)
            return vote.vote_type
        except CommentVote.DoesNotExist:
            return None


class CommentVote(models.Model):
    """
    Track individual user votes on comments.
    Each user can have one vote per comment (upvote or downvote).
    """
    
    VOTE_CHOICES = [
        ('upvote', 'Upvote'),
        ('downvote', 'Downvote'),
    ]
    
    comment = models.ForeignKey(
        BlogComment,
        on_delete=models.CASCADE,
        related_name='votes'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='comment_votes'
    )
    vote_type = models.CharField(
        max_length=10,
        choices=VOTE_CHOICES
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Store IP for potential future anonymous voting feature
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address for anonymous voting tracking"
    )
    
    class Meta:
        unique_together = [('comment', 'user')]  # One vote per user per comment
        indexes = [
            models.Index(fields=['comment', 'user']),
            models.Index(fields=['comment', 'vote_type']),
        ]
        verbose_name = 'Comment Vote'
        verbose_name_plural = 'Comment Votes'
    
    def __str__(self):
        return f"{self.user.username} {self.vote_type}d {self.comment}"
    
    def save(self, *args, **kwargs):
        """Automatically update comment's cached vote counts after saving."""
        super().save(*args, **kwargs)
        self.comment.update_vote_counts()


class KnowledgeGraphScreenshot(models.Model):
    """Model for storing knowledge graph screenshots to avoid runtime generation."""
    
    # Screenshot data
    image = models.ImageField(upload_to='knowledge_graph_screenshots/')

    # Metadata
    graph_data_hash = models.CharField(
        max_length=64,
        blank=True,
        help_text="Hash of the graph data used to generate this screenshot"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['graph_data_hash']),
        ]
    
    def __str__(self):
        return f"Knowledge Graph Screenshot - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
    
    @classmethod
    def get_latest(cls, force_regenerate=False):
        """
        Get the latest screenshot or return None if not found or force_regenerate is True.
        Generation should be handled by the view or management command.
        """
        if not force_regenerate:
            try:
                return cls.objects.latest('created_at')
            except cls.DoesNotExist:
                pass
        
        return None


