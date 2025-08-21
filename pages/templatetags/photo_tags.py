"""
Template tags for working with photos and responsive images.
"""
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def responsive_image(photo, css_class='', alt_text='', loading='lazy'):
    """
    Generate a responsive image tag with srcset for different screen sizes.
    
    Usage:
        {% load photo_tags %}
        {% responsive_image photo css_class="img-fluid" alt_text="My Photo" %}
    """
    if not photo or not photo.image:
        return ''
    
    # Use the title as alt text if not provided
    if not alt_text:
        alt_text = photo.title
    
    # Build the srcset attribute
    srcset_parts = []
    
    if photo.image_small:
        srcset_parts.append(f'{photo.image_small.url} 400w')
    
    if photo.image_medium:
        srcset_parts.append(f'{photo.image_medium.url} 800w')
    
    if photo.image_large:
        srcset_parts.append(f'{photo.image_large.url} 1920w')
    
    if photo.image:
        srcset_parts.append(f'{photo.image.url} {photo.width}w' if photo.width else photo.image.url)
    
    srcset = ', '.join(srcset_parts)
    
    # Default src (use medium as default, fallback to original)
    default_src = photo.image_medium.url if photo.image_medium else photo.image.url
    
    # Build the img tag
    img_tag = f'''
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
    '''
    
    return mark_safe(img_tag)


@register.simple_tag
def picture_element(photo, css_class='', alt_text='', loading='lazy'):
    """
    Generate a <picture> element with WebP support and responsive sources.
    
    Usage:
        {% load photo_tags %}
        {% picture_element photo css_class="img-fluid" %}
    """
    if not photo or not photo.image:
        return ''
    
    # Use the title as alt text if not provided
    if not alt_text:
        alt_text = photo.title
    
    # Build the picture element with source elements for different sizes
    picture_html = '<picture>'
    
    # Add source elements for different viewport widths
    if photo.image_large:
        picture_html += f'''
        <source media="(min-width: 1200px)"
                srcset="{photo.image_large.url}">
        '''
    
    if photo.image_medium:
        picture_html += f'''
        <source media="(min-width: 768px)"
                srcset="{photo.image_medium.url}">
        '''
    
    if photo.image_small:
        picture_html += f'''
        <source media="(min-width: 400px)"
                srcset="{photo.image_small.url}">
        '''
    
    # Fallback img element (use thumbnail for smallest screens)
    fallback_src = photo.image_thumbnail.url if photo.image_thumbnail else photo.image.url
    
    picture_html += f'''
    <img src="{fallback_src}"
         class="{css_class}"
         alt="{alt_text}"
         loading="{loading}">
    </picture>
    '''
    
    return mark_safe(picture_html)


@register.filter
def photo_url(photo, size='medium'):
    """
    Get the URL for a specific photo size.
    
    Usage:
        {% load photo_tags %}
        {{ photo|photo_url:"large" }}
        {{ photo|photo_url:"thumbnail" }}
    """
    if not photo:
        return ''
    
    return photo.get_image_url(size) or ''
