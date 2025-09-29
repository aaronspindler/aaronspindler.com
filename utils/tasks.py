from celery import shared_task
from django.apps import apps
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
import boto3

def get_notification_config():
    NotificationConfig = apps.get_model('utils', 'NotificationConfig')
    return NotificationConfig.objects.first()

@shared_task
def send_email(email_pk):
    notification_config = get_notification_config()
    if not notification_config.emails_enabled:
        return False
    
    Email = apps.get_model('utils', 'Email')
    email = Email.objects.get(pk=email_pk)
    if email.sent:
        return False

    parameters = email.get_parameters()
    # check if there is an unsubscribe code associated with this email address
    text_body = render_to_string("emails/{}.txt".format(email.template), parameters)
    html_body = render_to_string("emails/{}.html".format(email.template), parameters)

    emails = [email.recipient]

    send_mail(
        email.subject,
        text_body,
        settings.DEFAULT_FROM_EMAIL,
        emails,
        html_message=html_body,
        fail_silently=True,
    )

    email.text_body = text_body
    email.html_body = html_body
    email.sent = timezone.now()
    email.save()
    
@shared_task
def send_text_message(text_message_pk):
    notification_config = get_notification_config()
    if not notification_config.text_messages_enabled:
        return False
    
    TextMessage = apps.get_model('utils', 'TextMessage')
    text_message = TextMessage.objects.get(pk=text_message_pk)
    if text_message.sent:
        return False

    sns = boto3.client(
        "sns",  
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name="us-east-1",
    )
    
    parameters = text_message.get_parameters()
    message = render_to_string("sms/{}.txt".format(text_message.template), parameters)
    
    sns.publish(PhoneNumber=text_message.recipient, Message=message)

    text_message.message = message
    text_message.sent = timezone.now()
    text_message.save()