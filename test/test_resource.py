#  -*- coding: utf-8 -*-
#  test_resource.py ---
#

import json
import base64

from twisted.internet import defer, reactor
from twisted.web import server
from twisted.web.test.test_web import DummyRequest
from twisted.trial import unittest
from twisted.internet.defer import succeed
from twisted.python import log
from twisted.web.http import OK, NOT_FOUND, INTERNAL_SERVER_ERROR, CONFLICT

from diablo.resource import Resource
from diablo.api import RESTApi
from diablo.auth import HttpBasic, register_authenticator
from diablo.mappers.xmlmapper import XmlMapper
from diablo.mappers.jsonmapper import JsonMapper
from diablo.mappers.yamlmapper import YamlMapper
from diablo.http import NotFound, Response, Conflict


class DiabloDummyRequest(DummyRequest):

    code = OK
    data = ''

    def __init__(self, *args, **kw):
        DummyRequest.__init__(self, *args, **kw)
        self.content = self

    def read(self):
        return self.data


class UnaccessibleResource(Resource):

    allow_anonymous = False

    def get(self, request):
        return 'you will never see this'


class AuthenticatedResource(Resource):

    allow_anonymous = False
    authentication = HttpBasic()

    def get(self, request):
        return 'hello %s' % (request.user,)


class DiabloTestResource(Resource):

    collection = {}

    def get(self, request, *args, **kw):
        if 'key' in kw:
            key = kw.get('key')
            if key in self.collection:
                return self.collection[key]
            else:
                raise NotFound()
        else:
            return self.collection

    def put(self, data, request, *args, **kw):
        for k in data:
            self.collection[k] = data[k]

    def post(self, data, request, *args, **kw):
        for k in data:
            self.collection[k] = data[k]

    def delete(self, request, *args, **kw):
        if 'key' in kw:
            key = kw.get('key')
            if key in self.collection:
                removed = self.collection.pop(kw['key'])
                log.msg('removed', removed)
            else:
                raise NotFound()
        else:
            log.msg('removing entire collection')
            self.collection = {}


class RouteTestResource1(Resource):

    def get(self, request, *args, **kw):
        return {'nothing': 'something'}


class RouteTestResource2(Resource):

    def get(self, request, *args, **kw):
        return {'something': 'nothing'}


regular_result = {'name': 'luke skywalker', 'occupation': 'jedi'}


class RegularTestResource(Resource):

    def get(self, request, *args, **kw):
        return regular_result


deferred_result = [1, 2, 3, 4, 5]


class DeferredTestResource(Resource):

    def get(self, request, *args, **kw):
        d = defer.Deferred()
        reactor.callLater(0, d.callback, deferred_result)
        return d


class ErrorResource(Resource):
    """ Resource to test error scenarios. """

    def get(self, request, id, *args, **kw):
        self.error_id = int(id)
        if self.error_id is 1:
            raise NotFound("Can't find it, sorry.")
        elif self.error_id is 2:
            raise Exception('Unknown exception.')
        else:
            return {'id': 9}

    def _processResponse(self, request, response):
        if self.error_id is 3:
            raise Conflict("There's a conflict my friend.")
        elif self.error_id is 4:
            raise TypeError('Bad type.')
        else:
            return Response(code=OK, content='hiihoo')


def _render(resource, request):
    result = resource.render(request)
    if isinstance(result, str):
        request.write(result)
        request.finish()
        return succeed(None)
    elif result is server.NOT_DONE_YET:
        if request.finished:
            return succeed(None)
        else:
            return request.notifyFinish()
    else:
        raise ValueError("Unexpected return value: %r" % (result,))


routes = [
    ('/auth/unaccessible', 'test_resource.UnaccessibleResource'),
    ('/auth/normal', 'test_resource.AuthenticatedResource'),
    ('/testregular(?P<format>\.?\w{1,8})?$', 'test_resource.RegularTestResource'),
    ('/testdeferred(?P<format>\.?\w{1,8})?$', 'test_resource.DeferredTestResource'),
    ('/a/useless/path$', 'test_resource.RouteTestResource1'),
    ('/a/useful/path(/)?(?P<tendigit>\d{10})?$', 'test_resource.RouteTestResource2'),
    ('/a/test/resource(/)?(?P<key>\w{1,10})?$', 'test_resource.DiabloTestResource'),
    ('/error/(?P<err_id>\d{1,2})', 'test_resource.ErrorResource'),
]


