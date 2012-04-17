#  -*- coding: utf-8 -*-
# xmlrpcmapper.py ---
#
# Created: Wed Apr 11 15:40:26 2012 (-0600)
# Author: Patrick Hull
#

import xmlrpclib

from diablo.datamapper import DataMapper
from diablo import http

class XmlRpcMapper(DataMapper):
    """XML-RPC mapper

    The mapper must be set using the format arg or explicitly in the 
    resource, otherwise XmlMapper will be used for content-type text/xml.
    """
    content_type = 'text/xml'

    def __init__(self, methodresponse=True, allow_none=True):
        self.methodresponse = methodresponse
        self.allow_none = allow_none

    def _format_data(self, data, charset):
        try:
            return xmlrpclib.dumps((data,), 
                      methodresponse=self.methodresponse,
                      allow_none=self.allow_none,
                      encoding=charset)
        except TypeError, err:
            raise http.InternalServerError('unable to encode data')

    def _parse_data(self, data, charset):
        try:
            return xmlrpclib.loads(data)
        except ValueError:
            raise http.BadRequest('unable to parse data')
    
    

