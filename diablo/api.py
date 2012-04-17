#  -*- coding: utf-8 -*-
# rest.py ---
#
# Created: Sat Nov 19 15:04:29 2011 (+0200)
# Author: Janne Kuuskeri
#


import re
from twisted.web.resource import Resource


class RESTApi(Resource):
    """ RESTful API implementation.

    An instance of this class can by given to twisted.web.server.Site to
    create a web service.

    Currently only implements URL routing.
    """

    def __init__(self, routes):
        """ Compile regexes and create class objects for URL routes. """
        self._routes = [(re.compile(pattern), self._getResourceClass(clsname)) 
                        for pattern, clsname in routes]
        Resource.__init__(self)

    def _getResourceClass(self, clsname):
        """ load the resource """
        modname, clsname = self._splitModClassNames(clsname)
        if modname:
            mod = __import__(modname)
            return getattr(mod, clsname)
        else:
            return globals()[clsname]

    def _splitModClassNames(self, resource_name):
        """ Split the module from the resource name """
        try:
            dot_index = resource_name.rindex('.')
        except ValueError:
            return '', resource_name
        return resource_name[:dot_index], resource_name[dot_index+1:]

    def _toggleTrailingSlash(self, url):
        """ Toggle trailing slash

        That is,
        /foo/  ->  /foo
        /foo   ->  /foo/

        """
        return url + '/' if url.endswith('/') else url[:-1]

    def getChild(self, path, request):
        """ Implement URL routing.

        todo: add memoization
        """

        def potential_match(match, route):
            """ returns route if match is not None """
            if match:
                args = match.groups() or []
                kw = match.groupdict() or {}
                return route[1](*args, **kw)
            return None

        def try_to_match(url, route):
            """ returns route if match found, None otherwise """
            matching_route = potential_match(route[0].match(url), route)
            if not matching_route:
                # no match, now try toggling the ending slash
                newpath = self._toggleTrailingSlash(request.path)
                matching_route = potential_match(route[0].match(newpath), route)
            return matching_route

        for route in self._routes:
            match = try_to_match(request.path, route)
            if match:
                return match

        # let the base class handle 404
        return Resource.getChild(self, path, request)

#
# rest.py ends here