params = {
    'indent': 4,
    'ensure_ascii': False,
    'encoding': 'utf-8',
    }


xmlMapper = XmlMapper()
jsonMapper = JsonMapper()
yamlMapper = YamlMapper()


class AuthResourceTest(unittest.TestCase):
    passwd = {
        'jedi': 'jedixx',
        'sith': 'sithxx'
    }

    def check_creds(self, username, password):
        passwd = self.passwd.get(username, None)
        return passwd == password

    def get_auth_header(self, username, password):
        credsz = base64.b64encode('%s:%s' % (username, password))
        return {
            'authorization': 'Basic %s' % (credsz,)
        }

    def setUp(self):
        self.api = RESTApi(routes)
        register_authenticator(self.check_creds)

    def test_get_unaccessible(self):
        request = DiabloDummyRequest([''])
        request.method = 'GET'
        request.path = '/auth/unaccessible'
        resource = self.api.getChild('/', request)
        d = _render(resource, request)

        def renderer(ignored):
            self.assertEquals(request.responseCode, 403)

        d.addCallback(renderer)

    def test_get_jedi_fail(self):
        request = DiabloDummyRequest([''])
        request.method = 'GET'
        request.path = '/auth/normal'
        request.headers = self.get_auth_header('jedi', 'jedi')

        resource = self.api.getChild('/', request)
        d = _render(resource, request)

        def renderer(ignored):
            self.assertEquals(403, request.responseCode)

        d.addCallback(renderer)

    def test_get_jedi_ok(self):
        request = DiabloDummyRequest([''])
        request.method = 'GET'
        request.path = '/auth/normal'
        request.headers = self.get_auth_header('jedi', 'jedixx')

        resource = self.api.getChild('/', request)
        d = _render(resource, request)

        def renderer(ignored):
            self.assertEquals(200, request.responseCode)

        d.addCallback(renderer)

    def test_get_anonymous(self):
        request = DiabloDummyRequest([''])
        request.method = 'GET'
        request.path = '/auth/normal'
        # request.headers = self.get_auth_header('jedi', 'jedixx')

        resource = self.api.getChild('/', request)
        d = _render(resource, request)

        def renderer(ignored):
            self.assertEquals(401, request.responseCode)

        d.addCallback(renderer)


class PutResourceTest(unittest.TestCase):

    def setUp(self):
        self.api = RESTApi(routes)

    def test_put_resource(self):
        request = DiabloDummyRequest([''])
        request.method = 'PUT'
        request.path = '/a/test/resource'
        request.headers = {'content-type': 'application/json'}
        request.data = json.dumps({'key1': 'value1'})
        resource = self.api.getChild('/ignored', request)
        d = _render(resource, request)

        def rendered(ignored):
            self.assertEquals(request.responseCode, OK)
        d.addCallback(rendered)

        request2 = DiabloDummyRequest([''])
        request2.path = '/a/test/resource/key1'
        request2.headers = {'content-type': 'application/json'}
        resource2 = self.api.getChild('/ignored', request2)

        def doGet(ignored):
            d2 = _render(resource2, request2)

            def get_rendered(ignored):
                response = ''.join(request2.written)
                response_obj = json.loads(response)
                self.assertEquals(response_obj, 'value1')
            d2.addCallback(get_rendered)
            return d2
        d.addCallback(doGet)
        return d


class PostResourceTest(unittest.TestCase):

    def setUp(self):
        self.api = RESTApi(routes)

    def test_post_resource(self):
        request = DiabloDummyRequest([''])
        request.method = 'POST'
        request.path = '/a/test/resource'
        request.headers = {'content-type': 'application/json'}
        request.data = json.dumps({'key2': 'value2'})
        resource = self.api.getChild('/ignored', request)
        d = _render(resource, request)

        def rendered(ignored):
            self.assertEquals(request.responseCode, OK)
            self.assertEquals({'key2': 'value2'}, resource.collection)
        d.addCallback(rendered)

        request2 = DiabloDummyRequest([''])
        request2.path = '/a/test/resource/key2'
        request2.headers = {'content-type': 'application/json'}
        resource2 = self.api.getChild('/ignored', request2)

        def doGet(ignored):
            d2 = _render(resource2, request2)

            def get_rendered(ignored):
                response = ''.join(request2.written)
                response_obj = json.loads(response)
                self.assertEquals(response_obj, 'value2')
            d2.addCallback(get_rendered)
            return d2
        d.addCallback(doGet)
        return d


