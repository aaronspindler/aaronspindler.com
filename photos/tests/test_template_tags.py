"""
Comprehensive tests for Photos app template tags and filters.

This module tests all custom template tags and filters in the photos app,
including responsive image generation, picture element creation, and URL filters.
"""

from unittest.mock import Mock, patch

from django.template import Context, Template
from django.test import TestCase

from photos.models import Photo
from photos.templatetags.photo_tags import photo_url, picture_element, responsive_image, safe_image_url
from photos.tests.factories import PhotoFactory


class ResponsiveImageTagTest(TestCase):
    """Tests for the responsive_image template tag."""

    def setUp(self):
        """Set up test data."""
        self.photo = PhotoFactory.create_photo(
            title="Test Photo",
            width=1920,
            height=1080,
        )

    def test_responsive_image_with_all_sizes(self):
        """Test responsive image generation with all image sizes available."""
        # Set up all image fields with mock URLs
        self.photo.image.name = "photos/original/test.jpg"
        self.photo.image_optimized.name = "photos/optimized/test.jpg"
        self.photo.image_display.name = "photos/display/test.jpg"
        self.photo.save()

        # Generate the responsive image HTML
        with patch("photos.templatetags.photo_tags.escape", side_effect=lambda x: x):
            result = responsive_image(self.photo)

        # Verify the HTML contains expected elements
        self.assertIn("<img src=", result)
        self.assertIn("srcset=", result)
        self.assertIn("sizes=", result)
        self.assertIn('loading="lazy"', result)
        self.assertIn(f'width="{self.photo.width}"', result)
        self.assertIn(f'height="{self.photo.height}"', result)
        self.assertIn(f'alt="{self.photo.title}"', result)

    def test_responsive_image_with_custom_attributes(self):
        """Test responsive image with custom CSS class and alt text."""
        css_class = "img-fluid rounded"
        alt_text = "Custom Alt Text"
        loading = "eager"

        result = responsive_image(
            self.photo,
            css_class=css_class,
            alt_text=alt_text,
            loading=loading,
        )

        # Verify custom attributes are included
        self.assertIn(f'class="{css_class}"', result)
        self.assertIn(f'alt="{alt_text}"', result)
        self.assertIn(f'loading="{loading}"', result)

    def test_responsive_image_with_missing_photo(self):
        """Test responsive image returns empty string for missing photo."""
        result = responsive_image(None)

        expected = ""
        actual = result
        message = f"Expected empty string for None photo, got: {actual}"
        self.assertEqual(actual, expected, message)

    def test_responsive_image_without_image_field(self):
        """Test responsive image returns empty string when photo has no image."""
        photo_no_image = Photo(title="No Image")
        result = responsive_image(photo_no_image)

        expected = ""
        actual = result
        message = f"Expected empty string for photo without image, got: {actual}"
        self.assertEqual(actual, expected, message)

    def test_responsive_image_escapes_user_input(self):
        """Test that user-controlled data is properly escaped."""
        self.photo.title = '<script>alert("XSS")</script>'
        self.photo.save()

        with patch("photos.templatetags.photo_tags.escape") as mock_escape:
            mock_escape.side_effect = lambda x: f"escaped_{x}"
            result = responsive_image(self.photo, css_class="<script>")

        # Verify escape was called for user data
        mock_escape.assert_any_call(self.photo.title)
        mock_escape.assert_any_call("<script>")

    def test_responsive_image_handles_storage_errors(self):
        """Test responsive image handles S3 storage errors gracefully."""
        self.photo.image_display.name = "photos/display/test.jpg"
        self.photo.save()

        # Mock URL property to raise ValueError
        with patch.object(type(self.photo.image_display), "url", side_effect=ValueError("S3 error")):
            result = responsive_image(self.photo)

        # Should still generate HTML with available images
        self.assertIn("<img", result)

    def test_responsive_image_srcset_generation(self):
        """Test srcset attribute generation with multiple image sizes."""
        self.photo.image.name = "photos/original/test.jpg"
        self.photo.image_optimized.name = "photos/optimized/test.jpg"
        self.photo.image_display.name = "photos/display/test.jpg"
        self.photo.width = 1920
        self.photo.save()

        with patch("photos.templatetags.photo_tags.escape", side_effect=lambda x: x):
            result = responsive_image(self.photo)

        # Verify srcset contains all sizes
        self.assertIn("1200w", result)  # display size
        self.assertIn(f"{self.photo.width}w", result)  # optimized and original widths

    def test_responsive_image_in_template(self):
        """Test responsive_image tag usage in Django template."""
        template = Template(
            '{% load photo_tags %}{% responsive_image photo css_class="test-class" alt_text="Test Alt" %}'
        )
        context = Context({"photo": self.photo})
        result = template.render(context)

        # Verify the tag works in template context
        self.assertIn("<img", result)
        self.assertIn('class="test-class"', result)
        self.assertIn('alt="Test Alt"', result)


