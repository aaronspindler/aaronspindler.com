import datetime
from celery import shared_task
from web.lambda_function import check_endpoint_function
from web.models import Endpoint, EndpointStatus, EndpointStatusCheckRequest
from .lambda_handler import invoke_lambda


@shared_task
def check_endpoint_status_lambda(endpoint_id):
    endpoint = Endpoint.objects.get(id=endpoint_id)
    for region in endpoint.enabled_regions.filter(active=True):
        request = EndpointStatusCheckRequest.objects.create(endpoint=endpoint, region=region)
        invoke_lambda(endpoint_id, str(request.key), region.code)


@shared_task
def check_all_endpoints_status_interval(interval):
    endpoints = Endpoint.objects.filter(interval=interval)
    for endpoint in endpoints:
        check_endpoint_status_local.delay(endpoint.id)
        check_endpoint_status_lambda.delay(endpoint.id)


@shared_task
def check_endpoint_status_local(endpoint_id):
    endpoint = Endpoint.objects.get(id=endpoint_id)
    data = endpoint.get_data_for_lambda()
    result = check_endpoint_function(data)
    check_start_time = datetime.datetime.fromisoformat(result['check_start_time'])
    check_end_time = datetime.datetime.fromisoformat(result['check_end_time'])
    status_code = result['status_code']
    status = result['status']
    duration_ms = result['duration_ms']
    ssl_valid = result['ssl_valid']
    ssl_expiration = datetime.datetime.fromisoformat(result['ssl_expiration']) if result['ssl_expiration'] else None
    domain_expiration = datetime.datetime.fromisoformat(result['domain_expiration']) if result['domain_expiration'] else None
    error = result['error']
    
    previous_status = endpoint.get_most_recent_status()
    
    data_to_create = dict(
        endpoint=endpoint,
        status_code=status_code,
        status=status,
        check_start_time=check_start_time,
        check_end_time=check_end_time,
        duration_ms=duration_ms,
        ssl_valid=ssl_valid,
        ssl_expiration=ssl_expiration,
        domain_expiration=domain_expiration,
        error=error,
        region=None
    )
    current_status = EndpointStatus.objects.create(**data_to_create)
    if previous_status != None:
        if current_status.status != previous_status.status:
            endpoint.send_notification(current_status)