#  -*- coding: utf-8 -*-
# yamlmapper.py ---
#
# Created: Wed Apr 11 15:40:26 2012 (-0600)
# Author: Patrick Hull
#

import yaml

from diablo.datamapper import DataMapper
from diablo import http

class YamlMapper(DataMapper):
    """YAML mapper
    """
    content_type = 'application/yaml'

    def __init__(self, default_flow_style=True):
        self.default_flow_style = default_flow_style

    def _format_data(self, data, charset):
        return yaml.dump(data, default_flow_style=self.default_flow_style,
                         encoding=charset)

    def _parse_data(self, data, charset):
        return yaml.load(data) 
       
 
