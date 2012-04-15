#  -*- coding: utf-8 -*-
# resource.py ---
#
# Created: Mon Nov 21 11:07:03 2011 (+0200)
# Author: Janne Kuuskeri
#


from twisted.internet import defer
from twisted.web.server import NOT_DONE_YET
import functools
import logging
from twisted.web import http
from twisted.web.resource import Resource as ResourceBase
from .http import HTTPError, Response, BadRequest


# try simplejson first, as it supports ``use_decimal``
try:
    import simplejson as json
except ImportError:
    import json


class Resource(ResourceBase):
    """ Base class for all resources of the REST API. """

    log = logging.getLogger('diablo')

    """ No child resources.

    By default, resources don't have child resources because
    everything is defined in the URL routes.
    """
    isLeaf = True

    def __init__(self, use_decimal=False, *args, **kw):
        """ Store parameters for future use.

        Regular expressions in URL routes can contain groups and named
        groups. These will be passed on to handler (get/put/post/...)
        functions.

        :param use_decimal: set to ``True`` if you want json mapper to
        convert numbers to ``Decimal`` instances. Note that :mod:simplejson
        must be available if this is set to ``True``.
        """

        self._use_decimal = use_decimal
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
                d.addCallback(self._createResponse)
                d.addErrback(self._errorResponse)
                d.addCallback(self._prepareResponse, request)
                return NOT_DONE_YET
            else:
                # let the base class handle 405
                return ResourceBase.render(self, request)
        finally:
            # no matter what happens, always write log
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
            rawdata = self._readData()
            data = self._parseContentData(rawdata)
            method = functools.partial(method, data)
        return method(request, *self.args, **self.kw)

    def _readData(self, request):
        """ Read the content body.

        todo: this should support deferreds.
        """

        return request.content.read()

    def _errorResponse(self, err):
        """ Hanle errors.

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
        for k, v in response.headers.items():
            request.setHeader(k, v)
        request.write(response.content)
        request.finish()

    def _parseContentData(self, data):
        """ Parse the data into dictionary.

        :param data: data as it was received from PUT or POST body.
        :type data: string.
        :returns: dictionary containing the data or ``None`` if there
                  is no data.
        :raises: BadRequest if the data cannot be parsed.
        """

        if not data:
            return None

        # possible use_decimal parameter to json decoder
        params = {} if not self._use_decimal else {'use_decimal': True}
        try:
            return json.loads(data, **params)
        except json.JSONDecodeError, exc:
            self.log.error('unable to parse json data: ' + str(exc))
            raise BadRequest()

    def _createResponse(self, data):
        """ Create successful Response object.

        todo: support for different formats
        """

        content = json.dumps(data)
        return Response(http.OK, content, {'Content-Type': 'application/json'})


#
# resource.py ends here
