import json
from django.conf import settings
import requests
from pprint import pprint as pp


class ActionChecker:
    def __init__(self, user, action):
        self.user = user
        self.action = action
        self.token = self.get_token()
        self.repo_name = self.action.repo_name
        self.branch = self.action.branch
        
        
    def make_request(self, url, method='GET', data=None):
        session = requests.Session()
        if self.token:
            session.headers.update({
                'Authorization': f'Bearer {self.token}'
            })
        session.headers.update({
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28'
        })
        response = session.request(method, url, data=data)
        return response
    
    def get_workflows(self):
        response = self.make_request(f'https://api.github.com/repos/{self.repo_name}/actions/workflows')
        data = response.json()
        workflows = {}
        for workflow in data['workflows']:
            id = workflow['id']
            path = workflow['path'].split('/')[-1]
            workflows[path] = id
        return workflows
    
    def get_my_workflow_id(self):
        workflows = self.get_workflows()
        return workflows.get(self.action.url.split('/')[-1])
    
    def get_my_workflow_runs(self):
        workflow_id = self.get_my_workflow_id()
        response = self.make_request(f'https://api.github.com/repos/{self.repo_name}/actions/workflows/{workflow_id}/runs?branch={self.branch}&status=completed')
        data = response.json()
        return data['workflow_runs']
    
    def get_last_workflow_run(self):
        workflow_runs = self.get_my_workflow_runs()
        return workflow_runs[0]
    
    def get_last_workflow_run_status(self):
        workflow_run = self.get_last_workflow_run()
        return workflow_run['conclusion']
        
    def get_token(self):
        client_id = settings.SOCIALACCOUNT_PROVIDERS['github']['APP']['client_id']
        client_secret = settings.SOCIALACCOUNT_PROVIDERS['github']['APP']['secret']
        social_token = self.user.socialaccount_set.get(provider='github').socialtoken_set.first()
        if social_token:
            access_token = social_token.token
            url = f"https://api.github.com/applications/{client_id}/token"
            headers = {
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28"
            }
            data = {
                "access_token": access_token
            }
            auth = (client_id, client_secret)

            response = requests.post(
                url,
                headers=headers,
                data=json.dumps(data),
                auth=auth
            )
            
            if response.status_code == 200:
                return access_token
            return None