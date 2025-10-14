from django.conf import settings
from django.test import RequestFactory, TestCase

from pages.context_processors import resume_context


class ResumeContextProcessorTest(TestCase):
    """Test the resume_context context processor."""

    def setUp(self):
        self.factory = RequestFactory()

    def test_resume_context_with_settings(self):
        """Test context processor when settings are defined."""
        request = self.factory.get("/")

        with self.settings(RESUME_ENABLED=True, RESUME_FILENAME="test_resume.pdf"):
            context = resume_context(request)

            self.assertIn("RESUME_ENABLED", context)
            self.assertIn("RESUME_FILENAME", context)
            self.assertTrue(context["RESUME_ENABLED"])
            self.assertEqual(context["RESUME_FILENAME"], "test_resume.pdf")

    def test_resume_context_without_settings(self):
        """Test context processor when settings are not defined."""
        request = self.factory.get("/")

        # Remove settings if they exist
        if hasattr(settings, "RESUME_ENABLED"):
            delattr(settings, "RESUME_ENABLED")
        if hasattr(settings, "RESUME_FILENAME"):
            delattr(settings, "RESUME_FILENAME")

        context = resume_context(request)

        self.assertIn("RESUME_ENABLED", context)
        self.assertIn("RESUME_FILENAME", context)
        self.assertFalse(context["RESUME_ENABLED"])  # Default to False
        self.assertEqual(context["RESUME_FILENAME"], "")  # Default to empty string

    def test_resume_context_disabled(self):
        """Test context processor when resume is disabled."""
        request = self.factory.get("/")

        with self.settings(RESUME_ENABLED=False):
            context = resume_context(request)

            self.assertFalse(context["RESUME_ENABLED"])

    def test_resume_context_partial_settings(self):
        """Test context processor with partial settings."""
        request = self.factory.get("/")

        # Only RESUME_ENABLED is set
        with self.settings(RESUME_ENABLED=True):
            # Remove RESUME_FILENAME if it exists
            if hasattr(settings, "RESUME_FILENAME"):
                delattr(settings, "RESUME_FILENAME")

            context = resume_context(request)

            self.assertTrue(context["RESUME_ENABLED"])
            self.assertEqual(context["RESUME_FILENAME"], "")

    def test_resume_context_returns_dict(self):
        """Test that context processor returns a dictionary."""
        request = self.factory.get("/")

        context = resume_context(request)

        self.assertIsInstance(context, dict)

    def test_resume_context_different_requests(self):
        """Test context processor with different request types."""
        # Test with GET request
        get_request = self.factory.get("/")
        context_get = resume_context(get_request)
        self.assertIsInstance(context_get, dict)

        # Test with POST request
        post_request = self.factory.post("/")
        context_post = resume_context(post_request)
        self.assertIsInstance(context_post, dict)

        # Context should be the same regardless of request method
        self.assertEqual(context_get, context_post)

    def test_resume_context_with_various_filenames(self):
        """Test context processor with various filename formats."""
        request = self.factory.get("/")

        test_filenames = [
            "resume.pdf",
            "Resume_2024.pdf",
            "John_Doe_Resume.pdf",
            "resume-final-v2.pdf",
            "CV.pdf",
        ]

        for filename in test_filenames:
            with self.settings(RESUME_FILENAME=filename):
                context = resume_context(request)

                self.assertEqual(context["RESUME_FILENAME"], filename)

    def test_resume_context_immutability(self):
        """Test that context processor doesn't modify request."""
        request = self.factory.get("/")
        request.custom_attr = "test_value"

        context = resume_context(request)

        # Request should not be modified
        self.assertEqual(request.custom_attr, "test_value")

    def test_resume_context_keys_are_strings(self):
        """Test that context keys are strings."""
        request = self.factory.get("/")

        context = resume_context(request)

        for key in context.keys():
            self.assertIsInstance(key, str)
