from django.urls import path

from utils.views import add_phone, add_email, delete_phone, delete_email, healthcheck, verify_phone, verify_email, unsubscribe, dev

urlpatterns = [
    path("dev", dev, name="dev"),
    path("healthcheck", healthcheck, name="healthcheck"),
    path("add/phone", add_phone, name="add_phone"),
    path("add/email", add_email, name="add_email"),
    path("delete/phone/<int:phone_id>", delete_phone, name="delete_phone"),
    path("delete/email/<int:email_id>", delete_email, name="delete_email"),
    path("unsubscribe/<uuid:unsubscribe_code>", unsubscribe, name="unsubscribe"),
    path("verify/phone/<int:phone_id>", verify_phone, name="verify_phone"),
    path("verify/email/<int:email_id>/<str:code>", verify_email, name="verify_email"),
    path("verify/email/<int:email_id>", verify_email, name="verify_email"),
]