class DeleteResourceTest(unittest.TestCase):

    def setUp(self):
        self.api = RESTApi(routes)

    def _put_something(self, key, val):
        request = DiabloDummyRequest([''])
        request.method = 'PUT'
        request.path = '/a/test/resource'
        request.headers = {'content-type': 'application/json'}
        request.data = json.dumps({key: val})
        resource = self.api.getChild('/ignored', request)
        d = _render(resource, request)

        def rendered(ignored):
            self.assertEquals(request.responseCode, OK)
        d.addCallback(rendered)
        return d

    def _delete_it(self, ignored, key):
        request = DiabloDummyRequest([''])
        request.method = 'DELETE'
        request.path = '/a/test/resource/key3'
        request.headers = {'content-type': 'application/json'}
        resource = self.api.getChild('/ignored', request)
        d = _render(resource, request)

        def rendered(ignored):
            self.assertEquals(request.responseCode, OK)
        d.addCallback(rendered)
        return d

    def _get_it(self, ignored, key):
        request = DiabloDummyRequest([''])
        request.path = '/a/test/resource/key3'
        request.headers = {'content-type': 'application/json'}
        resource = self.api.getChild('/ignored', request)
        d = _render(resource, request)

        def rendered(ignored):
            self.assertEquals(request.responseCode, NotFound().code)
        d.addCallback(rendered)

    def test_delete_resource(self):
        key, val = 'key3', 'val3'
        d = self._put_something(key, val)
        d.addCallback(self._delete_it, key)
        d.addCallback(self._get_it, key)
        return d


class ResourceRoutingTest(unittest.TestCase):

    def setUp(self):
        self.api = RESTApi(routes)

    def test_basic_route(self):
        request = DiabloDummyRequest([''])
        request.path = '/a/useless/path'
        request.headers = {'content-type': 'application/json'}
        resource = self.api.getChild('/ignored', request)
        d = _render(resource, request)

        def rendered(ignored):
            response = ''.join(request.written)
            response_obj = json.loads(response)
            self.assertEquals(response_obj, {'nothing': 'something'})
        d.addCallback(rendered)
        return d

    def test_re_group_route_wo_group(self):
        request = DiabloDummyRequest([''])
        request.path = '/a/useful/path'
        request.headers = {'content-type': 'application/json'}
        resource = self.api.getChild('/ignored', request)
        d = _render(resource, request)

        def rendered(ignored):
            response = ''.join(request.written)
            response_obj = json.loads(response)
            self.assertEquals(response_obj, {'something': 'nothing'})
        d.addCallback(rendered)
        return d

    def test_re_group_route_w_group(self):
        request = DiabloDummyRequest([''])
        request.path = '/a/useful/path/1234567890'
        request.headers = {'content-type': 'application/json'}
        resource = self.api.getChild('/ignored', request)
        d = _render(resource, request)

        def rendered(ignored):
            response = ''.join(request.written)
            response_obj = json.loads(response)
            self.assertEquals(response_obj, {'something': 'nothing'})
        d.addCallback(rendered)
        return d

    def test_re_group_route_w_invalid_group(self):
        request = DiabloDummyRequest([''])
        request.path = '/a/useful/path/1invalid01'
        request.headers = {'content-type': 'application/json'}
        resource = self.api.getChild('/ignored', request)
        d = _render(resource, request)

        def rendered(ignored):
            log.msg('ignored', ignored)
            self.assertEquals(request.responseCode, NotFound().code)
        d.addCallback(rendered)
        return d


