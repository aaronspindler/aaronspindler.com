import datetime
import json
import time
import requests
import socket
import ssl
import whois
from datetime import datetime, timezone
from urllib.parse import urlparse

URL = "https://actionsuptime.com"

def post_to_webhook(request_key, return_data):
    print(f"Posting to webhook: {request_key}")
    max_retries = 5
    retry_count = 0
    while retry_count < max_retries:
        response = requests.post(
            f"{URL}/web/webhook/{request_key}",
            data=json.dumps(return_data),
            headers={'Content-Type': 'application/json'}
        )
        if response.status_code == 200:
            break
        retry_count += 1
        if retry_count < max_retries:
            time.sleep(retry_count ** 3)
    if retry_count == max_retries:
        print(f"Failed to post to webhook after {max_retries} attempts")

def check_endpoint_function(endpoint_data=None, event=None, context=None):
    start_time = None
    end_time = None
    duration_ms = None
    
    status_code_valid = False
    status_code = 500
    error = ""
    
    ssl_valid = None
    ssl_expiration = None
    domain_expiration = None
    
    request_key = endpoint_data.get('request_key')
    
    if request_key:
        import sentry_sdk
        from sentry_sdk.integrations.aws_lambda import AwsLambdaIntegration

        sentry_sdk.init(
            dsn="https://0d50900b250856e0af4739ea27a13b1a@o555567.ingest.us.sentry.io/4508026538033152",
            integrations=[AwsLambdaIntegration(timeout_warning=True)],

            traces_sample_rate=1.0,
            profiles_sample_rate=1.0,
        )

    url = endpoint_data.get('url')
    check_ssl = endpoint_data.get('check_ssl', False)
    check_domain_expiration = endpoint_data.get('check_domain_expiration', False)
    follow_redirects = endpoint_data.get('follow_redirects', False)
    http_method = endpoint_data.get('http_method', 'GET')
    up_status_codes = endpoint_data.get('up_status_codes', [])
    request_timeout_seconds = endpoint_data.get('request_timeout_seconds', 30)
    auth_type = endpoint_data.get('auth_type', None)
    auth_username = endpoint_data.get('auth_username', None)
    auth_password = endpoint_data.get('auth_password', None)
    request_body = endpoint_data.get('request_body', None)
    send_body_as_json = endpoint_data.get('send_body_as_json', False)
    request_headers = endpoint_data.get('request_headers', {})
    if request_headers:
        try:
            request_headers = json.loads(request_headers)
        except json.JSONDecodeError:
            # If JSON parsing fails, assume it's a string-based format
            request_headers = dict(item.split(": ") for item in request_headers.split("\n") if item)
    
    try:
        # Prepare request
        session = requests.Session()
        request_kwargs = dict(
            method=http_method,
            url=url,
            headers=request_headers or {},
        )
        if request_body:
            if send_body_as_json:
                body = json.loads(request_body)
                request_kwargs['json'] = body
            else:
                body = request_body
                request_kwargs['data'] = body

        request = requests.Request(
            **request_kwargs
        )
        session.timeout = request_timeout_seconds
        
        # Add authentication if needed
        if auth_type == 'basic':
            session.auth = (auth_username, auth_password)
        elif auth_type == 'digest':
            from requests.auth import HTTPDigestAuth
            session.auth = HTTPDigestAuth(auth_username, auth_password)
        
        # Prepare and send request
        prepped = session.prepare_request(request)
        start_time = datetime.now(timezone.utc)
        try:
            response = session.send(
                prepped,
                allow_redirects=follow_redirects,
                verify=check_ssl,
                timeout=request_timeout_seconds
            )
            status_code = response.status_code
        except requests.exceptions.Timeout:
            status_code = 504  # Gateway Timeout
        except requests.exceptions.RequestException as e:
            error = str(e)
            status_code = getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
            if status_code is None:
                if isinstance(e, requests.exceptions.ConnectionError):
                    status_code = 503  # Service Unavailable
                elif isinstance(e, requests.exceptions.Timeout):
                    status_code = 504  # Gateway Timeout
                else:
                    status_code = 500  # Internal Server Error
        end_time = datetime.now(timezone.utc)
        duration_ms = round((end_time - start_time).total_seconds() * 1000, 2)
        
        # Check status code
        status_code_valid = status_code in up_status_codes
        
        if check_ssl:
            try:
                parsed_url = urlparse(url)
                ssl_context = ssl.create_default_context()
                with socket.create_connection((parsed_url.hostname, parsed_url.port or 443)) as sock:
                    with ssl_context.wrap_socket(sock, server_hostname=parsed_url.hostname) as secure_sock:
                        cert = secure_sock.getpeercert()
                        ssl_expiration = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z').replace(tzinfo=timezone.utc)
                        ssl_valid = ssl_expiration > datetime.now(timezone.utc)
            except Exception as e:
                ssl_valid = False
                error += "\n" + "================================================" + "\n" + str(e)
    
        # Check domain expiration (simplified, might need additional library)
        if check_domain_expiration:
            try:
                domain = whois.whois(urlparse(url).netloc)
                if isinstance(domain.expiration_date, list):
                    domain_expiration = domain.expiration_date[0].replace(tzinfo=timezone.utc)
                else:
                    domain_expiration = domain.expiration_date.replace(tzinfo=timezone.utc)
            except Exception as e:
                domain_expiration = None
                error += "\n" + "================================================" + "\n" + str(e)
    except Exception as e:
        error += "\n" + "================================================" + "\n" + str(e)
    
    # Determine overall status
    ssl_component = ssl_valid is None or ssl_valid
    domain_component = domain_expiration is None or domain_expiration > datetime.now(timezone.utc)
    is_up = status_code_valid and ssl_component and domain_component
    
    print('status_code_valid', status_code_valid)
    print('ssl_component', ssl_component)
    print('domain_component', domain_component)
    print('is_up', is_up)
    
    # Determine status
    status = 'success' if is_up else 'failure'
    
    # Make a return object
    return_data = dict(
        status_code=status_code,
        status=status,
        check_start_time=start_time.isoformat() if start_time else None,
        check_end_time=end_time.isoformat() if end_time else None,
        duration_ms=duration_ms,
        ssl_valid=ssl_valid,
        ssl_expiration=ssl_expiration.isoformat() if ssl_expiration else None,
        domain_expiration=domain_expiration.isoformat() if domain_expiration else None,
        error=error
    )
    
    if request_key:
        post_to_webhook(request_key, return_data)
    return return_data