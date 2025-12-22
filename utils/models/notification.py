import json
import secrets
import uuid

from django.db import models

from utils.tasks import send_email, send_text_message


class NotificationConfig(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    emails_enabled = models.BooleanField()
    text_messages_enabled = models.BooleanField()


class NotificationEmail(models.Model):
    user = models.ForeignKey("accounts.CustomUser", on_delete=models.CASCADE)
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_code = models.UUIDField(default=uuid.uuid4, editable=False)
    verification_code_small = models.IntegerField(blank=True, null=True)

    unsubscribe_code = models.UUIDField(default=uuid.uuid4, editable=False)

    def save(self, *args, **kwargs):
        if not self.verification_code_small:
            self.verification_code_small = secrets.randbelow(900000) + 100000
        super().save(*args, **kwargs)

    def create_verification_message(self):
        message = Email.objects.create(
            template="new_email_verification",
            subject="Verify your email address",
            recipient=self.email,
        )
        message.set_parameters(
            {
                "id": self.id,
                "verification_code": str(self.verification_code),
                "verification_code_small": self.verification_code_small,
            }
        )
        send_email.delay(message.id)

    def __str__(self):
        return self.email


class NotificationPhoneNumber(models.Model):
    user = models.ForeignKey("accounts.CustomUser", on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=15, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_code = models.IntegerField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.verification_code:
            self.verification_code = secrets.randbelow(900000) + 100000
        super().save(*args, **kwargs)

    def create_verification_message(self):
        message = TextMessage.objects.create(
            template="new_phone_verification",
            recipient=self.phone_number,
        )
        message.set_parameters({"verification_code": self.verification_code})
        send_text_message.delay(message.id)

    def __str__(self):
        return self.phone_number


class Email(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    sent = models.DateTimeField(blank=True, null=True)

    template = models.CharField(max_length=255)
    subject = models.CharField(max_length=255)
    parameters = models.TextField(blank=True, null=True)

    recipient = models.EmailField()

    text_body = models.TextField(blank=True, null=True)
    html_body = models.TextField(blank=True, null=True)

    def set_parameters(self, parameters):
        self.parameters = json.dumps(parameters)
        self.save()

    def get_parameters(self):
        if self.parameters:
            return json.loads(self.parameters)
        return {}


class TextMessage(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    sent = models.DateTimeField(blank=True, null=True)
    recipient = models.CharField(max_length=255)

    template = models.CharField(max_length=255)
    parameters = models.TextField(blank=True, null=True)
    message = models.TextField()

    def set_parameters(self, parameters):
        self.parameters = json.dumps(parameters)
        self.save()

    def get_parameters(self):
        if self.parameters:
            return json.loads(self.parameters)
        return {}