class ResourceTestCase(unittest.TestCase):

    def setUp(self):
        self.api = RESTApi(routes)

    def test_regular_response(self):
        request = DiabloDummyRequest([''])
        request.path = '/testregular'
        request.headers = {'content-type': 'application/json'}
        resource = self.api.getChild('/testregular', request)
        d = _render(resource, request)

        def rendered(ignored):
            response = ''.join(request.written)
            response_obj = json.loads(response)
            self.assertEquals(response_obj, regular_result)
        d.addCallback(rendered)
        return d

    def test_deferred_response(self):
        request = DiabloDummyRequest([''])
        request.path = '/testdeferred'
        request.headers = {'content-type': 'application/json'}
        resource = self.api.getChild('/testdeferred', request)
        d = _render(resource, request)

        def rendered(ignored):
            response = ''.join(request.written)
            response_obj = json.loads(response)
            self.assertEquals(response_obj, deferred_result)
        d.addCallback(rendered)
        return d


class ContentTypeFormatterTestCase(unittest.TestCase):

    def setUp(self):
        self.api = RESTApi(routes)

    def test_json_formatter(self):
        request = DiabloDummyRequest([''])
        request.path = '/testregular'
        request.headers = {'content-type': 'application/json'}
        resource = self.api.getChild('/testregular', request)
        d = _render(resource, request)

        def rendered(ignored):
            response = ''.join(request.written)
            response_obj = jsonMapper._parse_data(response, 'utf-8')
            self.assertEquals(response_obj, regular_result)
            content_header = request.outgoingHeaders.get('content-type', None)
            content_type = content_header.split(';')[0] if content_header else None
            self.assertEquals(content_type, 'application/json')
        d.addCallback(rendered)
        return d

    def test_xml_formatter(self):
        request = DiabloDummyRequest([''])
        request.path = '/testregular'
        request.headers = {'content-type': 'text/xml'}
        resource = self.api.getChild('/testregular', request)
        d = _render(resource, request)

        def rendered(ignored):
            response = ''.join(request.written)
            response_obj = xmlMapper._parse_data(response, 'utf-8')
            self.assertEquals(response_obj, regular_result)
            content_header = request.outgoingHeaders.get('content-type', None)
            content_type = content_header.split(';')[0] if content_header else None
            self.assertEquals(content_type, 'text/xml')
        d.addCallback(rendered)
        return d

    def test_yaml_formatter(self):
        request = DiabloDummyRequest([''])
        request.path = '/testregular'
        request.headers = {'content-type': 'application/yaml'}
        resource = self.api.getChild('/testregular', request)
        d = _render(resource, request)

        def rendered(ignored):
            response = ''.join(request.written)
            response_obj = yamlMapper._parse_data(response, 'utf-8')
            self.assertEquals(response_obj, regular_result)
            content_header = request.outgoingHeaders.get('content-type', None)
            content_type = content_header.split(';')[0] if content_header else None
            self.assertEquals(content_type, 'application/yaml')
        d.addCallback(rendered)
        return d


class FormatArgTestCase(unittest.TestCase):

    def setUp(self):
        self.api = RESTApi(routes)

    def test_json_arg(self):
        request = DiabloDummyRequest([])
        request.path = '/testregular'
        request.args = {'format': ['json']}
        resource = self.api.getChild('/testregular', request)
        d = _render(resource, request)

        def rendered(ignored):
            response = ''.join(request.written)
            response_obj = jsonMapper._parse_data(response, 'utf-8')
            self.assertEquals(response_obj, regular_result)
            content_header = request.outgoingHeaders.get('content-type', None)
            content_type = content_header.split(';')[0] if content_header else None
            self.assertEquals(content_type, 'application/json')
        d.addCallback(rendered)
        return d

    def test_xml_arg(self):
        request = DiabloDummyRequest([])
        request.path = '/testregular'
        request.args = {'format': ['xml']}
        resource = self.api.getChild('/testregular', request)
        d = _render(resource, request)

        def rendered(ignored):
            response = ''.join(request.written)
            response_obj = xmlMapper._parse_data(response, 'utf-8')
            self.assertEquals(response_obj, regular_result)
            content_header = request.outgoingHeaders.get('content-type', None)
            content_type = content_header.split(';')[0] if content_header else None
            self.assertEquals(content_type, 'text/xml')
        d.addCallback(rendered)
        return d

    def test_yaml_arg(self):
        request = DiabloDummyRequest([])
        request.path = '/testregular'
        request.args = {'format': ['yaml']}
        resource = self.api.getChild('/testregular', request)
        d = _render(resource, request)

        def rendered(ignored):
            response = ''.join(request.written)
            response_obj = yamlMapper._parse_data(response, 'utf-8')
            self.assertEquals(response_obj, regular_result)
            content_header = request.outgoingHeaders.get('content-type', None)
            content_type = content_header.split(';')[0] if content_header else None
            self.assertEquals(content_type, 'application/yaml')
        d.addCallback(rendered)
        return d


