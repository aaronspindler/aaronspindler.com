from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MaxLengthValidator


class BlogComment(models.Model):
    """Model for blog comments with moderation support"""
    
    # Status choices for moderation
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('spam', 'Spam'),
    ]
    
    # Blog identification (using template name and category)
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
    
    # Comment author information
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='blog_comments',
        help_text="Registered user who made the comment"
    )
    
    # For anonymous comments
    author_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Name for anonymous commenters"
    )
    author_email = models.EmailField(
        blank=True,
        help_text="Email for anonymous commenters (not displayed publicly)"
    )
    
    # Comment content
    content = models.TextField(
        validators=[MaxLengthValidator(2000)],
        help_text="Comment content (max 2000 characters)"
    )
    
    # Parent comment for threaded discussions
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies'
    )
    
    # Metadata
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Moderation
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
    
    # User engagement
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of commenter for spam detection"
    )
    user_agent = models.TextField(
        blank=True,
        help_text="Browser user agent for spam detection"
    )
    
    # Edit tracking
    is_edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)
    
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
        """Get the display name for the comment author"""
        if self.author:
            return self.author.username
        elif self.author_name:
            return self.author_name
        else:
            return "Anonymous"
    
    def get_author_email(self):
        """Get the email address of the comment author"""
        if self.author:
            return self.author.email
        return self.author_email
    
    def approve(self, user=None):
        """Approve the comment"""
        self.status = 'approved'
        self.moderated_at = timezone.now()
        self.moderated_by = user
        self.save(update_fields=['status', 'moderated_at', 'moderated_by'])
    
    def reject(self, user=None, note=''):
        """Reject the comment"""
        self.status = 'rejected'
        self.moderated_at = timezone.now()
        self.moderated_by = user
        self.moderation_note = note
        self.save(update_fields=['status', 'moderated_at', 'moderated_by', 'moderation_note'])
    
    def mark_as_spam(self, user=None):
        """Mark the comment as spam"""
        self.status = 'spam'
        self.moderated_at = timezone.now()
        self.moderated_by = user
        self.save(update_fields=['status', 'moderated_at', 'moderated_by'])
    
    def get_replies(self):
        """Get approved replies to this comment (supports deep nesting)"""
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
        """Get all approved comments for a specific blog post with optimized prefetching"""
        from django.db.models import Prefetch
        
        # Create a recursive prefetch for nested replies
        replies_prefetch = Prefetch(
            'replies',
            queryset=cls.objects.filter(status='approved').select_related('author').prefetch_related(
                Prefetch('replies', queryset=cls.objects.filter(status='approved').select_related('author'))
            ),
        )
        
        queryset = cls.objects.filter(
            blog_template_name=template_name,
            status='approved',
            parent__isnull=True  # Only get top-level comments
        ).select_related('author', 'moderated_by').prefetch_related(replies_prefetch)
        
        if category:
            queryset = queryset.filter(blog_category=category)
        
        return queryset
    
    @classmethod
    def get_pending_count(cls):
        """Get the count of pending comments for admin notification"""
        return cls.objects.filter(status='pending').count()
