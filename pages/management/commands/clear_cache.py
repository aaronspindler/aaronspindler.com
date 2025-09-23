"""
Django management command to clear all cache keys.

Usage:
    python manage.py clear_cache
    python manage.py clear_cache --pattern="blog*"
    python manage.py clear_cache --yes
"""

from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Clear all cache keys from Redis'

    def handle(self, *args, **options):
        cache.clear()
