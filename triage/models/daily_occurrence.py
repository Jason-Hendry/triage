from mongoengine import *
from triage.util import create_from_msg


class DailyOccurrence(Document):
    meta = {
        'indexs': ['hash']
    }

    hash = StringField(required=True)
    key = StringField(required=True, unique=True)
    timestamp = FloatField()
    count = IntField()

    def from_msg(cls, msg):
        def generator(d):
            return '{0}-{1}-{2}'.format(d.year, d.month, d.day)
        create_from_msg(cls, msg, generator)