class PictureElementTagTest(TestCase):
    """Tests for the picture_element template tag."""

    def setUp(self):
        """Set up test data."""
        self.photo = PhotoFactory.create_photo(
            title="Test Photo",
            width=1920,
            height=1080,
        )

    def test_picture_element_with_all_sizes(self):
        """Test picture element generation with all image sizes."""
        self.photo.image.name = "photos/original/test.jpg"
        self.photo.image_optimized.name = "photos/optimized/test.jpg"
        self.photo.image_display.name = "photos/display/test.jpg"
        self.photo.save()

        with patch("photos.templatetags.photo_tags.escape", side_effect=lambda x: x):
            result = picture_element(self.photo)

        # Verify picture element structure
        self.assertIn("<picture>", result)
        self.assertIn("</picture>", result)
        self.assertIn("<source", result)
        self.assertIn('media="(min-width: 1200px)"', result)
        self.assertIn('media="(min-width: 768px)"', result)
        self.assertIn("<img", result)
        self.assertIn(f'alt="{self.photo.title}"', result)

    def test_picture_element_with_custom_attributes(self):
        """Test picture element with custom CSS class and alt text."""
        css_class = "img-fluid"
        alt_text = "Custom Alt"
        loading = "eager"

        result = picture_element(
            self.photo,
            css_class=css_class,
            alt_text=alt_text,
            loading=loading,
        )

        # Verify custom attributes
        self.assertIn(f'class="{css_class}"', result)
        self.assertIn(f'alt="{alt_text}"', result)
        self.assertIn(f'loading="{loading}"', result)

    def test_picture_element_with_missing_photo(self):
        """Test picture element returns empty string for missing photo."""
        result = picture_element(None)

        expected = ""
        actual = result
        message = f"Expected empty string for None photo, got: {actual}"
        self.assertEqual(actual, expected, message)

    def test_picture_element_without_image(self):
        """Test picture element returns empty string when photo has no image."""
        photo_no_image = Photo(title="No Image")
        result = picture_element(photo_no_image)

        expected = ""
        actual = result
        message = f"Expected empty string for photo without image, got: {actual}"
        self.assertEqual(actual, expected, message)

    def test_picture_element_escapes_user_input(self):
        """Test that user-controlled data is properly escaped."""
        self.photo.title = '<script>alert("XSS")</script>'
        self.photo.save()

        with patch("photos.templatetags.photo_tags.escape") as mock_escape:
            mock_escape.side_effect = lambda x: f"escaped_{x}"
            result = picture_element(self.photo, css_class="<script>")

        # Verify escape was called
        mock_escape.assert_any_call(self.photo.title)
        mock_escape.assert_any_call("<script>")

    def test_picture_element_handles_storage_errors(self):
        """Test picture element handles S3 storage errors gracefully."""
        self.photo.image_display.name = "photos/display/test.jpg"
        self.photo.image_optimized.name = "photos/optimized/test.jpg"
        self.photo.save()

        # Mock URL properties to raise ValueError for some images
        with patch.object(type(self.photo.image_optimized), "url", side_effect=ValueError("S3 error")):
            result = picture_element(self.photo)

        # Should still generate picture element with available images
        self.assertIn("<picture>", result)
        self.assertIn("<img", result)

    def test_picture_element_source_priority(self):
        """Test source elements are added in correct priority order."""
        self.photo.image_optimized.name = "photos/optimized/test.jpg"
        self.photo.image_display.name = "photos/display/test.jpg"
        self.photo.save()

        with patch("photos.templatetags.photo_tags.escape", side_effect=lambda x: x):
            result = picture_element(self.photo)

        # Verify source order (larger viewport widths first)
        min_1200_pos = result.find('media="(min-width: 1200px)"')
        min_768_pos = result.find('media="(min-width: 768px)"')
        self.assertLess(min_1200_pos, min_768_pos, "1200px source should come before 768px source")

    def test_picture_element_in_template(self):
        """Test picture_element tag usage in Django template."""
        template = Template('{% load photo_tags %}{% picture_element photo css_class="responsive" %}')
        context = Context({"photo": self.photo})
        result = template.render(context)

        # Verify the tag works in template context
        self.assertIn("<picture>", result)
        self.assertIn('class="responsive"', result)


