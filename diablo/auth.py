#  -*- coding: utf-8 -*-
#  auth.py ---
#  created: 2013-06-18 11:57:55
#


import base64
from twisted.internet import defer
from twisted.web import http
from .http import Unauthorized, Forbidden, Response


def authenticate(username, password):
    """ Check credentials.

    :returns: `True` if credentials match, `False` otherwise. May also
        return deferred and later invoke callback with the username, or
        errback with ``Forbidden`` or ``Unauthorized``.

    .. note::

        This implementation always raises ``NotImplemented`` error.
        Client code should provide implementation via
        `register_authenticator()` function.
    """

    raise NotImplemented('authenticate() not implemented')


def register_authenticator(fn):
    """ Register authenticator function.

    This will always override any previously registered functions.

    .. seealso:: ``authenticate()`` function
    """

    global authenticate
    authenticate = fn


class HttpBasic(object):
    def authenticate(self, request):
        """ Authenticate request using HTTP Basic authentication protocl.

        Returns deferred whose callback will eventually be called with the
        username if the login succeeded. If the login fails, errback is
        called with ``Forbidden`` or ``Unauthorized`` error.

        :returns: deferred
        :raises: ``Unauthorized`` if `Authorization` header is not present.
        """

        global authenticate

        auth_header = request.getHeader('authorization') or None

        if auth_header:
            auth = auth_header.split()
            if len(auth) == 2:
                if auth[0].lower() == "basic":
                    uname, passwd = base64.b64decode(auth[1]).split(':')
                    d = defer.maybeDeferred(authenticate, uname, passwd)
                    def auth_callback(success):
                        if success:
                            return uname
                        else:
                            raise Forbidden()
                    d.addCallback(auth_callback)
                    return d
        # either no auth header or using some other auth protocol,
        # we'll return a challenge for the user anyway
        raise Unauthorized()

    def auth_failed(self, exc):
        """ Generate HTTP Response for the client when authentication fails.

        According to the HTTP Basic authentication, return challenge.
        """

        content = exc.content or ''
        response = Response(code=http.UNAUTHORIZED, content=content)
        response.headers['WWW-Authenticate'] = 'Basic realm="diablo"'
        return response


#
#  auth.py ends here
