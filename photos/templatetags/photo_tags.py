"""
Template tags for working with photos and responsive images.
"""

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def responsive_image(photo, css_class="", alt_text="", loading="lazy", fetchpriority=""):
    """
    Generate a responsive image tag optimized for grid display.

    Uses the thumbnail (400x300) for fast loading.

    Args:
        photo: Photo model instance.
        css_class: CSS class(es) to apply to the image.
        alt_text: Alt text for the image.
        loading: Loading strategy ('lazy' or 'eager').
        fetchpriority: Fetch priority hint ('high', 'low', 'auto', or empty).

    Usage:
        {% load photo_tags %}
        {% responsive_image photo css_class="img-fluid" alt_text="My Photo" %}
        {% responsive_image photo loading="eager" fetchpriority="high" %}
    """
    if not photo or not photo.image:
        return ""

    # Use the title as alt text if not provided
    if not alt_text:
        alt_text = photo.title

    # Escape user-controlled data to prevent XSS
    alt_text = escape(alt_text)
    css_class = escape(css_class)

    # Use thumbnail as the source (optimized 400x300 for grid display)
    default_src = None
    for field in [photo.image_thumbnail, photo.image_preview]:
        if field and field.name:
            try:
                default_src = field.url
                break
            except (ValueError, AttributeError):
                continue

    if not default_src:
        return ""  # No valid image found

    # Build optional attributes
    fetchpriority_attr = f'fetchpriority="{escape(fetchpriority)}"' if fetchpriority else ""

    # Build a simple img tag - thumbnail is already optimized for grid display
    img_tag = f"""
    <img src="{escape(default_src)}"
         class="{css_class}"
         alt="{alt_text}"
         loading="{loading}"
         decoding="async"
         {fetchpriority_attr}
         width="400"
         height="300">
    """

    return mark_safe(img_tag)  # nosec B703 B308 - All user data escaped above


@register.simple_tag
def picture_element(photo, css_class="", alt_text="", loading="lazy"):
    """
    Generate a <picture> element with responsive sources.

    Usage:
        {% load photo_tags %}
        {% picture_element photo css_class="img-fluid" %}
    """
    if not photo or not photo.image:
        return ""

    # Use the title as alt text if not provided
    if not alt_text:
        alt_text = photo.title

    # Escape user-controlled data to prevent XSS
    alt_text = escape(alt_text)
    css_class = escape(css_class)

    # Build the picture element
    picture_html = "<picture>"

    # Add source element for thumbnail
    if photo.image_thumbnail and photo.image_thumbnail.name:
        try:
            picture_html += f"""
        <source srcset="{escape(photo.image_thumbnail.url)}">
        """
        except (ValueError, AttributeError):
            pass

    # Fallback img element (use thumbnail, fallback to preview)
    fallback_src = None
    for field in [photo.image_thumbnail, photo.image_preview]:
        if field and field.name:
            try:
                fallback_src = field.url
                break
            except (ValueError, AttributeError):
                continue

    if not fallback_src:
        return ""  # No valid image found

    picture_html += f"""
    <img src="{escape(fallback_src)}"
         class="{css_class}"
         alt="{alt_text}"
         loading="{loading}">
    </picture>
    """

    return mark_safe(picture_html)  # nosec B703 B308 - All user data escaped above


@register.filter
def photo_url(photo, size="thumbnail"):
    """
    Get the URL for a specific photo size.

    Valid sizes: "preview", "thumbnail", "original"

    Usage:
        {% load photo_tags %}
        {{ photo|photo_url:"thumbnail" }}
        {{ photo|photo_url:"preview" }}
    """
    if not photo:
        return ""

    return photo.get_image_url(size) or ""


@register.filter
def safe_image_url(image_field):
    """
    Safely get URL from an ImageField, returning empty string if no file.

    Usage:
        {% load photo_tags %}
        {{ photo.image_thumbnail|safe_image_url }}
    """
    try:
        if image_field and image_field.name:
            return image_field.url
    except (ValueError, AttributeError):
        # S3 storage may raise errors for missing/invalid files
        pass
    return ""
