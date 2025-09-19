from django import forms
from utils.common_list_choices import get_interval_choices, get_region_choices
from web.models import Endpoint
from utils.models import HTTPStatusCode

class EndpointForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        subscription_metadata = self.request.user.get_subscription_metadata()
        self.fields['interval'].choices = get_interval_choices(subscription_metadata.get('monitor_interval', '5M'))
        self.fields['enabled_regions'].choices = get_region_choices(subscription_metadata.get('endpoint_regions', []))
        self.fields['up_status_codes'].initial = HTTPStatusCode.objects.filter(code=200) 
        for field_name, field in self.fields.items():
            if field.widget.__class__.__name__ != 'CheckboxInput':
                field.widget.attrs.update({'class': 'form-control'})
            else:
                field.widget.attrs.update({'class': 'form-check-input'})
        
        # Make the up_status_codes field a little bit longer
        self.fields['up_status_codes'].widget.attrs.update({'size': '10'})
        self.fields['enabled_regions'].widget.attrs.update({'size': '10'})
        
    class Meta:
        model = Endpoint
        fields = [
            'url', 
            'http_method', 
            'up_status_codes', 
            'interval',
            'check_ssl', 
            'check_domain_expiration',
            'enabled_regions',
            'auth_type', 
            'auth_username', 
            'auth_password', 
            'request_body', 
            'send_body_as_json', 
            'request_headers',
            'request_timeout_seconds',
            'follow_redirects'
        ]
        labels = {
            'url': 'Endpoint URL',
            'http_method': 'HTTP Method',
            'up_status_codes': 'Up Status Codes',
            'interval': 'Check Interval',
            'check_ssl': 'Check SSL',
            'check_domain_expiration': 'Check Domain Expiration',
            'enabled_regions': 'Regions',
            'auth_type': 'Authentication Type',
            'auth_username': 'Authentication Username',
            'auth_password': 'Authentication Password',
            'request_body': 'Request Body',
            'send_body_as_json': 'Send Body as JSON',
            'request_headers': 'Request Headers',
            'request_timeout_seconds': 'Request Timeout',
            'follow_redirects': 'Follow Redirects'
        }
        help_texts = {
            'url': 'Enter the URL of the endpoint you want to monitor.',
            'http_method': 'Select the HTTP method to use for the request.',
            'up_status_codes': 'Select the status codes that indicate the endpoint is up.',
            'interval': 'Select how often the endpoint should be checked.',
            'check_ssl': 'Enable to check the SSL certificate of the endpoint.',
            'check_domain_expiration': 'Enable to check the domain expiration of the endpoint.',
            'enabled_regions': 'Select the regions where the endpoint should be checked.',
            'auth_type': 'Select the authentication type for the request.',
            'auth_username': 'Enter the username for authentication, if required.',
            'auth_password': 'Enter the password for authentication, if required.',
            'request_body': 'Enter the body of the request, if applicable.',
            'send_body_as_json': 'Enable to send the request body as JSON.',
            'request_headers': 'Enter the headers for the request in JSON format.',
            'request_timeout_seconds': 'Enter the maximum time (in seconds) to wait for a response.',
            'follow_redirects': 'Enable to follow HTTP redirects.'
        }
        widgets = {
            'url': forms.TextInput(attrs={'placeholder': 'https://google.com', 'class': 'form-control'}),
            'request_headers': forms.Textarea(attrs={
                'placeholder': '{\n  "Content-Type": "application/json",\n  "Authorization": "Bearer token"\n}', 'class': 'form-control'
            }),
            'request_timeout_seconds': forms.NumberInput(attrs={'min': 1, 'max': 300}),
        }

    def clean(self):
        cleaned_data = super().clean()
        up_status_codes = cleaned_data.get('up_status_codes')
        if not up_status_codes:
            cleaned_data['up_status_codes'] = [HTTPStatusCode.objects.get(code=200)]
        return cleaned_data