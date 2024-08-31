from django.db import models
from django.urls import reverse
from django.utils import timezone

class PageVisit(models.Model):
    created_at = models.DateTimeField(default=timezone.now)
    ip_address = models.GenericIPAddressField()
    page_name = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.page_name} visited from {self.ip_address} at {self.created_at}"

    class Meta:
        verbose_name = "Page Visit"
        verbose_name_plural = "Page Visits"

class BlogPost(models.Model):
    title = models.TextField()
    slug = models.SlugField(null=True, blank=True, unique=True, max_length=255)

    tags = models.ManyToManyField("Tag", blank=True)

    short_content = models.TextField(blank=True, null=True)
    content_html = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(auto_now=True)

    published = models.BooleanField(default=False)

    def get_absolute_url(self):
        return reverse("blog_post", args=[str(self.slug)])


class Tag(models.Model):
    name = models.CharField(max_length=75)

    def __str__(self):
        return self.name