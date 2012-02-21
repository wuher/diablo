#  -*- coding: utf-8 -*-
# resource.py ---
#
# Created: Mon Nov 21 11:07:03 2011 (+0200)
# Author: Janne Kuuskeri
#


try:
    import json
except ImportError:
    import simplejson


from twisted.web import http
from twisted.web.resource import Resource as ResourceBase
from .http import HTTPError, Response


class Resource(ResourceBase):
    """ Base class for all resources of the REST API. """

    _log = None

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

        Dispatch the request to corresponging handler function based
        on the request method (get/put/post/...).
        """

        try:
            m = getattr(self, request.method.lower(), None)
            if m:
                response = self._executeMethod(m, request)
                return self._prepareResponse(request, response)
            else:
                # let the base class handle 405
                ResourceBase.render(self, request)
        finally:
            if self._log:
                self._log.info('"%s %s" %d' % (
                    request.method,
                    request.path,
                    request.code if m else 501))

    def _prepareResponse(self, request, response):
        """ Prepare the HTTP response.

        Set response code, headers and return body as a string.
        """

        request.setResponseCode(response.code)
        for k, v in response.headers.items():
            request.setHeader(k, v)
        return response.content

    def _executeMethod(self, method, request):
        """ Execute the method that handles the request.

        @return Response object
        """

        try:
            data = method(request, *self.args, **self.kw)
        except HTTPError, error:
            return Response.fromError(error)
        else:
            return self._createResponse(data)

    def _createResponse(self, data):
        """ Create successful Response object.

        todo: support for different formats
        """
        content = json.dumps(data)
        return Response(http.OK, content, {'Content-Type': 'application/json'})


#
# resource.py ends here
