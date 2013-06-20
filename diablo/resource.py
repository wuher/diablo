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
from .http import HTTPError, Response, Unauthorized, Forbidden
import datamapper


class Resource(ResourceBase):
    """ Base class for all resources of the REST API. """

    default_mapper = None
    mapper = None
    authentication = None
    allow_anonymous = True

    log = logging.getLogger('diablo')
    datalog = logging.getLogger('diablo.data')

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
                d = defer.maybeDeferred(self._authenticate, request)
                data = self._getInputData(request)
                data = self._validateInputData(data, request)
                data = self._createObject(data, request)
                d.addCallback(
                    self._executeHandler,
                    methodname,
                    method,
                    data,
                    request)
                d.addCallback(self._processResponse, request)
                d.addErrback(self._httpError)
                d.addErrback(self._unknownError)
                d.addCallback(self._writeResponse, request)
                return NOT_DONE_YET
            else:
                # let the base class handle 405
                return ResourceBase.render(self, request)
        finally:
            self.log.info('"%s %s" %d' % (
                request.method,
                request.path,
                request.code if method else 501))

    def _authenticate(self, request):
        """ Authenticates the request if authentication is specified.

        If authentication succeeds, username is stored in `request.user`.

        :returns: username or `deferred`
        """

        def anonymous_access(exc_obj):
            """ Check whether anonymous access is allowed. """
            if not request.user and not self.allow_anonymous:
                raise exc_obj

        request.user = None
        if self.authentication:
            try:
                request.user = self.authentication.authenticate(request)
            except Unauthorized, exc:
                anonymous_access(exc)
        else:
            anonymous_access(Forbidden())
        return request.user

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

    def _executeHandler(self, username, methodname, method, data, request):
        """ Execute handler.

        First, read and parse the content data.
        """

        if methodname in ('put', 'post',):
            method = functools.partial(method, data)
        return method(request, *self.args, **self.kw)

    def _httpError(self, failure):
        """ event: error in ``_executeHandler`` or ``_processResponse``.

        Handles ``HTTPError``s and propagates others to next errback.
        """

        failure.trap(HTTPError)
        res = self._getErrorResponse(failure.value)
        self.log.error(str(res))
        return res

    def _unknownError(self, failure):
        """ event: error in ``_executeHandler`` or ``_processResponse``.

        Handles everything that ``_httpError`` doesn't (i.e. all other
        exceptions besides ``HTTPError``s).
        """

        res = self._getUnknownErrorResponse(failure.value)
        self.log.error(failure.getTraceback())
        return res

    def _getErrorResponse(self, exc):
        """ Turn ``HTTPError`` into appropriate ``Response``.

        :returns: ``diablo.Response``
        """

        if exc.code == http.UNAUTHORIZED:
            return self._getAuthFailedResponse(exc)
        else:
            content = exc.content or ''
            return Response(code=exc.code, content=content)

    def _getAuthFailedResponse(self, exc):
        """ Return HTTP response for when auth failed. """

        return self.authentication.auth_failed(exc)

    def _getUnknownErrorResponse(self, exc):
        """ Turn unknown error into ``Response``.

        :returns: ``diablo.Response``
        """

        return Response(code=http.INTERNAL_SERVER_ERROR, content=str(exc))

    def _processResponse(self, response, request):
        """ Process the response returned by the resource.

        The response needs to be serialized, validated and formatted using
        appropriate datamapper.

        :returns: ``diablo.Response``
        """

        def coerce_response():
            """ Coerce the response object into diable structure. """
            if not isinstance(response, Response):
                return Response(0, response)
            return response

        diablo_res = coerce_response()
        if diablo_res.content and diablo_res.code in (0, 200, 201):
            # serialize, format and validate
            serialized_res = diablo_res.content = self._serializeObject(diablo_res.content, request)
            formatted_res = self._formatResponse(request, diablo_res)
            self._validateOutputData(response, serialized_res, formatted_res, request)
        else:
            # no data -> format only
            formatted_res = self._formatResponse(request, diablo_res)
        return formatted_res

    def _validateInputData(self, data, request):
        """ todo: implement """
        return data

    def _createObject(self, data, request):
        """ todo: implement """
        return data

    def _validateOutputData(
        self, original_res, serialized_res, formatted_res, request):
        """ todo: implement """
        pass

    def _serializeObject(self, data, request):
        """ todo: implement """
        return data

    def _formatResponse(self, request, response):
        """ Format the response using a datamapper.

        :returns: ``diablo.Response``
        """

        # content
        response = datamapper.encode(request, response, self)
        # status code
        if response.code is 0:
            response.code = http.OK
        return response

    def _writeResponse(self, response, request):
        """ Prepare the HTTP response.

        Set response code, headers and return body as a string.
        """

        request.setResponseCode(response.code)
        for key, value in response.headers.items():
            request.setHeader(key, value)
        self.datalog.info('>> "%s"' % ((response.content if response.content else ''),))
        request.write(response.content)
        request.finish()
        return NOT_DONE_YET

    def _getInputData(self, request):
        """ If there is data, parse it, otherwise return None. """
        content = [row for row in request.content.read()] if request.content else None
        content = ''.join(content) if content else None
        self.datalog.info('<< "%s"' % ((content if content else ''),))
        return self._parseInputData(content, request) if content else None

    def _parseInputData(self, data, request):
        """ Execute appropriate parser. """
        return datamapper.decode(data, request, self)

#
# resource.py ends here
