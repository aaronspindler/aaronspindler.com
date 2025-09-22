from django import forms
from django.core.exceptions import ValidationError
from .models import BlogComment
import re


class CommentForm(forms.ModelForm):
    """Form for submitting blog comments"""
    
    # Honeypot field for spam detection (hidden via CSS)
    website = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'style': 'display:none;',
            'tabindex': '-1',
            'autocomplete': 'off'
        }),
        label="Leave blank"
    )
    
    class Meta:
        model = BlogComment
        fields = ['content', 'author_name', 'author_email']
        widgets = {
            'content': forms.Textarea(attrs={
                'rows': 6,
                'placeholder': 'Write your comment here...',
                'class': 'comment-textarea',
                'maxlength': '2000'
            }),
            'author_name': forms.TextInput(attrs={
                'placeholder': 'Your name (optional)',
                'class': 'comment-input'
            }),
            'author_email': forms.EmailInput(attrs={
                'placeholder': 'Your email (optional, not displayed)',
                'class': 'comment-input'
            })
        }
        labels = {
            'content': 'Your Comment',
            'author_name': 'Name',
            'author_email': 'Email'
        }
        help_texts = {
            'content': 'Maximum 2000 characters. Markdown is supported.',
            'author_email': 'Your email will not be displayed publicly.'
        }
    
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        
        # If user is authenticated, hide name and email fields
        if user and user.is_authenticated:
            self.fields['author_name'].required = False
            self.fields['author_name'].widget = forms.HiddenInput()
            self.fields['author_email'].required = False
            self.fields['author_email'].widget = forms.HiddenInput()
        else:
            # For anonymous users, at least name is recommended
            self.fields['author_name'].required = False
            self.fields['author_email'].required = False
    
    def clean_website(self):
        """Honeypot field validation - should always be empty"""
        website = self.cleaned_data.get('website')
        if website:
            raise ValidationError("Bot detection triggered")
        return website
    
    def clean_content(self):
        """Validate comment content"""
        content = self.cleaned_data.get('content')
        
        if not content:
            raise ValidationError("Comment cannot be empty")
        
        # Strip whitespace and check if still has content
        content = content.strip()
        if not content:
            raise ValidationError("Comment cannot be just whitespace")
        
        # Check for excessive URLs (potential spam)
        url_pattern = re.compile(r'https?://[^\s]+')
        urls = url_pattern.findall(content)
        if len(urls) > 3:
            raise ValidationError("Too many URLs in comment. Maximum 3 URLs allowed.")
        
        # Check for repeated characters (spam pattern)
        if re.search(r'(.)\1{10,}', content):
            raise ValidationError("Comment appears to be spam")
        
        return content
    
    def clean_author_email(self):
        """Validate email if provided"""
        email = self.cleaned_data.get('author_email')
        if email:
            # Additional email validation if needed
            email = email.strip().lower()
        return email
    
    def save(self, commit=True, blog_template_name=None, blog_category=None, 
             parent=None, ip_address=None, user_agent=None):
        """Save the comment with additional metadata"""
        comment = super().save(commit=False)
        
        # Set the blog post reference
        if blog_template_name:
            comment.blog_template_name = blog_template_name
        if blog_category:
            comment.blog_category = blog_category
        
        # Set the author
        if self.user and self.user.is_authenticated:
            comment.author = self.user
            # Clear anonymous fields if user is authenticated
            comment.author_name = ''
            comment.author_email = ''
        
        # Set parent for replies
        if parent:
            comment.parent = parent
        
        # Set metadata for spam detection
        if ip_address:
            comment.ip_address = ip_address
        if user_agent:
            comment.user_agent = user_agent
        
        # Auto-approve comments from authenticated users or staff
        if self.user and self.user.is_authenticated:
            if self.user.is_staff or self.user.is_superuser:
                comment.status = 'approved'
            else:
                # Could implement a reputation system here
                comment.status = 'pending'
        else:
            comment.status = 'pending'
        
        if commit:
            comment.save()
        
        return comment


class ReplyForm(CommentForm):
    """Form specifically for replying to existing comments"""
    
    class Meta(CommentForm.Meta):
        widgets = {
            'content': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Write your reply...',
                'class': 'reply-textarea',
                'maxlength': '2000'
            }),
            'author_name': forms.TextInput(attrs={
                'placeholder': 'Your name (optional)',
                'class': 'reply-input'
            }),
            'author_email': forms.EmailInput(attrs={
                'placeholder': 'Your email (optional, not displayed)',
                'class': 'reply-input'
            })
        }


class CommentModerationForm(forms.ModelForm):
    """Form for moderating comments in the admin"""
    
    class Meta:
        model = BlogComment
        fields = ['status', 'moderation_note']
        widgets = {
            'status': forms.Select(attrs={'class': 'moderation-select'}),
            'moderation_note': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Optional note about this moderation decision',
                'class': 'moderation-note'
            })
        }
