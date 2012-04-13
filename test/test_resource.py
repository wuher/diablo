import json

from twisted.internet import defer, reactor
from twisted.web import server
from twisted.web.test.test_web import DummyRequest
from twisted.trial import unittest
from twisted.internet.defer import succeed
from twisted.python import log

from diablo.resource import Resource
from diablo.api import RESTApi
from diablo.mappers.xmlmapper import XmlMapper
from diablo.mappers.jsonmapper import JsonMapper
from diablo.mappers.yamlmapper import YamlMapper

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

def _render(resource, request):
    result = resource.render(request)
    if isinstance(result, str):
        #for k, v in request.headers.items():
        #    request.setHeader(k, v)
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
  ('/testregular(?P<format>\.?\w{1,8})?$', 'test_resource.RegularTestResource'),
  ('/testdeferred(?P<format>\.?\w{1,8})?$', 'test_resource.DeferredTestResource'),
]

params = {'indent': 4,'ensure_ascii': False,'encoding': 'utf-8',}

xmlMapper = XmlMapper()
jsonMapper = JsonMapper()
yamlMapper = YamlMapper()


class ResourceTestCase(unittest.TestCase):

    def setUp(self):
        self.api = RESTApi(routes)

    def test_regular_response(self):
        request = DummyRequest([''])
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
        request = DummyRequest([''])
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
        request = DummyRequest([''])
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
        request = DummyRequest([''])
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
        request = DummyRequest([''])
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
        request = DummyRequest([])
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
        request = DummyRequest([])
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
        request = DummyRequest([])
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
        request = DummyRequest([])
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
        request = DummyRequest([])
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
        request = DummyRequest([])
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

    

