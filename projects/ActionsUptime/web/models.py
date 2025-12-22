import uuid
from django.conf import settings
from django.core.cache import cache
from django.db import models
from django.db.models import Count, Q, Avg, Sum
from django.db.models.functions import TruncHour, TruncDay, TruncMonth
from django.urls import reverse

from utils.common_list_choices import INTERVAL_CHOICES
from utils.models import Notification


class Endpoint(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    owner = models.ForeignKey('accounts.CustomUser', on_delete=models.CASCADE)
    
    url = models.URLField(max_length=2000)
    
    notify_emails = models.ManyToManyField('utils.NotificationEmail', blank=True)
    notify_phone_numbers = models.ManyToManyField('utils.NotificationPhoneNumber', blank=True)
    
    private_id = models.UUIDField(default=uuid.uuid4)
    
    interval = models.CharField(max_length=10, choices=INTERVAL_CHOICES, default='5M')
    
    enabled_regions = models.ManyToManyField('utils.LambdaRegion', blank=True)
    
    check_ssl = models.BooleanField(default=True)
    check_domain_expiration = models.BooleanField(default=True)
    
    follow_redirects = models.BooleanField(default=True)
    
    request_timeout_seconds = models.IntegerField(default=30)
    
    HTTP_METHOD_CHOICES = [
        ('HEAD', 'HEAD'),
        ('GET', 'GET'),
        ('POST', 'POST'),
        ('PUT', 'PUT'),
        ('PATCH', 'PATCH'),
        ('DELETE', 'DELETE'),
        ('OPTIONS', 'OPTIONS'),
    ]
    http_method = models.CharField(max_length=10, choices=HTTP_METHOD_CHOICES, default='GET')
    
    up_status_codes = models.ManyToManyField('utils.HTTPStatusCode', blank=True)
    
    AUTH_TYPE_CHOICES = [
        ('none', 'None'),
        ('basic', 'Basic'),
        ('digest', 'Digest'),
    ]
    auth_type = models.CharField(max_length=10, choices=AUTH_TYPE_CHOICES, default='none')
    
    auth_username = models.CharField(max_length=255, blank=True, null=True)
    auth_password = models.CharField(max_length=255, blank=True, null=True)
    
    request_body = models.TextField(blank=True, null=True)
    send_body_as_json = models.BooleanField(default=False)
    
    request_headers = models.TextField(blank=True, null=True)
    
    def send_notification(self, current_status):
        notification_context = {
            "url": self.url,
            "created_at": current_status.created_at.strftime("%B %d, %Y, %I:%M %p"),
            "status": current_status.status.title(),
            "response_code": current_status.status_code,
            "duration_ms": current_status.duration_ms,
            "ssl_valid": current_status.ssl_valid,
            "ssl_expiration": current_status.ssl_expiration.strftime("%B %d, %Y, %I:%M %p") if current_status.ssl_expiration else None,
            "domain_expiration": current_status.domain_expiration.strftime("%B %d, %Y, %I:%M %p") if current_status.domain_expiration else None,
            "region": current_status.region.name if current_status.region else "ActionsUptime Server",
            "details_url": self.get_private_status_url(),
        }
        for phone_number in self.notify_phone_numbers.all():
            phone_number.create_endpoint_status_notification_message(notification_context)            
        for email in self.notify_emails.all():
            email.create_endpoint_status_notification_message(notification_context)
        notification_type = "failure" if current_status.status == "failure" else "success"
        if notification_type == "failure":
            notification_message = f"{self.url} is down"
        else:
            notification_message = f"{self.url} is up"
        Notification.objects.create(
            endpoint=self,
            endpoint_status=current_status,
            type=notification_type,
            message=notification_message
        )
    def get_private_status_url(self):
        # TODO make an actual private details URL
        return f"{settings.BASE_URL}{reverse('home')}"
    
    def get_percentage_success(self):
        statuses = self.endpointstatus_set.all()
        total_count = statuses.count()
        if total_count == 0:
            return 0
        success_count = statuses.filter(status='success').count()
        return round((success_count / total_count) * 100, 2)
    
    def get_average_latency(self):
        statuses = self.endpointstatus_set.filter(region__in=self.enabled_regions.all())
        if statuses.count() == 0:
            return 0
        total_duration = statuses.aggregate(total_duration=Sum('duration_ms'))['total_duration'] or 0
        return round(total_duration / statuses.count(), 2)
    
    def get_most_recent_status(self):
        return self.endpointstatus_set.order_by('-check_start_time').first()
    
    def get_status_timeline(self, timeline_type='daily'):
        cache_key = f'endpoint_status_timeline_{self.id}_{timeline_type}'
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

            stats = self.endpointstatus_set.filter(
                Q(region__in=self.enabled_regions.all()) | Q(region=None)
            ).annotate(
                period=trunc_func('check_start_time')
            ).values('period').annotate(
                total=Count('id'),
                success_count=Count('id', filter=Q(status='success')),
            ).order_by('period')

            timeline = [
                {
                    'date': stat['period'].isoformat(),
                    'success_percentage': round((stat['success_count'] / stat['total']) * 100, 2) if stat['total'] > 0 else 0,
                    'failure_percentage': round(((stat['total'] - stat['success_count']) / stat['total']) * 100, 2) if stat['total'] > 0 else 0,
                }
                for stat in stats
            ]

            cache.set(cache_key, timeline, 3)  # Cache for 5 minutes
        else:
            timeline = cached_timeline

        return timeline
    
    def get_latency_timeline_by_region(self, timeline_type='daily'):
        cache_key = f'endpoint_latency_timeline_{self.id}_{timeline_type}'
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

            stats = self.endpointstatus_set.filter(
                Q(region__in=self.enabled_regions.all()) | Q(region=None)
            ).annotate(
                period=trunc_func('check_start_time')
            ).values('period', 'region__name').annotate(
                avg_duration=Avg('duration_ms')
            ).order_by('period', 'region__name')

            timeline = {}
            
            for stat in stats:
                date = stat['period'].isoformat()
                region_name = stat['region__name'] if stat['region__name'] else 'ActionsUptime Server'
                avg_duration = round(stat['avg_duration'], 2)
                
                if date not in timeline:
                    timeline[date] = {}
                
                timeline[date][region_name] = avg_duration

            cache.set(cache_key, timeline, 5)  # Cache for 5 minutes
        else:
            timeline = cached_timeline
        return timeline
        
    
    def __str__(self):
        return f"{self.url} - {self.interval} - {self.http_method}"
    
    def get_data_for_lambda(self):
        return {
            'endpoint_id': self.id,
            'url': self.url,
            'check_ssl': self.check_ssl,
            'check_domain_expiration': self.check_domain_expiration,
            'follow_redirects': self.follow_redirects,
            'request_timeout_seconds': self.request_timeout_seconds,
            'http_method': self.http_method,
            'up_status_codes': list(self.up_status_codes.values_list('code', flat=True)),
            'auth_type': self.auth_type,
            'auth_username': self.auth_username,
            'auth_password': self.auth_password,
            'request_body': self.request_body,
            'send_body_as_json': self.send_body_as_json,
            'request_headers': self.request_headers,
        }
    

class EndpointStatusCheckRequest(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    endpoint = models.ForeignKey(Endpoint, on_delete=models.CASCADE)
    region = models.ForeignKey('utils.LambdaRegion', on_delete=models.CASCADE, null=True)
    
    key = models.UUIDField(default=uuid.uuid4)
    
    received_response = models.BooleanField(default=False)
    response = models.TextField(blank=True, null=True)


class EndpointStatus(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    endpoint = models.ForeignKey(Endpoint, on_delete=models.CASCADE)
    
    region = models.ForeignKey('utils.LambdaRegion', on_delete=models.CASCADE, null=True)
    status_code = models.IntegerField()
    
    STATUS_CHOICES = [
        ('success', 'Success'),
        ('failure', 'Failure'),
    ]
    status = models.CharField(max_length=7, choices=STATUS_CHOICES)
    error = models.TextField(blank=True, null=True)
    
    ssl_valid = models.BooleanField(default=False, null=True)
    ssl_expiration = models.DateTimeField(blank=True, null=True)
    
    domain_expiration = models.DateTimeField(blank=True, null=True)
    
    check_start_time = models.DateTimeField()
    check_end_time = models.DateTimeField()
    
    duration_ms = models.FloatField()

    def __str__(self):
        return f"{self.endpoint.url} - {self.status_code} - {self.status} - {self.duration_ms:.2f} ms"
    
    def get_iso_datetime(self):
        return self.check_start_time.isoformat()
    
    class Meta:
        verbose_name = "Endpoint Status"
        verbose_name_plural = "Endpoint Statuses"
        
        indexes = [
            models.Index(fields=['endpoint']),
            models.Index(fields=['endpoint', 'check_start_time']),
            models.Index(fields=['endpoint', 'region']),
            models.Index(fields=['endpoint', 'region', 'check_start_time']),
        ]