from celery import shared_task

from actions.action_checker import ActionChecker
from .models import Action, ActionStatus

@shared_task
def check_action_status_badge(action_id):
    action = Action.objects.get(id=action_id)
    previous_status = action.most_recent_status()
    current_workflow_status = 'failure'
    
    error = ""
    try:
        if action.is_private:
            return
        else:
            current_workflow_status = action.badge_status()
    except Exception as e:
        current_workflow_status = 'error'
        error = str(e)

    new_status = ActionStatus.objects.create(
        action=action,
        status=current_workflow_status,
        checker='badge',
        previous_status=previous_status,
        error=error
    )
    if previous_status != None:
        if current_workflow_status != previous_status.status:
            action.send_notification(new_status)
            
@shared_task
def check_action_status_api(action_id):
    action = Action.objects.get(id=action_id)
    previous_status = action.most_recent_status()
    current_workflow_status = 'failure'
    error = ""
    try:
        checker = ActionChecker(action.owner, action)
        current_workflow_status = checker.get_last_workflow_run_status()
    except Exception as e:
        current_workflow_status = 'error'
        error = str(e)
    
    new_status = ActionStatus.objects.create(
        action=action,
        status=current_workflow_status,
        checker='api',
        previous_status=previous_status,
        error=error
    )
    # We don't want to notify for API status' yet
    # if previous_status != None:
    #     if current_workflow_status != previous_status.status:
    #         action.send_notification(new_status)

@shared_task
def check_all_actions_status_interval(interval):
    actions = Action.objects.filter(interval=interval)
    for action in actions:
        check_action_status_badge.delay(action.id)
        check_action_status_api.delay(action.id)