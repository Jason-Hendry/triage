from mongoengine import *
from triage.models.error import Error


class Project(Document):
    name = StringField(required=True)
    token = StringField(required=True)
    path = StringField()
    github = StringField()

    def clean_file_path(self, path):
        return path.replace(self.path, '')

    def errors(self):
        return Error.objects(project=self.token)

    def update(project, data):
        for field in ['name', 'token', 'path', 'github']:
            project[field] = data[field]

        return project
