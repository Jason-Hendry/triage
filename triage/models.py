import re

try:
    from hashlib import md5
except:
    from md5 import new as md5

from pymongo.code import Code
from time import time
import time as _time
import datetime
from datetime import timedelta
from math import floor
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

    @classmethod
    def get_occurrence(cls, error_hash, granularity, window):
        """
        Get occurrence counts, grouped by the granularity in seconds, that
        that occurred no more than window seconds in the past.
        """

        now = time()
        earliest = now - window

        map_func = Code("""
        function() {
            var now = %d;
            var earliest = %d;
            var granularity = %d;

            function getPeriod(instance) {
                var
                    period = earliest,
                    prevPeriod = 0;

                while (period <= now ) {
                    if (instance.timestamp >= prevPeriod && instance.timestamp < period) {
                        return period;
                    }

                    prevPeriod = period;
                    period += granularity;
                }
            }

            function getKey(period) {
                return key = "occurrences:" + granularity + ":" + period;
            }

            var period = getPeriod(this);

            emit(getKey(period), {hash: this.hash, count: 0, timestamp: period});
        }
""" % (now, earliest, granularity))

        reduce_func = Code("""
        function(key, instances) {
            var result = instances.pop();
            var count = 0;
            for (instance in instances) {
                count++;
            }

            result.count = count;

            return result;
        }
""")

        instances = cls.objects(hash=error_hash, timestamp__gt=earliest).order_by('timestamp').map_reduce(map_func, reduce_func, 'inline')

        occurrences = []

        try:
            while True:
                instance = instances.next()
                occurrences.append(instance.value)
        except StopIteration:
            pass

        return occurrences


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
        print msg
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

        self.instances.append(instance)

    def get_hourly_occurrences(self, window=12):
        return HourlyOccurrences.get_occurrences(self.hash, 1, window)

    def get_daily_occurrences(self, window=7 * 24):
        return HourlyOccurrences.get_occurrences(self.hash, 24, window)

    def get_weekly_occurrences(self, window=26 * 7 * 24):
        return HourlyOccurrences.get_occurrences(self.hash, 7 * 24, window)

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
        'indexes': ['hash', 'key']
    }

    hash = StringField(required=True)
    key = StringField(required=True, unique=True)
    timestamp = FloatField()
    count = IntField()

    @classmethod
    def get_occurrences(cls, hash, granularity, window):
        def get_date(prev_occurrence):
            date_keys = prev_occurrence.key.split('-')
            return datetime.datetime(year=int(date_keys[0]), month=int(date_keys[1]), day=int(date_keys[2]), hour=int(date_keys[3]))

        def timestamp(datetime, granularity):
            timestamp = datetime.year, "-", datetime.month, "-", datetime.day
            return _time.mktime(datetime.timetuple())
            if granularity == 1:
                return timestamp, "-", datetime.hour
            else:
                return timestamp

        def to_list(queryset):
            record_list = []

            for record in queryset:
                record_list.append(record)
            return record_list

        def populate_occurrences(occurrences, granularity, earliest, now):
            def to_datetime(occurrence):
                arr = occurrence.key.split("-")
                return datetime.datetime(year=int(arr[0]), month=int(arr[1]) + 1, day=int(arr[2]), hour=int(arr[3]))

            result = []
            step = earliest
            while step <= now:
                granular_occurrence = {"timestamp": timestamp(step, granularity), "count": 0}
                if len(occurrences):
                    for occurrence in occurrences:
                        d = to_datetime(occurrence)
                        print occurrence
                        print d
                        if d < step:
                            granular_occurrence['count'] += occurrence.count
                            occurrences.remove(occurrence)
                        else:
                            break
                result.append(granular_occurrence)
                step += timedelta(hours=granularity)
            return result

        now = datetime.datetime(year=2012, month=6, day=29)
        earliest = now - timedelta(hours=window)

        try:
            occurrences = to_list(
                cls.objects(hash=hash, timestamp__gt=_time.mktime(earliest.timetuple())).order_by("timestamp")
            )
        except DoesNotExist:
            return []

        for o in occurrences:
            print o.key, ' ', o.count, ' ', o.timestamp
        print '..'

        result = populate_occurrences(occurrences, granularity, earliest, now)

        for o in result:
            print o['count'], ' ', datetime.datetime.fromtimestamp(o['timestamp'])

        return result
