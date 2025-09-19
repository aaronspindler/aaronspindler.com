import json
from django.core.management.base import BaseCommand

from web.models import EndpointStatus, EndpointStatusCheckRequest
class Command(BaseCommand):

    def handle(self, *args, **options):
        import concurrent.futures
        from django.db import transaction

        def process_request(request):
            try:
                original_response = request.response
                response = original_response[2:-1].replace("\\n", "").replace("\\", "")
                json_response = json.loads(response)
                return EndpointStatus(
                    endpoint=request.endpoint,
                    region=request.region,
                    **json_response
                ), request.pk
            except Exception as e:
                print(f"Error processing request {request.pk}: {e}")
                print(f"Response: {request.response}")
                return None, None

        completed_status_requests = EndpointStatusCheckRequest.objects.filter(received_response=True, response__isnull=False)
        to_create = []
        to_delete = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
            future_to_request = {executor.submit(process_request, request): request for request in completed_status_requests}
            for i, future in enumerate(concurrent.futures.as_completed(future_to_request)):
                status, pk = future.result()
                if status and pk:
                    to_create.append(status)
                    to_delete.append(pk)
                print(f"Processed {i+1}/{len(completed_status_requests)}")

        with transaction.atomic():
            EndpointStatus.objects.bulk_create(to_create)
            EndpointStatusCheckRequest.objects.filter(pk__in=to_delete).delete()