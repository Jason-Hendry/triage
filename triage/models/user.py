from mongoengine import *
from passlib.apps import custom_app_context as pwd_context
from time import time

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
