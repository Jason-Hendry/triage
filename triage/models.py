import re

try:
    from hashlib import md5
except:
    from md5 import new as md5

from time import time
from mongoengine import *
from mongoengine.queryset import DoesNotExist, QuerySet
from passlib.apps import custom_app_context as pwd_context


class ErrorHasher:
    digit_re = re.compile('\d')
    hex_re = re.compile('["\'\s][0-9a-f]+["\'\s]')

    def __init__(self, error):
        self.error = error

    def get_hash(self):
        return md5(str(self.get_identity())).hexdigest()   

    def get_identity(self):
        return {
            'project': self.error['project'],
            'language': self.error['language'],
            'type': self.error['type'],
            'message': self.digit_re.sub('', self.hex_re.sub('', self.error['message']))
        }


class User(Document):
    name = StringField(required=True)
    email = EmailField(required=True)
    password = StringField(required=True)
    created = IntField(required=True)
    tzoffset = IntField()

    @classmethod
    def from_data(cls, data):
        return cls(
                name=data['name'],
                email=data['email'],
                password=pwd_context.encrypt(data['password']),
                created=int(time())
            )


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


class Comment(EmbeddedDocument):
    author = ReferenceField(User, required=True)
    content = StringField(required=True)
    created = IntField(required=True)



class ErrorQuerySet(QuerySet):

    def search(self, search_keywords):
        search_keywords = re.split("\s+", search_keywords)

        qObjects = Q()
        for keyword in search_keywords:
            qObjects = qObjects | Q(message__icontains=keyword) | Q(type__icontains=keyword)

        return self.filter(qObjects)

    def resolved(self, project):
        selected_project = project['id']
        self.filter(project=selected_project)
        return self.filter( hiddenby__exists=True)

    def active(self, project):
        selected_project = project['id']
        self.filter(project=selected_project)
        return self.filter( hiddenby__exists=False)


class Error(Document):
    meta = {
        'queryset_class': ErrorQuerySet,
        'ordering': ['-timelatest'],
        'indexes': ['-count', '+count', '-timelatest', '+timelatest', '-comments', '+comments', '+hash']
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
    timelatest = IntField()
    instances = ListField(DictField())
    count = IntField()
    claimedby = ReferenceField(User)
    tags = ListField(StringField(max_length=30))
    comments = ListField(EmbeddedDocumentField(Comment))
    seenby = ListField(ReferenceField(User))
    hiddenby = ReferenceField(User) 

    @classmethod
    def from_msg(cls, msg):
        hash = ErrorHasher(msg).get_hash()
        msg['hash'] = hash
        try:
            error = cls.objects.get(hash=hash)
            error.update_from_msg(msg)
        except DoesNotExist:
            error = cls.create_from_msg(msg)
        return error

    @classmethod
    def create_from_msg(cls, msg):
        now = int(time())
        error = cls(**msg)
        error.count = 0
        error.update_from_msg(msg)
        return error

    def update_from_msg(self, msg):
        now = int(time())
        instance = {
            'timecreated': now,
            'message': msg['message']
        }
        self.message = msg['message']
        self.timelatest = now
        self.count = self.count + 1
        self.hiddenby = None
        self.instances.append(instance)

    @property
    def timefirst(self):
        return self.instances[0]['timecreated']

    def get_row_classes(self, user):
        classes = []
        user not in self.seenby and classes.append('unseen')
        user in self.seenby and classes.append('seen')
        self.hiddenby and classes.append('hidden')
        self.claimedby == user and classes.append('mine')
        return ' '.join(classes)