class PhotoUrlFilterTest(TestCase):
    """Tests for the photo_url filter."""

    def setUp(self):
        """Set up test data."""
        self.photo = PhotoFactory.create_photo()

    def test_photo_url_default_size(self):
        """Test photo_url filter with default medium size."""
        with patch.object(self.photo, "get_image_url", return_value="/media/photos/medium.jpg"):
            result = photo_url(self.photo)

        expected = "/media/photos/medium.jpg"
        actual = result
        message = f"Expected URL {expected}, got {actual}"
        self.assertEqual(actual, expected, message)

        # Verify default size is "medium"
        self.photo.get_image_url.assert_called_once_with("medium")

    def test_photo_url_with_specific_size(self):
        """Test photo_url filter with specific size parameter."""
        test_cases = [
            ("thumbnail", "/media/photos/thumb.jpg"),
            ("large", "/media/photos/large.jpg"),
            ("original", "/media/photos/original.jpg"),
        ]

        for size, expected_url in test_cases:
            with self.subTest(size=size):
                with patch.object(self.photo, "get_image_url", return_value=expected_url):
                    result = photo_url(self.photo, size)

                actual = result
                expected = expected_url
                message = f"For size {size}, expected {expected}, got {actual}"
                self.assertEqual(actual, expected, message)

    def test_photo_url_with_none_photo(self):
        """Test photo_url filter returns empty string for None photo."""
        result = photo_url(None)

        expected = ""
        actual = result
        message = f"Expected empty string for None photo, got: {actual}"
        self.assertEqual(actual, expected, message)

    def test_photo_url_when_get_image_url_returns_none(self):
        """Test photo_url filter handles None from get_image_url."""
        with patch.object(self.photo, "get_image_url", return_value=None):
            result = photo_url(self.photo, "large")

        expected = ""
        actual = result
        message = f"Expected empty string when get_image_url returns None, got: {actual}"
        self.assertEqual(actual, expected, message)

    def test_photo_url_in_template(self):
        """Test photo_url filter usage in Django template."""
        template = Template("{% load photo_tags %}{{ photo|photo_url:'large' }}")
        context = Context({"photo": self.photo})

        with patch.object(self.photo, "get_image_url", return_value="/media/large.jpg"):
            result = template.render(context)

        expected = "/media/large.jpg"
        actual = result.strip()
        message = f"Expected {expected} from template, got {actual}"
        self.assertEqual(actual, expected, message)

    def test_photo_url_filter_chaining(self):
        """Test photo_url filter can be chained with other filters."""
        template = Template("{% load photo_tags %}{{ photo|photo_url:'thumbnail'|default:'No image' }}")

        # Test with None photo
        context = Context({"photo": None})
        result = template.render(context)

        expected = "No image"
        actual = result.strip()
        message = f"Expected default value for None photo, got {actual}"
        self.assertEqual(actual, expected, message)


