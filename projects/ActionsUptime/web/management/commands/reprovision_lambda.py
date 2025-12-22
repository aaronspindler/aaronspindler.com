from django.core.management.base import BaseCommand

from utils.models import LambdaRegion
from web.lambda_handler import create_or_update_lambda_function


class Command(BaseCommand):

    def handle(self, *args, **options):
        for region in LambdaRegion.objects.all():
            print(region.code)
            create_or_update_lambda_function(region.code)