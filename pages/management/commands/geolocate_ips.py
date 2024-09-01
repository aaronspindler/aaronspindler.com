from django.core.management.base import BaseCommand
from pages.models import PageVisit
import requests
import json

class Command(BaseCommand):
    help = 'Geolocate IP addresses for PageVisit records'

    def handle(self, *args, **options):
        ips = list(PageVisit.objects.filter(geo_data__isnull=True).values_list('ip_address', flat=True).distinct())
        ips.remove('127.0.0.1')
        ips.remove('10.0.2.2')
        ips.remove('10.0.1.5')
        
        print(f"Geolocating {len(ips)} IP addresses")
        print(ips)
        
        for i in range(0, len(ips), 100):
            chunk = ips[i:i+100]
            formatted_chunk = json.dumps(chunk)
            try:
                response = requests.post('http://ip-api.com/batch', data=formatted_chunk)
                data = response.json()
                for response in data:
                    if response['status'] == 'success':
                        ip = response.pop('query')
                        response.pop('status')
                        PageVisit.objects.filter(ip_address=ip).update(geo_data=response)
            except Exception as e:
                print(f"Error geolocating chunk {i//100 + 1}: {e}")