class UrlFormatTestCase(unittest.TestCase):

    def setUp(self):
        self.api = RESTApi(routes)

    def test_json_url(self):
        request = DiabloDummyRequest([])
        request.path = '/testregular.json'
        resource = self.api.getChild('/testregular', request)
        d = _render(resource, request)

        def rendered(ignored):
            response = ''.join(request.written)
            log.msg('Response', response)
            response_obj = jsonMapper._parse_data(response, 'utf-8')
            self.assertEquals(response_obj, regular_result)
            content_header = request.outgoingHeaders.get('content-type', None)
            content_type = content_header.split(';')[0] if content_header else None
            self.assertEquals(content_type, 'application/json')
        d.addCallback(rendered)
        return d

    def test_xml_url(self):
        request = DiabloDummyRequest([])
        request.path = '/testregular.xml'
        resource = self.api.getChild('/testregular', request)
        d = _render(resource, request)

        def rendered(ignored):
            response = ''.join(request.written)
            log.msg('Response', response)
            response_obj = xmlMapper._parse_data(response, 'utf-8')
            self.assertEquals(response_obj, regular_result)
            content_header = request.outgoingHeaders.get('content-type', None)
            content_type = content_header.split(';')[0] if content_header else None
            self.assertEquals(content_type, 'text/xml')
        d.addCallback(rendered)
        return d

    def test_yaml_url(self):
        request = DiabloDummyRequest([])
        request.method = 'GET'
        request.path = '/testregular.yaml'
        resource = self.api.getChild('/testregular', request)
        d = _render(resource, request)

        def rendered(ignored):
            response = ''.join(request.written)
            log.msg('Response', response)
            response_obj = yamlMapper._parse_data(response, 'utf-8')
            self.assertEquals(response_obj, regular_result)
            content_header = request.outgoingHeaders.get('content-type', None)
            content_type = content_header.split(';')[0] if content_header else None
            self.assertEquals(content_type, 'application/yaml')
        d.addCallback(rendered)
        return d


class TestErrors(unittest.TestCase):
    def setUp(self):
        self.api = RESTApi(routes)

    def test_exec_handler_fails_http(self):
        request = DiabloDummyRequest([])
        request.method = 'GET'
        request.path = '/error/1'
        resource = self.api.getChild('/error/1', request)
        d = _render(resource, request)

        def rendered(ignored):
            response = ''.join(request.written)
            self.assertEquals(NOT_FOUND, request.responseCode)
            self.assertEquals("Can't find it, sorry.", response)
        d.addCallback(rendered)
        return d

    def test_exec_handler_fails_unknown(self):
        request = DiabloDummyRequest([])
        request.method = 'GET'
        request.path = '/error/2'
        resource = self.api.getChild('/error/2', request)
        d = _render(resource, request)

        def rendered(ignored):
            response = ''.join(request.written)
            self.assertEquals(INTERNAL_SERVER_ERROR, request.responseCode)
            self.assertEquals("Unknown exception.", response)
        d.addCallback(rendered)
        return d

    def test_processing_fails_http(self):
        request = DiabloDummyRequest([])
        request.method = 'GET'
        request.path = '/error/3'
        resource = self.api.getChild('/error/3', request)
        d = _render(resource, request)

        def rendered(ignored):
            response = ''.join(request.written)
            self.assertEquals(CONFLICT, request.responseCode)
            self.assertEquals("There's a conflict my friend.", response)
        d.addCallback(rendered)
        return d

    def test_processing_fails_unknown(self):
        request = DiabloDummyRequest([])
        request.method = 'GET'
        request.path = '/error/4'
        resource = self.api.getChild('/error/4', request)
        d = _render(resource, request)

        def rendered(ignored):
            response = ''.join(request.written)
            self.assertEquals(INTERNAL_SERVER_ERROR, request.responseCode)
            self.assertEquals("Bad type.", response)
        d.addCallback(rendered)
        return d


#
#  test_resource.py ends here
