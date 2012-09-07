from mongoengine import *
from triage.models.base_occurrence import BaseOccurrence


class DailyOccurrence(Document, BaseOccurrence):
    meta = {
        'indexes': ['hash', 'project', 'key']
    }

    hash = StringField(required=True)
    key = StringField(required=True)
    project = StringField(required=True)
    timestamp = FloatField()
    count = IntField()
    granularity = 'days'
