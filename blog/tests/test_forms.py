from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from blog.forms import CommentForm, ReplyForm, CommentModerationForm
from blog.models import BlogComment

User = get_user_model()


class CommentFormTest(TestCase):
    """Test CommentForm validation and functionality."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.staff_user = User.objects.create_user(
            username='staffuser',
            email='staff@example.com',
            password='testpass123',
            is_staff=True
        )

    def test_comment_form_valid_data(self):
        """Test form with valid data."""
        form = CommentForm(data={
            'content': 'This is a valid comment',
            'author_name': 'John Doe',
            'author_email': 'john@example.com',
            'website': ''  # Honeypot should be empty
        })
        
        self.assertTrue(form.is_valid())

    def test_comment_form_honeypot_protection(self):
        """Test honeypot field catches bots."""
        form = CommentForm(data={
            'content': 'Spam comment',
            'website': 'http://spam.com'  # Bot filled honeypot
        })
        
        self.assertFalse(form.is_valid())
        self.assertIn('Bot detection triggered', str(form.errors))

    def test_comment_form_empty_content(self):
        """Test that empty content is rejected."""
        form = CommentForm(data={
            'content': '',
            'website': ''
        })
        
        self.assertFalse(form.is_valid())
        self.assertIn('content', form.errors)

    def test_comment_form_whitespace_content(self):
        """Test that whitespace-only content is rejected."""
        form = CommentForm(data={
            'content': '   \n\t   ',
            'website': ''
        })
        
        self.assertFalse(form.is_valid())
        self.assertIn('content', form.errors)
        self.assertIn('cannot be just whitespace', str(form.errors))

    def test_comment_form_excessive_urls(self):
        """Test that comments with too many URLs are rejected."""
        content = '''
        Check out these links:
        http://example1.com
        https://example2.com
        http://example3.com
        https://example4.com
        '''
        
        form = CommentForm(data={
            'content': content,
            'website': ''
        })
        
        self.assertFalse(form.is_valid())
        self.assertIn('Too many URLs', str(form.errors))

    def test_comment_form_repeated_characters_spam(self):
        """Test that repeated character spam is caught."""
        form = CommentForm(data={
            'content': 'This is spaaaaaaaaaaam',
            'website': ''
        })
        
        self.assertFalse(form.is_valid())
        self.assertIn('appears to be spam', str(form.errors))

    def test_comment_form_authenticated_user(self):
        """Test form for authenticated users hides author fields."""
        form = CommentForm(user=self.user)
        
        # Author fields should be hidden for authenticated users
        self.assertEqual(form.fields['author_name'].widget.__class__.__name__, 'HiddenInput')
        self.assertEqual(form.fields['author_email'].widget.__class__.__name__, 'HiddenInput')

    def test_comment_form_anonymous_user(self):
        """Test form for anonymous users shows author fields."""
        form = CommentForm(user=None)
        
        # Author fields should be visible for anonymous users
        self.assertEqual(form.fields['author_name'].widget.__class__.__name__, 'TextInput')
        self.assertEqual(form.fields['author_email'].widget.__class__.__name__, 'EmailInput')

    def test_comment_form_email_normalization(self):
        """Test that email addresses are normalized to lowercase."""
        form = CommentForm(data={
            'content': 'Test comment',
            'author_email': 'John.Doe@Example.COM',
            'website': ''
        })
        
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['author_email'], 'john.doe@example.com')

    def test_comment_form_save_with_user(self):
        """Test saving form with authenticated user."""
        form = CommentForm(data={
            'content': 'User comment',
            'website': ''
        }, user=self.user)
        
        self.assertTrue(form.is_valid())
        
        comment = form.save(
            blog_template_name='0001_test_post',
            blog_category='tech',
            ip_address='192.168.1.1',
            user_agent='Mozilla/5.0'
        )
        
        self.assertEqual(comment.author, self.user)
        self.assertEqual(comment.author_name, '')
        self.assertEqual(comment.author_email, '')
        self.assertEqual(comment.blog_template_name, '0001_test_post')
        self.assertEqual(comment.blog_category, 'tech')
        self.assertEqual(comment.ip_address, '192.168.1.1')
        self.assertEqual(comment.user_agent, 'Mozilla/5.0')
        self.assertEqual(comment.status, 'pending')

    def test_comment_form_save_staff_auto_approved(self):
        """Test that staff comments are auto-approved."""
        form = CommentForm(data={
            'content': 'Staff comment',
            'website': ''
        }, user=self.staff_user)
        
        self.assertTrue(form.is_valid())
        
        comment = form.save(blog_template_name='0001_test_post')
        
        self.assertEqual(comment.author, self.staff_user)
        self.assertEqual(comment.status, 'approved')  # Auto-approved for staff

    def test_comment_form_save_anonymous(self):
        """Test saving form with anonymous user."""
        form = CommentForm(data={
            'content': 'Anonymous comment',
            'author_name': 'Jane Doe',
            'author_email': 'jane@example.com',
            'website': ''
        }, user=None)
        
        self.assertTrue(form.is_valid())
        
        comment = form.save(blog_template_name='0001_test_post')
        
        self.assertIsNone(comment.author)
        self.assertEqual(comment.author_name, 'Jane Doe')
        self.assertEqual(comment.author_email, 'jane@example.com')
        self.assertEqual(comment.status, 'pending')

    def test_comment_form_save_with_parent(self):
        """Test saving reply comment."""
        parent_comment = BlogComment.objects.create(
            blog_template_name='0001_test_post',
            content='Parent comment',
            status='approved'
        )
        
        form = CommentForm(data={
            'content': 'Reply comment',
            'website': ''
        }, user=self.user)
        
        self.assertTrue(form.is_valid())
        
        reply = form.save(
            blog_template_name='0001_test_post',
            parent=parent_comment
        )
        
        self.assertEqual(reply.parent, parent_comment)

    def test_comment_form_max_length(self):
        """Test that content respects max length."""
        # Content at max length should be valid
        max_content = 'x' * 2000
        form = CommentForm(data={
            'content': max_content,
            'website': ''
        })
        self.assertTrue(form.is_valid())
        
        # Content over max length should show in widget attributes
        self.assertEqual(form.fields['content'].widget.attrs['maxlength'], '2000')

    def test_comment_form_markdown_support(self):
        """Test that markdown content is accepted."""
        markdown_content = """
        # Heading
        
        This is **bold** and this is *italic*.
        
        - List item 1
        - List item 2
        
        ```python
        print("Code block")
        ```
        """
        
        form = CommentForm(data={
            'content': markdown_content,
            'website': ''
        })
        
        self.assertTrue(form.is_valid())


class ReplyFormTest(TestCase):
    """Test ReplyForm specific functionality."""

    def test_reply_form_inherits_from_comment_form(self):
        """Test that ReplyForm inherits CommentForm functionality."""
        self.assertTrue(issubclass(ReplyForm, CommentForm))

    def test_reply_form_smaller_textarea(self):
        """Test that reply form has smaller textarea."""
        form = ReplyForm()
        
        # Check that reply textarea has fewer rows
        self.assertEqual(form.fields['content'].widget.attrs['rows'], 4)
        self.assertEqual(form.fields['content'].widget.attrs['class'], 'reply-textarea')

    def test_reply_form_placeholder_text(self):
        """Test reply form has appropriate placeholder."""
        form = ReplyForm()
        
        self.assertEqual(
            form.fields['content'].widget.attrs['placeholder'],
            'Write your reply...'
        )


class CommentModerationFormTest(TestCase):
    """Test CommentModerationForm functionality."""

    def setUp(self):
        self.comment = BlogComment.objects.create(
            blog_template_name='0001_test_post',
            content='Test comment',
            status='pending'
        )

    def test_moderation_form_fields(self):
        """Test moderation form has correct fields."""
        form = CommentModerationForm()
        
        self.assertIn('status', form.fields)
        self.assertIn('moderation_note', form.fields)

    def test_moderation_form_status_choices(self):
        """Test that status field has correct choices."""
        form = CommentModerationForm()
        
        status_choices = dict(form.fields['status'].choices)
        self.assertIn('pending', status_choices)
        self.assertIn('approved', status_choices)
        self.assertIn('rejected', status_choices)
        self.assertIn('spam', status_choices)

    def test_moderation_form_valid_data(self):
        """Test moderation form with valid data."""
        form = CommentModerationForm(data={
            'status': 'approved',
            'moderation_note': 'Looks good'
        })
        
        self.assertTrue(form.is_valid())

    def test_moderation_form_save(self):
        """Test saving moderation form updates comment."""
        form = CommentModerationForm(
            instance=self.comment,
            data={
                'status': 'rejected',
                'moderation_note': 'Inappropriate content'
            }
        )
        
        self.assertTrue(form.is_valid())
        comment = form.save()
        
        self.assertEqual(comment.status, 'rejected')
        self.assertEqual(comment.moderation_note, 'Inappropriate content')

    def test_moderation_form_widget_classes(self):
        """Test that form widgets have appropriate CSS classes."""
        form = CommentModerationForm()
        
        self.assertEqual(
            form.fields['status'].widget.attrs['class'],
            'moderation-select'
        )
        self.assertEqual(
            form.fields['moderation_note'].widget.attrs['class'],
            'moderation-note'
        )
