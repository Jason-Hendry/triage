from mongoengine import *


class Tag(Document):
    meta = {
        'ordering': ['-count']
    }

    tag = StringField(required=True)
    count = IntField(required=True)
    created = IntField(required=True)

    @classmethod
    def create(cls, value):
        try:
            tag = cls.objects.get(tag=value)
            tag.count = tag.count + 1
        except DoesNotExist:
            tag = cls.create_from_tag(value)
        return tag

    @classmethod
    def removeOne(cls, value):
        try:
            tag = cls.objects.get(tag=value)
            tag.count = tag.count - 1
            tag.save()
        except DoesNotExist:
            pass

    @classmethod
    def create_from_tag(cls, value):
        tag = cls()
        tag.tag = value
        tag.count = 1
        tag.created = int(time())
        return tag
