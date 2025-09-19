from django.core.management.base import BaseCommand
from actions.models import Action

class Command(BaseCommand):
    def handle(self, *args, **options):
        action = Action.objects.get(id=3)
       
        current_status = action.most_recent_status()
        
        action.send_notification(current_status)