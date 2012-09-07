from mongoengine import *


class ErrorInstance(Document):
    meta = {
        'allow_inheritance': False,
        'ordering': ['-timestamp'],
        'indexes': ['hash', 'timestamp', ('hash', '-timestamp')]
    }

    hash = StringField(required=True)
    project = StringField(required=True)
    language = StringField(required=True)
    message = StringField(required=True)
    type = StringField(required=True)
    line = IntField()
    file = StringField()
    context = DictField()
    backtrace = ListField(DictField())
    timestamp = FloatField()

    @classmethod
    def from_raw(cls, raw):
        return cls(**raw)
