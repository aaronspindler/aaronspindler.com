from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, CrontabSchedule
import json


class Command(BaseCommand):
    help = 'Setup periodic tasks for Celery Beat'

    def handle(self, *args, **options):
        # Setup daily sitemap rebuild at 3 AM
        schedule_daily_3am, created = CrontabSchedule.objects.get_or_create(
            minute='0',
            hour='3',
            day_of_week='*',
            day_of_month='*',
            month_of_year='*',
        )
        
        # Create or update the sitemap rebuild task
        task, created = PeriodicTask.objects.update_or_create(
            name='Rebuild and cache sitemap daily',
            defaults={
                'task': 'pages.tasks.rebuild_and_cache_sitemap',
                'crontab': schedule_daily_3am,
                'kwargs': json.dumps({}),
                'enabled': True,
                'description': 'Rebuilds and caches the sitemap every day at 3 AM'
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created periodic task: {task.name}'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully updated periodic task: {task.name}'
                )
            )
        
        # Setup knowledge graph rebuild every 6 hours
        schedule_every_6_hours, created = CrontabSchedule.objects.get_or_create(
            minute='0',
            hour='*/6',
            day_of_week='*',
            day_of_month='*',
            month_of_year='*',
        )
        
        # Create or update the knowledge graph rebuild task
        kg_task, created = PeriodicTask.objects.update_or_create(
            name='Rebuild knowledge graph cache',
            defaults={
                'task': 'blog.tasks.rebuild_knowledge_graph',
                'crontab': schedule_every_6_hours,
                'kwargs': json.dumps({}),
                'enabled': True,
                'description': 'Rebuilds the knowledge graph cache every 6 hours'
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created periodic task: {kg_task.name}'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully updated periodic task: {kg_task.name}'
                )
            )
        
        # Setup knowledge graph screenshot generation daily at 4 AM
        schedule_daily_4am, created = CrontabSchedule.objects.get_or_create(
            minute='0',
            hour='4',
            day_of_week='*',
            day_of_month='*',
            month_of_year='*',
        )
        
        # Create or update the knowledge graph screenshot task
        kg_screenshot_task, created = PeriodicTask.objects.update_or_create(
            name='Generate knowledge graph screenshot',
            defaults={
                'task': 'blog.tasks.generate_knowledge_graph_screenshot',
                'crontab': schedule_daily_4am,
                'kwargs': json.dumps({}),
                'enabled': True,
                'description': 'Generates a fresh knowledge graph screenshot every day at 4 AM'
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created periodic task: {kg_screenshot_task.name}'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully updated periodic task: {kg_screenshot_task.name}'
                )
            )
        
        # Setup daily Lighthouse audit at 2 AM
        schedule_daily_2am, created = CrontabSchedule.objects.get_or_create(
            minute='0',
            hour='2',
            day_of_week='*',
            day_of_month='*',
            month_of_year='*',
        )
        
        # Create or update the Lighthouse audit task
        lighthouse_task, created = PeriodicTask.objects.update_or_create(
            name='Run daily Lighthouse audit',
            defaults={
                'task': 'lighthouse_monitor.tasks.run_lighthouse_audit',
                'crontab': schedule_daily_2am,
                'kwargs': json.dumps({}),
                'enabled': True,
                'description': 'Runs a Lighthouse performance audit of the production site every day at 2 AM'
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created periodic task: {lighthouse_task.name}'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully updated periodic task: {lighthouse_task.name}'
                )
            )
        
        self.stdout.write(
            self.style.SUCCESS(
                '\nAll periodic tasks have been configured successfully!'
            )
        )