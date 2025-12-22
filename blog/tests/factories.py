class BlogCommentFactory:
    @staticmethod
    def create_comment(
        blog_template_name="0001_test_post",
        blog_category="tech",
        content="This is a test comment",
        author=None,
        author_name=None,
        author_email=None,
        status="pending",
        parent=None,
        **kwargs,
    ):
        from blog.models import BlogComment

        if author and author_name is None:
            author_name = ""
        elif not author and author_name is None:
            author_name = "Anonymous"

        # Similar logic for author_email
        if author and author_email is None:
            author_email = ""
        elif not author and author_email is None:
            author_email = "anonymous@example.com"

        return BlogComment.objects.create(
            blog_template_name=blog_template_name,
            blog_category=blog_category,
            content=content,
            author=author,
            author_name=author_name,
            author_email=author_email,
            status=status,
            parent=parent,
            **kwargs,
        )

    @staticmethod
    def create_approved_comment(**kwargs):
        kwargs.setdefault("status", "approved")
        return BlogCommentFactory.create_comment(**kwargs)

    @staticmethod
    def create_pending_comment(**kwargs):
        kwargs.setdefault("status", "pending")
        return BlogCommentFactory.create_comment(**kwargs)

    @staticmethod
    def create_anonymous_comment(author_name="John Doe", author_email="john@example.com", **kwargs):
        return BlogCommentFactory.create_comment(
            author=None, author_name=author_name, author_email=author_email, **kwargs
        )

    @staticmethod
    def create_comment_vote(comment, user, vote_type="upvote", ip_address=None, **kwargs):
        from blog.models import CommentVote

        return CommentVote.objects.create(
            comment=comment,
            user=user,
            vote_type=vote_type,
            ip_address=ip_address,
            **kwargs,
        )


class MockDataFactory:
    @staticmethod
    def get_mock_blog_data(
        entry_number="0001",
        template_name="0001_test_post",
        blog_title="0001 test post",
        blog_content="<p>Test content</p>",
        category="tech",
        github_link="https://github.com/test",
    ):
        return {
            "entry_number": entry_number,
            "template_name": template_name,
            "blog_title": blog_title,
            "blog_content": blog_content,
            "category": category,
            "github_link": github_link,
        }

    @staticmethod
    def get_common_ip_addresses():
        return {
            "local_ipv4": "127.0.0.1",
            "private_ipv4": "192.168.1.1",
            "public_ipv4": "8.8.8.8",
            "google_dns": "8.8.4.4",
            "ipv6": "2001:0db8:85a3:0000:0000:8a2e:0370:7334",
        }

    @staticmethod
    def get_common_form_data():
        return {
            "comment_form": {
                "content": "This is a test comment",
                "author_name": "Test User",
                "author_email": "test@example.com",
                "website": "",  # Honeypot field
            },
            "user_form": {
                "username": "testuser",
                "email": "test@example.com",
                "password1": "testpass123",
                "password2": "testpass123",
            },
        }
