"""
Template tags for working with photos and responsive images.
"""

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def responsive_image(photo, css_class="", alt_text="", loading="lazy"):
    """
    Generate a responsive image tag with srcset for different screen sizes.

    Usage:
        {% load photo_tags %}
        {% responsive_image photo css_class="img-fluid" alt_text="My Photo" %}
    """
    if not photo or not photo.image:
        return ""

    # Use the title as alt text if not provided
    if not alt_text:
        alt_text = photo.title

    # Build the srcset attribute
    srcset_parts = []

    if photo.image_display and photo.image_display.name:
        try:
            srcset_parts.append(f"{photo.image_display.url} 1200w")
        except (ValueError, AttributeError):
            # S3 storage may raise errors for missing files - skip this size
            pass

    if photo.image_optimized and photo.image_optimized.name:
        try:
            srcset_parts.append(
                f"{photo.image_optimized.url} {photo.width}w" if photo.width else photo.image_optimized.url
            )
        except (ValueError, AttributeError):
            # S3 storage may raise errors for missing files - skip this size
            pass

    if photo.image and photo.image.name:
        try:
            srcset_parts.append(f"{photo.image.url} {photo.width}w" if photo.width else photo.image.url)
        except (ValueError, AttributeError):
            # S3 storage may raise errors for missing files - skip this size
            pass

    srcset = ", ".join(srcset_parts)

    # Default src (use display version as default, fallback to optimized then original)
    default_src = None
    for field in [photo.image_display, photo.image_optimized, photo.image]:
        if field and field.name:
            try:
                default_src = field.url
                break
            except (ValueError, AttributeError):
                continue

    if not default_src:
        return ""  # No valid image found

    # Build the img tag
    img_tag = f"""
    <img src="{default_src}"
         {f'srcset="{srcset}"' if srcset else ''}
         sizes="(max-width: 400px) 400px,
                (max-width: 800px) 800px,
                (max-width: 1920px) 1920px,
                100vw"
         class="{css_class}"
         alt="{alt_text}"
         loading="{loading}"
         {f'width="{photo.width}"' if photo.width else ''}
         {f'height="{photo.height}"' if photo.height else ''}>
    """

    return mark_safe(img_tag)


@register.simple_tag
def picture_element(photo, css_class="", alt_text="", loading="lazy"):
    """
    Generate a <picture> element with WebP support and responsive sources.

    Usage:
        {% load photo_tags %}
        {% picture_element photo css_class="img-fluid" %}
    """
    if not photo or not photo.image:
        return ""

    # Use the title as alt text if not provided
    if not alt_text:
        alt_text = photo.title

    # Build the picture element with source elements for different sizes
    picture_html = "<picture>"

    # Add source elements for different viewport widths
    if photo.image_optimized and photo.image_optimized.name:
        try:
            picture_html += f"""
        <source media="(min-width: 1200px)"
                srcset="{photo.image_optimized.url}">
        """
        except (ValueError, AttributeError):
            # S3 storage may raise errors for missing files - skip this source
            pass

    if photo.image_display and photo.image_display.name:
        try:
            picture_html += f"""
        <source media="(min-width: 768px)"
                srcset="{photo.image_display.url}">
        """
        except (ValueError, AttributeError):
            # S3 storage may raise errors for missing files - skip this source
            pass

    # Fallback img element (use display for smallest screens, fallback to optimized or original)
    fallback_src = None
    for field in [photo.image_display, photo.image_optimized, photo.image]:
        if field and field.name:
            try:
                fallback_src = field.url
                break
            except (ValueError, AttributeError):
                continue

    if not fallback_src:
        return ""  # No valid image found

    picture_html += f"""
    <img src="{fallback_src}"
         class="{css_class}"
         alt="{alt_text}"
         loading="{loading}">
    </picture>
    """

    return mark_safe(picture_html)


@register.filter
def photo_url(photo, size="medium"):
    """
    Get the URL for a specific photo size.

    Usage:
        {% load photo_tags %}
        {{ photo|photo_url:"large" }}
        {{ photo|photo_url:"thumbnail" }}
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
        {{ photo.image_display|safe_image_url }}
    """
    try:
        if image_field and image_field.name:
            return image_field.url
    except (ValueError, AttributeError):
        # S3 storage may raise errors for missing/invalid files
        pass
    return ""
