from django.conf import settings
from django.urls import path

from web.views import endpoint_status_webhook, endpoints_home, endpoints_status, add_endpoint, edit_endpoint, delete_endpoint, endpoint_details, endpoint_status, endpoint_status_timeline, endpoint_latency_timeline, endpoint_available_notification_methods, add_email_notification, add_phone_notification, remove_email_notification, remove_phone_notification
urlpatterns = [
    path("", endpoints_home, name="endpoints_home"),
    path("webhook/<str:key>", endpoint_status_webhook, name="endpoint_status_webhook"),
    path("endpoints_status", endpoints_status, name="endpoints_status"),
    path("add", add_endpoint, name="add_endpoint"),
    path("edit/<int:pk>", edit_endpoint, name="edit_endpoint"),
    path("delete/<int:pk>", delete_endpoint, name="delete_endpoint"),
    path("status/<uuid:private_id>", endpoint_status, name="endpoint_status"),
    path("graph/status/<uuid:private_id>", endpoint_status_timeline, name="endpoint_status_timeline"),
    path("graph/latency/<uuid:private_id>", endpoint_latency_timeline, name="endpoint_latency_timeline"),
    path("details/<uuid:private_id>", endpoint_details, name="endpoint_details"),
    path("available_notification_methods/<int:pk>", endpoint_available_notification_methods, name="endpoint_available_notification_methods"),
    path("add_email_notification/<int:pk>", add_email_notification, name="add_email_notification"),
    path("add_phone_notification/<int:pk>", add_phone_notification, name="add_phone_notification"),
    path("remove_email_notification/<int:pk>", remove_email_notification, name="remove_email_notification"),
    path("remove_phone_notification/<int:pk>", remove_phone_notification, name="remove_phone_notification"),
]

if settings.TESTING:
    import web.testing_views as testing_views
    urlpatterns += [
        path("testing/get_success", testing_views.testing_view__get_success, name="testing_view__get_success"),
        path("testing/get_failure", testing_views.testing_view__get_failure, name="testing_view__get_failure"),
        path("testing/post_success", testing_views.testing_view__post_success, name="testing_view__post_success"),
        path("testing/post_failure", testing_views.testing_view__post_failure, name="testing_view__post_failure"),
        path("testing/post_json_success", testing_views.testing_view__post_json_success, name="testing_view__post_json_success"),
        path("testing/post_body_success", testing_views.testing_view__post_body_success, name="testing_view__post_body_success"),
        path("testing/redirect_get", testing_views.testing_view_redirect_get, name="testing_view_redirect_get"),
        path("testing/slow_response", testing_views.testing_view__slow_response, name="testing_view__slow_response"),
        path("testing/custom_header", testing_views.testing_view__custom_header, name="testing_view__custom_header"),
        path("testing/server_error", testing_views.testing_view__server_error, name="testing_view__server_error"),
    ]