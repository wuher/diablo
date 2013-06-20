#  -*- coding: utf-8 -*-
# http.py ---
#
# Created: Tue Nov 22 14:11:40 2011 (+0200)
# Author: Janne Kuuskeri
#


from twisted.web import http


class HTTPError(Exception):
    def __init__(self, code, content=None):
        self.code = code
        self.content = content


class BadRequest(HTTPError):
    def __init__(self, content=None):
        HTTPError.__init__(self, http.BAD_REQUEST, content)


class Unauthorized(HTTPError):
    def __init__(self, content=None):
        HTTPError.__init__(self, http.UNAUTHORIZED, content)


class Forbidden(HTTPError):
    def __init__(self, content=None):
        HTTPError.__init__(self, http.FORBIDDEN, content)


class NotFound(HTTPError):
    def __init__(self, content=None):
        HTTPError.__init__(self, http.NOT_FOUND, content)


class MethodNotAllowed(HTTPError):
    def __init__(self, content=None):
        HTTPError.__init__(self, http.NOT_ALLOWED, content)


class Conflict(HTTPError):
    def __init__(self, content=None):
        HTTPError.__init__(self, http.CONFLICT, content)


class InternalServerError(HTTPError):
    def __init__(self, content=None):
        HTTPError.__init__(self, http.INTERNAL_SERVER_ERROR, content)


class NotAcceptable(HTTPError):
    def __init__(self, content=None):
        HTTPError.__init__(self, http.NOT_ACCEPTABLE, content)


class Response(object):

    @classmethod
    def fromError(cls, error):
        return cls(error.code, error.content)

    def __init__(self, code=None, content=None, headers=None):
        self.code = code
        self.content = content or ''
        self.headers = headers if headers is not None else {}

    def __repr__(self):
        return '%s: code[%d], content[%s], headers[%s]' % (
            self.__class__.__name__,
            self.code,
            self.content,
            repr(self.headers))


#
# http.py ends here
