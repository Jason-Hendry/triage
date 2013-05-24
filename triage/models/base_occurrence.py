from datetime import timedelta, datetime
import time


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


def generate_key(granularity, d):
    return {
        'days': lambda d: '%s-%s-%s' % (d.year, d.month, d.day),
        'hours': lambda d: '%s-%s-%s-%s' % (d.year, d.month, d.day, d.hour)
    }[granularity](d)


class BaseOccurrence():
    @classmethod
    def from_msg(cls, msg):
        d = datetime.utcfromtimestamp(msg['timestamp'])
        key = generate_key(cls.granularity, d)

        update_occurrence = {
            '$set': {
                'timestamp': msg['timestamp']
            },
            '$inc': {
                'count': 1
            }
        }

        cls.objects._collection.update({
            '_cls': cls.__name__,
            '_types': [cls.__name__],
            'key': key,
            'hash': msg['hash'],
            'project': msg['project']
        }, update_occurrence, upsert=True)

    @classmethod
    def get_occurrences(cls, hash, window):
        def populate_occurrences(occurrences, earliest, now):
            def match_occurrence(key, occurrences):
                for o in occurrences:
                    if o.key == key:
                        return o

            def to_datetime(occurrence):
                return datetime(*map(int, occurrence.key.split("-")))

            result = []
            step = earliest

            while step <= now:
                occurrence = {"timestamp": to_utctimestamp(step), "count": 0}
                match = match_occurrence(generate_key(cls.granularity, step), occurrences)

                if match:
                    occurrence['count'] = match.count

                result.append(occurrence)
                step += timedelta(**{cls.granularity: 1})
            return result

        now = datetime.utcnow()
        earliest = now - timedelta(**{cls.granularity: window})

        try:
            occurrences = cls.objects(hash=hash, timestamp__gt=to_utctimestamp(earliest)).order_by("timestamp")
        except DoesNotExist:
            return []

        result = populate_occurrences(occurrences, earliest, now)

        return result
