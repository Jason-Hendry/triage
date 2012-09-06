from mongoengine import *
import re
from mongoengine.queryset import DoesNotExist, QuerySet
from triage.models.error_hasher import ErrorHasher
from triage.models.daily_occurrence import DailyOccurrence
from triage.models.hourly_occurrence import HourlyOccurrence
from triage.models.user import User
from triage.models.comment import Comment

keyword_re = re.compile(r'\w+')


class ErrorQuerySet(QuerySet):

    def search(self, search_keywords):
        search_keywords = re.split("\s+", search_keywords)

        qObjects = Q()
        for keyword in search_keywords:
            qObjects = qObjects | Q(keywords__icontains=keyword) | Q(type__icontains=keyword) | Q(tags__icontains=keyword)

        return self.filter(qObjects)

    def resolved(self):
        return self.filter(hiddenby__exists=True)

    def active(self):
        return self.filter(hiddenby__exists=False)


class Error(Document):
    meta = {
        'queryset_class': ErrorQuerySet,
        'allow_inheritance': False,
        'ordering': ['-timelatest'],
        'indexes': ['count', 'timelatest', 'comments', 'hash', 'keywords']
    }

    hash = StringField(required=True, unique=True)
    project = StringField(required=True)
    language = StringField(required=True)
    message = StringField(required=True)
    type = StringField(required=True)
    line = IntField()
    file = StringField()
    context = DictField()
    backtrace = ListField(DictField())
    timelatest = FloatField()
    timefirst = FloatField()
    firstcommit = StringField()
    lastcommit = StringField()
    count = IntField()
    claimedby = ReferenceField(User)
    keywords = ListField(StringField())
    tags = ListField(StringField(max_length=30))
    comments = ListField(EmbeddedDocumentField(Comment))
    seenby = ListField(ReferenceField(User))
    hiddenby = ReferenceField(User)

    @classmethod
    def validate_and_upsert(cls, msg):
        msg['timelatest'] = msg['timestamp']

        error = cls.create_from_msg(msg)
        error.validate()

        keywords = list(set(keyword_re.findall(msg['message'].lower())))

        insert_doc = {
                'hash': msg['hash'],
                'project': msg['project'],
                'language': msg['language'],
                'message': msg['message'],
                'type': msg['type'],
                'line': msg['line'],
                'file': msg['file'],
                'context': msg['context'],
                'backtrace': msg['backtrace'],
                'timelatest': msg['timelatest'],
                'timefirst': msg['timelatest'],
                'firstcommit': msg['commithash'],
                'lastcommit': msg['commithash'],
                'keywords': keywords,
                'count': 1
        }

        update_doc = {
            '$set': {
                'hash': msg['hash'],
                'project': msg['project'],
                'language': msg['language'],
                'message': msg['message'],
                'type': msg['type'],
                'line': msg['line'],
                'file': msg['file'],
                'context': msg['context'],
                'backtrace': msg['backtrace'],
                'timelatest': msg['timelatest'],
                'lastcommit': msg['commithash']
            },
            '$unset': {
                'hiddenby': 1
            },
            '$inc': {
                'count': 1
            },
            '$addToSet': {
                'keywords': {
                    '$each': keywords
                }
            }
        }

        collection = cls.objects._collection  # probs a hack

        # Update fails if document not found
        collection.update({'hash': msg['hash']}, update_doc)
        # insert fails if unique index violated
        collection.insert(insert_doc)

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
        error = cls(**msg)
        error.count = 0
        error.update_from_msg(msg)
        return error

    def claim(self, user):
        self.claimedby = user

    def is_claimed(self):
        return self.claimedby != None

    def remove_claim(self):
        self.claimedby = None

    def resolve(self, user):
        self.hiddenby = user

    def unresolve(self):
        self.hiddenby = None

    def mark_seen(self, user):

        if user not in self.seenby:
            self.seenby.append(user)

    def mark_unseen(self, user):
        if user in self.seenby:
            self.seenby.remove(user)  # does it work?

    def update_from_msg(self, msg):
        self.message = msg['message']
        self.timelatest = msg['timestamp']
        self.count = self.count + 1
        self.hiddenby = None

    def get_hourly_occurrences(self, window=12):
        return HourlyOccurrence.get_occurrences(self.hash, 1, window)

    def get_daily_occurrences(self, window=7 * 24):
        return HourlyOccurrence.get_occurrences(self.hash, 24, window)

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
