import re
import urllib.request
import uuid
from urllib.parse import urlparse

from django.conf import settings
from django.core.cache import cache
from django.db import models
from django.db.models import Count, Q
from django.db.models.functions import TruncHour, TruncDay, TruncMonth
from django.urls import reverse

from utils.common_list_choices import INTERVAL_CHOICES
from utils.models import Notification

class Action(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    is_private = models.BooleanField(default=False)
    
    owner = models.ForeignKey('accounts.CustomUser', on_delete=models.CASCADE)
    url = models.TextField()
    branch = models.TextField(default="main")
    
    notify_emails = models.ManyToManyField('utils.NotificationEmail', blank=True)
    notify_phone_numbers = models.ManyToManyField('utils.NotificationPhoneNumber', blank=True)
    
    private_id = models.UUIDField(default=uuid.uuid4)
    
    interval = models.CharField(max_length=10, choices=INTERVAL_CHOICES, default='5M')        
    
    def send_notification(self, current_status):
        # this is called when the last status is different from the previous status
        notification_context = {
            "created_at": current_status.created_at.strftime("%B %d, %Y, %I:%M %p"),
            "action_branch": self.branch,
            "action_repo": self.repo_name,
            "action_name": self.pretty_name,
            "status": current_status.status.title(),
            "previous_status": current_status.previous_status.status.title() if current_status.previous_status else None,
            "details_url": self.get_private_status_url(),
        }
        for phone_number in self.notify_phone_numbers.all():
            phone_number.create_action_status_notification_message(notification_context)            
        for email in self.notify_emails.all():
            email.create_action_status_notification_message(notification_context)
        notification_type = "failure" if current_status.status == "failure" else "success"
        if notification_type == "failure":
            notification_message = f"{self.pretty_name} in {self.repo_name} ({self.branch}) has started failing"
        else:
            notification_message = f"{self.pretty_name} in {self.repo_name} ({self.branch}) has recovered"
        Notification.objects.create(
            action=self,
            action_status=current_status,
            type=notification_type,
            message=notification_message
        )
    
    def badge_status(self):
        url = f"{self.url}/badge.svg{'?branch=' + self.branch if self.branch != 'main' else ''}"
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(request) as response:
            svg = response.read().decode().lower()
        title_match = re.search(r'<title>(.*?)</title>', svg)
        if title_match:
            return "success" if 'passing' in title_match.group(1).lower() else "failure"
        return "failure"
    
    def get_checker_to_use(self, checker=None):
        if checker:
            return checker
        if self.is_private:
            return 'api'
        return 'badge'
        
    def get_percentage_success(self, checker=None):
        checker = self.get_checker_to_use(checker)
        statuses = self.actionstatus_set.filter(checker=checker)
        total_count = statuses.count()
        if total_count == 0:
            return 0
        success_count = statuses.filter(status='success').count()
        return round((success_count / total_count) * 100, 2)
    
    def get_public_status_url(self):
        return f"{settings.BASE_URL}{reverse('action_status', args=[self.private_id])}"
    
    def get_private_status_url(self):
        # TODO make an actual private details URL
        return f"{settings.BASE_URL}{reverse('home')}"
        
    def most_recent_status(self, checker=None):
        checker = self.get_checker_to_use(checker)
        return self.actionstatus_set.filter(checker=checker).order_by('-created_at').first()
    
    def get_action_status_timeline(self, timeline_type='daily', checker=None):
        checker = self.get_checker_to_use(checker)
        cache_key = f'action_status_timeline_{self.id}_{checker}_{timeline_type}'
        cached_timeline = cache.get(cache_key)

        if cached_timeline is None:
            if timeline_type == 'hourly':
                trunc_func = TruncHour
            elif timeline_type == 'daily':
                trunc_func = TruncDay
            elif timeline_type == 'monthly':
                trunc_func = TruncMonth
            else:
                raise ValueError("Invalid timeline type")

            stats = self.actionstatus_set.filter(checker=checker).annotate(
                period=trunc_func('created_at')
            ).values('period').annotate(
                total=Count('id'),
                success_count=Count('id', filter=Q(status='success'))
            ).order_by('period')

            timeline = [
                {
                    'date': stat['period'].isoformat(),
                    'success_percentage': round((stat['success_count'] / stat['total']) * 100, 2) if stat['total'] > 0 else 0,
                    'failure_percentage': round(((stat['total'] - stat['success_count']) / stat['total']) * 100, 2) if stat['total'] > 0 else 0
                }
                for stat in stats
            ]

            cache.set(cache_key, timeline, 10)  # Cache for 10 seconds
        else:
            timeline = cached_timeline

        return timeline
    
    @property
    def pretty_name(self):
        return self.action_name.replace('.yml', '').replace('.yaml', '').replace('-', ' ').replace('_', ' ').title()
    
    @property
    def action_name(self):
        return urlparse(self.url).path.split('/')[-1]
    
    @property
    def repo_name(self):
        path_parts = urlparse(self.url).path.split('/')
        return f"{path_parts[1]}/{path_parts[2]}"
    
    def __str__(self):
        return f"{self.repo_name} - {self.pretty_name} ({self.branch})"

    class Meta:
        unique_together = [('owner', 'url', 'branch')]
        

class ActionStatus(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    action = models.ForeignKey(Action, on_delete=models.CASCADE)
    
    error = models.TextField(blank=True, null=True)
    CHECKER_CHOICES = [
        ('badge', 'Badge'),
        ('api', 'API'),
    ]
    checker = models.CharField(max_length=10, choices=CHECKER_CHOICES, default='badge')
    
    previous_status = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)
    
    STATUS_CHOICES = [
        ('success', 'Success'),
        ('failure', 'Failure'),
        ('error', 'Error'),
    ]
    status = models.CharField(max_length=7, choices=STATUS_CHOICES)
    
    def get_iso_datetime(self):
        return self.created_at.isoformat()

    class Meta:
        indexes = [
            models.Index(fields=['action']),
            models.Index(fields=['action', 'created_at']),
        ]
        verbose_name_plural = "Statuses"