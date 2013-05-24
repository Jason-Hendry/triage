import json
import mongoengine
import logging
from sys import argv
from pyramid.paster import get_appsettings
from models import Error, ErrorHasher, ErrorInstance
from time import time

from twisted.web import server, resource
from twisted.internet import reactor

#logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')

# config
logging.info('Loading configuration')
settings = get_appsettings(argv[1], 'triage')

# mongo
logging.info('Connecting to mongo at: mongodb://' + settings['mongodb.host'] + '/' + settings['mongodb.db_name'])
mongoengine.connect(settings['mongodb.db_name'], host=settings['mongodb.host'])

class Simple(resource.Resource):
    isLeaf = True
    def render_POST(self, request):
        try:
            unpacker = json.loads(request.content.read())
            logging.debug('fed data to unpacker')
            for msg in unpacker:
                logging.debug('found message in unpacker')
                if type(msg) == dict:
                    logging.debug('found object in message')

                    msg['hash'] = ErrorHasher(msg).get_hash()
                    logging.debug(msg)
                    if 'timestamp' not in msg:
                        msg['timestamp'] = int(time())

                    Error.validate_and_upsert(msg)
                    logging.debug('saved error')

                    ErrorInstance.from_raw(msg).save(safe=False)
                    logging.debug('saved instance')

        except Exception, a:
            logging.exception('Failed to process error')
            return 'FAILED';
        return "OK";

site = server.Site(Simple())
reactor.listenTCP(9090, site)
reactor.run()
