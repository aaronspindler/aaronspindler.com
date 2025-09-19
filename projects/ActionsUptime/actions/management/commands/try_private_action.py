from django.core.management.base import BaseCommand
from actions.models import Action
from actions.action_checker import ActionChecker
from pprint import pprint as pp

class Command(BaseCommand):
    def handle(self, *args, **options):
        action = Action.objects.get(id=3)
        owner = action.owner
        checker = ActionChecker(owner, action)
        pp(checker.get_last_workflow_run_status())