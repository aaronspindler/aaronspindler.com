from django.core.management.base import BaseCommand

from web.models import Endpoint
from web.tasks import check_endpoint_status_local


class Command(BaseCommand):

    def handle(self, *args, **options):
       endpoint = Endpoint.objects.get(pk=11)
       check_endpoint_status_local(endpoint.id)