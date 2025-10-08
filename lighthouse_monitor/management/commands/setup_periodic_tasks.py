from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, CrontabSchedule
import json


class Command(BaseCommand):
    """Setup periodic tasks for Lighthouse monitoring."""
    help = 'Setup periodic Lighthouse audit task for Celery Beat'

    def handle(self, *args, **options):
        # Setup daily Lighthouse audit at 2 AM
        schedule_daily_2am, created = CrontabSchedule.objects.get_or_create(
            minute='0',
            hour='2',
            day_of_week='*',
            day_of_month='*',
            month_of_year='*',
        )
        
        # Create or update the Lighthouse audit task
        task, created = PeriodicTask.objects.update_or_create(
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
                    f'✓ Successfully created periodic task: {task.name}'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ Successfully updated periodic task: {task.name}'
                )
            )
        
        self.stdout.write(
            self.style.SUCCESS(
                '\n✓ Lighthouse monitoring periodic task has been configured!'
            )
        )
        self.stdout.write(
            self.style.WARNING(
                '\nNote: Make sure Celery Beat is running for the task to execute:'
            )
        )
        self.stdout.write('  celery -A config beat -l info')

