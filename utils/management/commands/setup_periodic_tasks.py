import json

from django.core.management.base import BaseCommand
from django_celery_beat.models import CrontabSchedule, PeriodicTask

# Define all periodic tasks here - just add to the list!
# Format: (name, task_path, cron_schedule, description)
PERIODIC_TASKS = [
    # IP geolocation
    (
        "Geolocate missing IP addresses",
        "utils.tasks.geolocate_missing_ips",
        {"minute": "0", "hour": "0,12"},
        "Geolocates IP addresses without geo data twice daily at midnight and noon",
    ),
    # Daily tasks
    (
        "Run daily Lighthouse audit",
        "utils.tasks.run_lighthouse_audit",
        {"minute": "0", "hour": "2"},
        "Runs a Lighthouse performance audit of the production site every day at 2 AM",
    ),
    (
        "Rebuild and cache sitemap daily",
        "pages.tasks.rebuild_and_cache_sitemap",
        {"minute": "0", "hour": "3"},
        "Rebuilds and caches the sitemap every day at 3 AM",
    ),
    (
        "Generate knowledge graph screenshot",
        "blog.tasks.generate_knowledge_graph_screenshot",
        {"minute": "0", "hour": "4"},
        "Generates a fresh knowledge graph screenshot every day at 4 AM",
    ),
    # Recurring tasks
    (
        "Rebuild knowledge graph cache",
        "blog.tasks.rebuild_knowledge_graph",
        {"minute": "0", "hour": "*/6"},
        "Rebuilds the knowledge graph cache every 6 hours",
    ),
]


class Command(BaseCommand):
    help = "Setup periodic tasks for Celery Beat"

    def handle(self, *args, **options):
        # Track configured task names
        configured_task_names = set()

        for name, task_path, cron_config, description in PERIODIC_TASKS:
            configured_task_names.add(name)

            # Create cron schedule with defaults for unspecified fields
            schedule, _ = CrontabSchedule.objects.get_or_create(
                minute=cron_config.get("minute", "*"),
                hour=cron_config.get("hour", "*"),
                day_of_week=cron_config.get("day_of_week", "*"),
                day_of_month=cron_config.get("day_of_month", "*"),
                month_of_year=cron_config.get("month_of_year", "*"),
            )

            # Create or update the periodic task
            task, created = PeriodicTask.objects.update_or_create(
                name=name,
                defaults={
                    "task": task_path,
                    "crontab": schedule,
                    "kwargs": json.dumps({}),
                    "enabled": True,
                    "description": description,
                },
            )

            action = "Created" if created else "Updated"
            self.stdout.write(self.style.SUCCESS(f"{action}: {task.name}"))

        # Remove tasks that are no longer in the configuration
        orphaned_tasks = PeriodicTask.objects.exclude(name__in=configured_task_names)
        if orphaned_tasks.exists():
            self.stdout.write(self.style.WARNING(f"\nRemoving {orphaned_tasks.count()} orphaned task(s):"))
            for task in orphaned_tasks:
                self.stdout.write(self.style.WARNING(f"  - {task.name}"))
                task.delete()

        self.stdout.write(self.style.SUCCESS(f"\n✓ Configured {len(PERIODIC_TASKS)} periodic tasks successfully!"))
