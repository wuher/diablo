# Simple REST framework for Twisted

Diablo aims to be simple to use REST framework for [Twisted][1]. Ultimately
diablo should incorporate pretty much the same functionality as its big
brother, the [Devil][2].

Currently, only main features are Django style [URL routing][3] and
appropriate method invocation based on the HTTP request's method.


## Todo

Next big todo is content type negotiation. Currently, diablo only supports
json. For incoming data diablo doesn't do anything, but for outgoing data,
everything is encoded (by diablo) into json. Therefore resources must always
either raise one of the exceptions derived from `diablo.http.HTTPError` or
return a dictionary that can be encoded into json.


## Example

myproject.tac:

	from twisted.application import service, internet
	from twisted.web.server import Site
	from diablo.api import RESTApi

	HTTP_PORT = 8000

	routes = [
	    ('/user/(?P<user>.{3,20})?(/)?$', 'myproject.Users'),
	    ('/order/(?P<order>\d{1,10})(/)?$', 'myproject.Orders'),
	]

	application = service.Application("MyApplication")

	class MyService(internet.TCPServer):
	    """ REST API """

	    def __init__(self):
	        internet.TCPServer.__init__(
	            self, HTTP_PORT, Site(RESTApi(routes)))
	MyService().setServiceParent(application)


myproject.py:

	from diablo.resource import Resource
	from diablo import http

	class Users(Resource):
		def get(self, request, *args, **kw):
			user_id = kw['user']
			if something_bad:
				raise http.BadRequest()
			else:
				return {
					'name': 'Luke Skywalker',
					'age': 23,
				}


If someone would send any other HTTP method besides GET to the Users resource,
diablo would automatically return `405 Method Not Allowed`.


[1]:http://twistedmatrix.com/trac/
[2]:https://github.com/wuher/devil
[3]:https://docs.djangoproject.com/en/dev/topics/http/urls/
