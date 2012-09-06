from mongoengine import *
from triage.util import create_from_msg, to_utctimestamp
from datetime import datetime, timedelta


class HourlyOccurrence(Document):
    meta = {
        'indexes': ['hash']
    }

    hash = StringField(required=True)
    key = StringField(required=True, unique=True)
    timestamp = FloatField()
    count = IntField()

    @classmethod
    def from_msg(cls, msg):
        def generator():
            '{0}-{1}-{2}-{3}'.format(d.year, d.month, d.day, d.hour)
        from_msg(cls, msg, generator)

    @classmethod
    def get_occurrences(cls, hash, granularity, window):
        def to_list(queryset):
            return [record for record in queryset]

        def populate_occurrences(occurrences, granularity, earliest, now):
            def to_datetime(occurrence, granularity):
                arr = occurrence.key.split("-")
                arr[3] = 0 if granularity == 24 else int(arr[3])
                return datetime(*map(int, arr))

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

        now = datetime.utcnow()
        earliest = now - timedelta(hours=window)

        try:
            occurrences = to_list(
                cls.objects(hash=hash, timestamp__gt=to_utctimestamp(earliest)).order_by("timestamp")
            )
        except DoesNotExist:
            return []

        result = populate_occurrences(occurrences, granularity, earliest, now)

        return result
