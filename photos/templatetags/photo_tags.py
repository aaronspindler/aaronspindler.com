"""
Template tags for working with photos and responsive images.
"""

from django import template
from django.utils.html import escape
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

    # Escape user-controlled data to prevent XSS
    alt_text = escape(alt_text)
    css_class = escape(css_class)

    # Build the srcset attribute
    srcset_parts = []

    if photo.image_gallery_cropped and photo.image_gallery_cropped.name:
        try:
            srcset_parts.append(f"{escape(photo.image_gallery_cropped.url)} 1200w")
        except (ValueError, AttributeError):
            # S3 storage may raise errors for missing files - skip this size
            pass

    if photo.image and photo.image.name:
        try:
            srcset_parts.append(f"{escape(photo.image.url)} {photo.width}w" if photo.width else escape(photo.image.url))
        except (ValueError, AttributeError):
            # S3 storage may raise errors for missing files - skip this size
            pass

    srcset = ", ".join(srcset_parts)

    # Default src (use gallery_cropped version as default, fallback to preview)
    default_src = None
    for field in [photo.image_gallery_cropped, photo.image_preview]:
        if field and field.name:
            try:
                default_src = field.url
                break
            except (ValueError, AttributeError):
                continue

    if not default_src:
        return ""  # No valid image found

    # Build the img tag with escaped values
    img_tag = f"""
    <img src="{escape(default_src)}"
         {f'srcset="{srcset}"' if srcset else ""}
         sizes="(max-width: 400px) 400px,
                (max-width: 800px) 800px,
                (max-width: 1920px) 1920px,
                100vw"
         class="{css_class}"
         alt="{alt_text}"
         loading="{loading}"
         {f'width="{photo.width}"' if photo.width else ""}
         {f'height="{photo.height}"' if photo.height else ""}>
    """

    return mark_safe(img_tag)  # nosec B703 B308 - All user data escaped above


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

    # Escape user-controlled data to prevent XSS
    alt_text = escape(alt_text)
    css_class = escape(css_class)

    # Build the picture element with source elements for different sizes
    picture_html = "<picture>"

    # Add source element for gallery_cropped on larger viewports
    if photo.image_gallery_cropped and photo.image_gallery_cropped.name:
        try:
            picture_html += f"""
        <source media="(min-width: 768px)"
                srcset="{escape(photo.image_gallery_cropped.url)}">
        """
        except (ValueError, AttributeError):
            # S3 storage may raise errors for missing files - skip this source
            pass

    # Fallback img element (use gallery_cropped, fallback to preview)
    fallback_src = None
    for field in [photo.image_gallery_cropped, photo.image_preview]:
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
def photo_url(photo, size="gallery_cropped"):
    """
    Get the URL for a specific photo size.

    Valid sizes: "preview", "gallery_cropped", "original"

    Usage:
        {% load photo_tags %}
        {{ photo|photo_url:"gallery_cropped" }}
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
        {{ photo.image_gallery_cropped|safe_image_url }}
    """
    try:
        if image_field and image_field.name:
            return image_field.url
    except (ValueError, AttributeError):
        # S3 storage may raise errors for missing/invalid files
        pass
    return ""
