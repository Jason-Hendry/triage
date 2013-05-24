from mongoengine import *
import re
try:
    from hashlib import md5
except:
    from md5 import new as md5


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
