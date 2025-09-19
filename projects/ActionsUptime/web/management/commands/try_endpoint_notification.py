from django.core.management.base import BaseCommand
from web.models import Endpoint

class Command(BaseCommand):
    def handle(self, *args, **options):
        endpoint = Endpoint.objects.get(id=2)
       
        current_status = endpoint.get_most_recent_status()
        
        endpoint.send_notification(current_status)