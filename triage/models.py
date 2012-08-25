import re

try:
    from hashlib import md5
except:
    from md5 import new as md5

import time
import datetime
from datetime import timedelta
from mongoengine import *
from mongoengine.queryset import DoesNotExist, QuerySet
from passlib.apps import custom_app_context as pwd_context

class ErrorHasher:
    digit_re = re.compile('\d+')
    string_re = re.compile(r'".*?(?<!\\)"|\'.*?(?<!\\)\'')

    def __init__(self, error):
        self.error = error

    def get_hash(self):
        return md5(str(self.get_identity())).hexdigest()

    def get_identity(self):
        return {
            'project': self.error['project'],
            'language': self.error['language'],
            'type': self.error['type'],
            'message': self.digit_re.sub('', self.string_re.sub('', self.error['message']))
        }


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


class ProjectVersion(Document):
    project = ReferenceField(Project)
    version = StringField(required=True)
    previous = StringField()
    created = IntField(required=True)


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

    def update(user, data):
        for field in ['name', 'email', 'tzoffset']:
            user[field] = data[field]

        if data['password']:
            user.password = pwd_context.encrypt(data['password'])

        return user


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

keyword_re = re.compile(r'\w+')

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
        return HourlyOccurrences.get_occurrences(self.hash, 1, window)

    def get_daily_occurrences(self, window=7 * 24):
        return HourlyOccurrences.get_occurrences(self.hash, 24, window)

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


class HourlyOccurrences(Document):
    meta = {
        'indexes': ['hash']
    }

    hash = StringField(required=True)
    key = StringField(required=True, unique=True)
    timestamp = FloatField()
    count = IntField()

    @classmethod
    def from_msg(cls, msg):
        d = datetime.datetime.utcfromtimestamp(msg['timestamp'])
        key = '{0}-{1}-{2}-{3}'.format(d.year, d.month, d.day, d.hour)

        occurrence = {
            'hash': msg['hash'],
            'project': msg['project'],
            'key': key,
            'count': 1,
            'timestamp': msg['timestamp']
        }

        update_occurrence = {
            '$set': {
                'hash': msg['hash'],
                'project': msg['project'],
                'key': key,
                'timestamp': msg['timestamp']
            },
            '$inc': {
                'count': 1
            }
        }

        result = cls.objects._collection.update({
            'key': key,
            'hash': msg['hash']
        }, update_occurrence, safe_update=True)

        if not result['updatedExisting']:
            occurrence = cls(**occurrence)
            occurrence.save()

    @classmethod
    def get_occurrences(cls, hash, granularity, window):
        def to_utctimestamp(dt):
            def utc_mktime(utc_tuple):
                """
                Returns number of seconds elapsed since epoch
                Note that no timezone are taken into consideration.
                utc tuple must be: (year, month, day, hour, minute, second)
                """
                if len(utc_tuple) == 6:
                    utc_tuple += (0, 0, 0)
                return time.mktime(utc_tuple) - time.mktime((1970, 1, 1, 0, 0, 0, 0, 0, 0))

            return int(utc_mktime(dt.timetuple()))

        def to_list(queryset):
            return [record for record in queryset]

        def populate_occurrences(occurrences, granularity, earliest, now):
            def to_datetime(occurrence, granularity):
                arr = occurrence.key.split("-")
                arr[3] = 0 if granularity == 24 else int(arr[3])
                return datetime.datetime(*map(int, arr))

            result = []
            step = earliest
            temp_occurrences = list(occurrences)

            while step <= now:
                granular_occurrence = {"timestamp": to_utctimestamp(step), "count": 0}

                if occurrences:
                    for occurrence in occurrences:
                        d = to_datetime(occurrence, granularity)
                        if d <= step:
                            granular_occurrence['count'] += occurrence.count
                            temp_occurrences.remove(occurrence)
                        else:
                            break
                occurrences = list(temp_occurrences)
                result.append(granular_occurrence)
                step += timedelta(hours=granularity)
            return result

        now = datetime.datetime.utcnow()
        earliest = now - timedelta(hours=window)

        try:
            occurrences = to_list(
                cls.objects(hash=hash, timestamp__gt=to_utctimestamp(earliest)).order_by("timestamp")
            )
        except DoesNotExist:
            return []

        result = populate_occurrences(occurrences, granularity, earliest, now)

        return result