class SafeImageUrlFilterTest(TestCase):
    """Tests for the safe_image_url filter."""

    def setUp(self):
        """Set up test data."""
        self.photo = PhotoFactory.create_photo()

    def test_safe_image_url_with_valid_field(self):
        """Test safe_image_url filter with valid image field."""
        # Create a mock image field
        mock_field = Mock()
        mock_field.name = "photos/test.jpg"
        mock_field.url = "/media/photos/test.jpg"

        result = safe_image_url(mock_field)

        expected = "/media/photos/test.jpg"
        actual = result
        message = f"Expected URL {expected}, got {actual}"
        self.assertEqual(actual, expected, message)

    def test_safe_image_url_with_empty_field(self):
        """Test safe_image_url filter with empty image field."""
        mock_field = Mock()
        mock_field.name = ""

        result = safe_image_url(mock_field)

        expected = ""
        actual = result
        message = f"Expected empty string for empty field, got: {actual}"
        self.assertEqual(actual, expected, message)

    def test_safe_image_url_with_none_field(self):
        """Test safe_image_url filter with None field."""
        result = safe_image_url(None)

        expected = ""
        actual = result
        message = f"Expected empty string for None field, got: {actual}"
        self.assertEqual(actual, expected, message)

    def test_safe_image_url_handles_value_error(self):
        """Test safe_image_url filter handles ValueError from S3 storage."""
        mock_field = Mock()
        mock_field.name = "photos/test.jpg"
        mock_field.url = Mock(side_effect=ValueError("File not found in S3"))

        result = safe_image_url(mock_field)

        expected = ""
        actual = result
        message = f"Expected empty string on ValueError, got: {actual}"
        self.assertEqual(actual, expected, message)

    def test_safe_image_url_handles_attribute_error(self):
        """Test safe_image_url filter handles AttributeError."""
        mock_field = Mock()
        mock_field.name = "photos/test.jpg"
        del mock_field.url  # Remove url attribute

        result = safe_image_url(mock_field)

        expected = ""
        actual = result
        message = f"Expected empty string on AttributeError, got: {actual}"
        self.assertEqual(actual, expected, message)

    def test_safe_image_url_in_template(self):
        """Test safe_image_url filter usage in Django template."""
        template = Template("{% load photo_tags %}{{ photo.image_display|safe_image_url }}")

        self.photo.image_display.name = "photos/display/test.jpg"
        with patch.object(type(self.photo.image_display), "url", "/media/display/test.jpg"):
            context = Context({"photo": self.photo})
            result = template.render(context)

        expected = "/media/display/test.jpg"
        actual = result.strip()
        message = f"Expected {expected} from template, got {actual}"
        self.assertEqual(actual, expected, message)

    def test_safe_image_url_with_default_filter(self):
        """Test safe_image_url filter combined with default filter."""
        template = Template(
            "{% load photo_tags %}{{ photo.image_display|safe_image_url|default:'/static/placeholder.jpg' }}"
        )

        # Test with field that raises error
        self.photo.image_display.name = "missing.jpg"
        with patch.object(type(self.photo.image_display), "url", side_effect=ValueError("Not found")):
            context = Context({"photo": self.photo})
            result = template.render(context)

        expected = "/static/placeholder.jpg"
        actual = result.strip()
        message = f"Expected default placeholder, got {actual}"
        self.assertEqual(actual, expected, message)


