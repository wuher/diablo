#  -*- coding: utf-8 -*-
# resource.py ---
#
# Created: Mon Nov 21 11:07:03 2011 (+0200)
# Author: Janne Kuuskeri
#


try:
    import json
except ImportError:
    import simplejson as json

import xmlrpclib, yaml

from twisted.internet import defer
from twisted.web.server import NOT_DONE_YET
from twisted.web import http
from twisted.web.resource import Resource as ResourceBase
from diablo.http import HTTPError, Response, InternalServerError
import util, datamapper



class Resource(ResourceBase):
    """ Base class for all resources of the REST API. """

    _log = None
    default_mapper = None
    mapper = None

    """ No child resources.

    By default, resources don't have child resources because
    everything is defined in the URL routes.
    """
    isLeaf = True

    def __init__(self, *args, **kw):
        """ Store parameters for future use.

        Regular expressions in URL routes can contain groups and named
        groups. These will be passed on to handler (get/put/post/...)
        functions.
        """

        self.args = args or []
        self.kw = kw or {}
        ResourceBase.__init__(self)

    def render(self, request):
        """ Invoke appropriate handler function.

        This is where the incoming HTTP request first lands.

        Dispatch the request to corresponding handler function based
        on the request method (get/put/post/...).
        """
        #self.content_type = request.getHeader('content-type') or 'application/json'

        try:
            m = getattr(self, request.method.lower(), None)
            if m:
                data = self._get_input_data(request)
                d = defer.maybeDeferred(m, request, data, *self.args, **self.kw)
                d.addCallback(self._createResponse, request)
                d.addErrback(self._errorResponse)
                d.addCallback(self._prepareResponse, request)
                return NOT_DONE_YET
            else:
                # let the base class handle 405
                ResourceBase.render(self, request)
        finally:
            if self._log:
                self._log.info('"%s %s" %d' % (
                    request.method,
                    request.path,
                    request.code if m else 501))

    def _errorResponse(self, err):
      """ Create error Response obect. """
      try: 
        err.raiseException()
      except HTTPError, error:
        return Response.fromError(error)

    def _prepareResponse(self, response, request):
        """ Prepare the HTTP response.

        Set response code, headers and return body as a string.
        """

        request.setResponseCode(response.code)
        for k, v in response.headers.items():
            request.setHeader(k, v)
        request.write(response.content)
        request.finish()

    def _createResponse(self, data, request):
        """ Create successful Response object.

        todo: support for different formats
        """
        res = datamapper.format(request, data, self)
        if res.code is 0:
          res.code = 200
        return Response(res.code, res.content, res.headers)

    def _get_input_data(self, request):
        """ If there is data, parse it, otherwise return None. """
        # only PUT and POST should provide data
        if not self._is_data_method(request):
            return None

        content = [row for row in request.read()]
        content = ''.join(content) if content else None
        return self._parse_input_data(content, request) if content else None

    def _parse_input_data(self, data, request):
        """ Execute appropriate parser. """
        return datamapper.parse(data, request, self)

    def _is_data_method(self, request):
        """ Return True, if request method is either PUT or POST """
        return request.method.upper() in ('PUT', 'POST')


#
# resource.py ends here
