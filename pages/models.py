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