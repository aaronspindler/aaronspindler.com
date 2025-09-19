from django.urls import path

from actions.views import actions_home, action_available_notification_methods, action_details, action_graph, action_status, add_action, add_email_notification, add_phone_notification, delete_action, actions_status, remove_email_notification, remove_phone_notification

urlpatterns = [
    path("", actions_home, name="actions_home"),
    path("add", add_action, name="add_action"),
    path("actions_status", actions_status, name="actions_status"),
    path("delete/<int:pk>", delete_action, name="delete_action"),
    path("status/<uuid:private_id>", action_status, name="action_status"),
    path("graph/<uuid:private_id>", action_graph, name="action_graph"),
    path("details/<uuid:private_id>", action_details, name="action_details"),
    path("available_notification_methods/<int:pk>", action_available_notification_methods, name="action_available_notification_methods"),
    path("add_email_notification/<int:pk>", add_email_notification, name="actions_add_email_notification"),
    path("add_phone_notification/<int:pk>", add_phone_notification, name="actions_add_phone_notification"),
    path("remove_email_notification/<int:pk>", remove_email_notification, name="actions_remove_email_notification"),
    path("remove_phone_notification/<int:pk>", remove_phone_notification, name="actions_remove_phone_notification"),
]