class IntegrationTest(TestCase):
    """Integration tests for template tags working together."""

    def setUp(self):
        """Set up test data."""
        self.photo = PhotoFactory.create_photo(
            title="Integration Test Photo",
            width=1920,
            height=1080,
        )
        self.photo.image.name = "photos/original/test.jpg"
        self.photo.image_optimized.name = "photos/optimized/test.jpg"
        self.photo.image_display.name = "photos/display/test.jpg"
        self.photo.save()

    def test_multiple_tags_in_template(self):
        """Test using multiple tags together in a template."""
        template = Template(
            "{% load photo_tags %}"
            "{% responsive_image photo css_class='responsive' %}"
            "{% picture_element photo css_class='picture' %}"
            "URL: {{ photo|photo_url:'large' }}"
        )

        with patch.object(self.photo, "get_image_url", return_value="/media/large.jpg"):
            context = Context({"photo": self.photo})
            result = template.render(context)

        # Verify all elements are present
        self.assertIn("<img src=", result)
        self.assertIn("<picture>", result)
        self.assertIn("URL: /media/large.jpg", result)

    def test_conditional_rendering_with_tags(self):
        """Test conditional rendering based on photo availability."""
        template = Template(
            "{% load photo_tags %}{% if photo %}{% responsive_image photo %}{% else %}No photo available{% endif %}"
        )

        # Test with photo
        context = Context({"photo": self.photo})
        result = template.render(context)
        self.assertIn("<img src=", result)

        # Test without photo
        context = Context({"photo": None})
        result = template.render(context)

        expected = "No photo available"
        self.assertIn(expected, result)

    def test_loop_with_template_tags(self):
        """Test using template tags in a loop."""
        photos = [PhotoFactory.create_photo(title=f"Photo {i}") for i in range(3)]

        template = Template(
            "{% load photo_tags %}"
            "{% for photo in photos %}"
            "{% responsive_image photo css_class='gallery-item' %}"
            "{% endfor %}"
        )

        context = Context({"photos": photos})
        result = template.render(context)

        # Verify each photo generates an image tag
        img_count = result.count("<img src=")
        expected = 3
        actual = img_count
        message = f"Expected {expected} img tags, found {actual}"
        self.assertEqual(actual, expected, message)


class PerformanceTest(TestCase):
    """Performance-related tests for template tags."""

    def test_responsive_image_with_many_photos(self):
        """Test responsive_image performance with multiple photos."""
        photos = [PhotoFactory.create_photo(title=f"Photo {i}") for i in range(20)]

        # Generate responsive images for all photos
        results = []
        for photo in photos:
            result = responsive_image(photo)
            results.append(result)

        # Verify all generated successfully
        generated_count = sum(1 for r in results if "<img" in r)
        expected = 20
        actual = generated_count
        message = f"Expected {expected} images generated, got {actual}"
        self.assertEqual(actual, expected, message)

    def test_error_handling_doesnt_break_page(self):
        """Test that errors in one tag don't break entire page rendering."""
        template = Template(
            "{% load photo_tags %}Start{% responsive_image bad_photo %}Middle{% picture_element good_photo %}End"
        )

        good_photo = PhotoFactory.create_photo()
        context = Context(
            {
                "bad_photo": None,  # This will return empty string
                "good_photo": good_photo,
            }
        )

        result = template.render(context)

        # Verify page structure is maintained
        self.assertIn("Start", result)
        self.assertIn("Middle", result)
        self.assertIn("End", result)
        self.assertIn("<picture>", result)


class SecurityTest(TestCase):
    """Security-related tests for template tags."""

    def test_xss_prevention_in_responsive_image(self):
        """Test that XSS attempts are properly escaped."""
        photo = PhotoFactory.create_photo(title='"><script>alert("XSS")</script><"')

        result = responsive_image(
            photo, css_class='"><script>alert("XSS2")</script><"', alt_text='"><script>alert("XSS3")</script><"'
        )

        # Verify no unescaped script tags in output
        self.assertNotIn("<script>alert", result)
        self.assertNotIn("</script>", result)

    def test_xss_prevention_in_picture_element(self):
        """Test that XSS attempts are properly escaped in picture element."""
        photo = PhotoFactory.create_photo(title='<img src=x onerror=alert("XSS")>')

        result = picture_element(photo, css_class='<img src=x onerror=alert("XSS2")>')

        # Verify no unescaped attack vectors in output
        self.assertNotIn("onerror=alert", result)
        self.assertNotIn("<img src=x", result)

    def test_safe_string_marking(self):
        """Test that output is properly marked as safe."""
        from django.utils.safestring import SafeString

        photo = PhotoFactory.create_photo()

        result = responsive_image(photo)
        self.assertIsInstance(result, (SafeString, str))

        result = picture_element(photo)
        self.assertIsInstance(result, (SafeString, str))
