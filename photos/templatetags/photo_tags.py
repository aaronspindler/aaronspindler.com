from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def responsive_image(photo, css_class="", alt_text="", loading="lazy", fetchpriority=""):
    if not photo or not photo.image:
        return ""

    if not alt_text:
        alt_text = photo.title

    alt_text = escape(alt_text)
    css_class = escape(css_class)

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

    fetchpriority_attr = f'fetchpriority="{escape(fetchpriority)}"' if fetchpriority else ""

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
    if not photo or not photo.image:
        return ""

    if not alt_text:
        alt_text = photo.title

    alt_text = escape(alt_text)
    css_class = escape(css_class)

    picture_html = "<picture>"

    if photo.image_thumbnail and photo.image_thumbnail.name:
        try:
            picture_html += f"""
        <source srcset="{escape(photo.image_thumbnail.url)}">
        """
        except (ValueError, AttributeError):
            pass

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
    if not photo:
        return ""

    return photo.get_image_url(size) or ""


@register.filter
def safe_image_url(image_field):
    try:
        if image_field and image_field.name:
            return image_field.url
    except (ValueError, AttributeError):
        # S3 storage may raise errors for missing/invalid files
        pass
    return ""
