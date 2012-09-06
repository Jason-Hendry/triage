from mongoengine import *
from triage.models.project import Project


class ProjectVersion(Document):
    project = ReferenceField(Project)
    version = StringField(required=True)
    previous = StringField()
    created = IntField(required=True)
