"""
Django management command to clear all cache keys.

Usage:
    python manage.py clear_cache
    python manage.py clear_cache --pattern="blog*"
    python manage.py clear_cache --yes
"""

import logging

from django.core.cache import cache
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Clear all cache keys from Redis"

    def handle(self, *args, **options):
        cache.clear()
