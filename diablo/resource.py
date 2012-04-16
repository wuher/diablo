#  -*- coding: utf-8 -*-
# resource.py ---
#
# Created: Mon Nov 21 11:07:03 2011 (+0200)
# Author: Janne Kuuskeri
#

import functools
import logging

from twisted.internet import defer
from twisted.web.server import NOT_DONE_YET
from twisted.web import http
from twisted.web.resource import Resource as ResourceBase
from .http import HTTPError, Response, BadRequest
import datamapper


class Resource(ResourceBase):
    """ Base class for all resources of the REST API. """

    default_mapper = None
    mapper = None
    log = logging.getLogger('diablo')

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

        methodname, method = self._getMethod(request)
        try:
            if method:
                d = defer.maybeDeferred(
                    self._executeHandler,
                    methodname,
                    method,
                    request)
                d.addCallback(self._createResponse, request)
                d.addErrback(self._errorResponse)
                d.addCallback(self._prepareResponse, request)
                return NOT_DONE_YET
            else:
                # let the base class handle 405
                return ResourceBase.render(self, request)
        finally:
            self.log.info('"%s %s" %d' % (
                request.method,
                request.path,
                request.code if method else 501))

    def _getMethod(self, request):
        """ Return request method information.

        Returns a tuple with the name of the requested method in lower case
        and the actual method, or ``None`` if this resource doesn't implement
        the requested method.

        :returns: tuple of (``method name``, ``method``)
        """

        methodname = request.method.lower()
        method = getattr(self, methodname, None)
        return methodname, method

    def _executeHandler(self, methodname, method, request):
        """ Execute handler.

        First, read and parse the content data.
        """
        if methodname in ('put', 'post',):
            data = self._get_input_data(request)
            method = functools.partial(method, data)
        return method(request, *self.args, **self.kw)

    def _errorResponse(self, err):
        """ Handle errors.

        If the error is ``HTTPError`` turn it into appropriate http
        response code.
        """

        try:
            err.raiseException()
        except HTTPError, error:
            return Response.fromError(error)

    def _prepareResponse(self, response, request):
        """ Prepare the HTTP response.

        Set response code, headers and return body as a string.
        """
        request.setResponseCode(response.code)
        for key, value in response.headers.items():
            request.setHeader(key, value)
        request.write(response.content)
        request.finish()
        return NOT_DONE_YET

    def _createResponse(self, data, request):
        """ Create successful Response object. """
        res = datamapper.encode(request, data, self)
        if res.code is 0:
            res.code = http.OK

        return Response(res.code, res.content, res.headers)

    def _get_input_data(self, request):
        """ If there is data, parse it, otherwise return None. """
        content = [row for row in request.read()]
        content = ''.join(content) if content else None
        return self._parse_input_data(content, request) if content else None

    def _parse_input_data(self, data, request):
        """ Execute appropriate parser. """
        return datamapper.decode(data, request, self)

#
# resource.py ends here
