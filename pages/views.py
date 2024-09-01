from django.template import TemplateDoesNotExist
from django.shortcuts import render

from pages.decorators import track_page_visit
from pages.utils import get_blog_from_template_name


@track_page_visit
def home(request):
    import os
    from django.conf import settings

    blog_posts = []
    blog_templates_path = os.path.join(settings.BASE_DIR, 'templates', 'blog')
    for template_name in os.listdir(blog_templates_path):
        if template_name.endswith('.html'):
            template_name = template_name.split('.')[0]
            blog_posts.append(get_blog_from_template_name(template_name))
    print(blog_posts)
    return render(request, "pages/home.html", {"blog_posts": blog_posts})


@track_page_visit
def render_blog_template(request, template_name):
    try:
        blog_data = get_blog_from_template_name(template_name)
        return render(request, "_blog_base.html", blog_data)
    except TemplateDoesNotExist:
        return render(request, "404.html")
