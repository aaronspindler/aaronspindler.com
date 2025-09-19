LAMBDA_LAYER_NAME = 'actionsuptime-web-endpoint-environment'
LAMBDA_FUNCTION_NAME = 'check_endpoint_status'
PYTHON_VERSION = 'python3.12'
TIMEOUT = 240

import json
import boto3
import io
import zipfile
from django.conf import settings

from web.models import Endpoint
    
def create_client(region = 'us-east-1'):
    client = boto3.client(
        'lambda',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=region
    )
    return client

def invoke_lambda(endpoint_id, request_key, region='us-east-1'):
    client = create_client(region)
    endpoint = Endpoint.objects.get(id=endpoint_id)
    data = endpoint.get_data_for_lambda()
    data['request_key'] = request_key
    client.invoke(
        FunctionName=LAMBDA_FUNCTION_NAME,
        InvocationType='Event',
        Payload=json.dumps(data)
    )
    

def create_or_update_lambda_function(region='us-east-1'):
    client = create_client(region)
    
    # Prepare Lambda function code
    with open('web/lambda_function.py', 'rb') as lambda_file:
        lambda_function_content = lambda_file.read()
    
    function_zip_buffer = io.BytesIO()
    with zipfile.ZipFile(function_zip_buffer, 'w', zipfile.ZIP_DEFLATED) as function_zip_file:
        function_zip_file.writestr('lambda_function.py', lambda_function_content)
    
    function_zip_buffer.seek(0)
    function_zip_content = function_zip_buffer.getvalue()

    # Prepare Lambda layer
    with open('web/python.zip', 'rb') as layer_zip_file:
        layer_zip_content = layer_zip_file.read()
    
    try:
        # Create or update Lambda layer
        layer_response = client.publish_layer_version(
            LayerName=LAMBDA_LAYER_NAME,
            Description='Python dependencies for ActionsUptime web endpoint checks',
            Content={
                'ZipFile': layer_zip_content
            },
            CompatibleRuntimes=[PYTHON_VERSION]
        )
        layer_version_arn = layer_response['LayerVersionArn']

        try:
            # Check if the Lambda function exists
            client.get_function(FunctionName=LAMBDA_FUNCTION_NAME)
            
            # Update existing Lambda function
            update_response = client.update_function_code(
                FunctionName=LAMBDA_FUNCTION_NAME,
                ZipFile=function_zip_content,
                Publish=True
            )
            new_version = update_response['Version']
            
            # Wait for the function update to complete
            waiter = client.get_waiter('function_updated')
            waiter.wait(FunctionName=LAMBDA_FUNCTION_NAME)
            
            # Update function configuration
            client.update_function_configuration(
                FunctionName=LAMBDA_FUNCTION_NAME,
                Layers=[layer_version_arn],
                Timeout=TIMEOUT,
            )
            
            print(f"Lambda function {LAMBDA_FUNCTION_NAME} updated successfully to version {new_version}.")
        except client.exceptions.ResourceNotFoundException:
            # If function doesn't exist, create it
            create_response = client.create_function(
                FunctionName=LAMBDA_FUNCTION_NAME,
                Role='arn:aws:iam::702821028163:role/ActionsUptime-Lambda-Role',
                Handler='lambda_function.check_endpoint_function',
                Runtime=PYTHON_VERSION,
                Code={'ZipFile': function_zip_content},
                Layers=[layer_version_arn],
                Timeout=TIMEOUT,
                Publish=True
            )
            new_version = create_response['Version']
            
            # Wait for the function creation to complete
            waiter = client.get_waiter('function_active')
            waiter.wait(FunctionName=LAMBDA_FUNCTION_NAME)
            
            print(f"Lambda function {LAMBDA_FUNCTION_NAME} created successfully with version {new_version}.")
    except Exception as e:
        print(f"Error creating/updating Lambda function or layer: {str(e)}")
        raise  # Re-raise the exception to ensure the error is not silently ignored
    
def delete_lambda_function(region = 'us-east-1'):
    client = create_client(region)
    try:
        client.delete_function(FunctionName=LAMBDA_FUNCTION_NAME)
    except Exception as e:
        print(e)
    try:
        layer_versions = client.list_layer_versions(LayerName=LAMBDA_LAYER_NAME)
        for version in layer_versions['LayerVersions']:
            client.delete_layer_version(
                LayerName=LAMBDA_LAYER_NAME,
                VersionNumber=version['Version']
                )
    except Exception as e:
        print(e)