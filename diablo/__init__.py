
import datamapper
from diablo.mappers.xmlmapper import XmlMapper
from diablo.mappers.jsonmapper import JsonMapper
from diablo.mappers.yamlmapper import YamlMapper

def register_mappers():
    textmapper = datamapper.DataMapper()
    jsonmapper = JsonMapper()
    xmlmapper = XmlMapper(numbermode='basic')
    yamlmapper = YamlMapper()

    # we'll be tolerant on what we receive
    # remember to put these false content types in the beginning so that they
    # are overridden by the proper ones
    datamapper.manager.register_mapper(jsonmapper, 'application/x-javascript', 'json')
    datamapper.manager.register_mapper(jsonmapper, 'text/javascript', 'json')
    datamapper.manager.register_mapper(jsonmapper, 'text/x-javascript', 'json')
    datamapper.manager.register_mapper(jsonmapper, 'text/x-json', 'json')

    # text mapper
    datamapper.manager.register_mapper(textmapper, 'text/plain', 'text')

    # xml mapper
    datamapper.manager.register_mapper(xmlmapper, 'application/xml', 'xml')
    datamapper.manager.register_mapper(xmlmapper, 'text/xml', 'xml')

    # json mapper
    datamapper.manager.register_mapper(jsonmapper, 'application/json', 'json')

    # yaml mapper
    datamapper.manager.register_mapper(yamlmapper, 'text/yaml', 'yaml')
    datamapper.manager.register_mapper(yamlmapper, 'application/yaml', 'yaml')

register_mappers()
