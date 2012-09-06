from mongoengine import *
from triage.models.user import User


class Comment(EmbeddedDocument):
    author = ReferenceField(User, required=True)
    content = StringField(required=True)
    created = IntField(required=True)
