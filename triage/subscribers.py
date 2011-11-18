import pyramid.threadlocal as threadlocal
from pyramid.events import BeforeRender, subscriber, NewRequest

# Adds route_url method to the top level of the template context
@subscriber(BeforeRender)
def add_route_url(event):
	request = event.get('request') or threadlocal.get_current_request()
	if not request:
		return
	event['route_url'] = request.route_url

# Adds mongo db to each request
@subscriber(NewRequest)
def add_mongo_db(event):
	settings = event.request.registry.settings
	url = settings['mongodb.url']
	db_name = settings['mongodb.db_name']
	db = settings['mongodb_conn'][db_name]
	event.request.db = db	