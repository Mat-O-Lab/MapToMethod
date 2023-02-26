from re import search as re_search
import ssl
from collections import OrderedDict
from typing import List

from yaml import Loader, Dumper, dump
from yaml.representer import SafeRepresenter
from yaml.resolver import BaseResolver

from rdflib import Graph, URIRef, Namespace
from rdflib.namespace import RDF, RDFS
from rdflib.plugins.sparql import prepareQuery
from rdflib.util import guess_format
import github
from urllib.parse import urlparse, unquote

# disable ssl verification
ssl._create_default_https_context = ssl._create_unverified_context


def dict_representer(dumper, data):
    return dumper.represent_dict(data.items())


def dict_constructor(loader, node):
    return OrderedDict(loader.construct_pairs(node))


Dumper.add_representer(OrderedDict, dict_representer)
Loader.add_constructor(BaseResolver.DEFAULT_MAPPING_TAG, dict_constructor)
Dumper.add_representer(str, SafeRepresenter.represent_str)

sub_classes = prepareQuery(
    "SELECT ?entity WHERE {?entity rdfs:subClassOf* ?parent}"
)

# MSEO_URL='https://purl.matolab.org/mseo/mid'
OBO = Namespace('http://purl.obolibrary.org/obo/')
MSEO_NAMESPACE = 'https://raw.githubusercontent.com/Mat-O-Lab/MSEO/main/MSEO_mid.owl'
#CCO_URL = 'https://github.com/CommonCoreOntology/CommonCoreOntologies/raw/master/cco-merged/MergedAllCoreOntology-v1.3-2021-03-01.ttl'
MSEO_URL = './ontologies/mseo.ttl'
CCO_URL = './ontologies/cco.ttl'


MSEO = Namespace(MSEO_NAMESPACE)
CCO = Namespace('http://www.ontologyrepository.com/CommonCoreOntologies/')
CSVW = Namespace('http://www.w3.org/ns/csvw#')
OA = Namespace('http://www.w3.org/ns/oa#')

mseo_graph = Graph()
mseo_graph.parse(CCO_URL, format='turtle')
mseo_graph.parse(MSEO_URL, format='turtle')

InformtionContentEntity = CCO.InformationContentEntity
TemporalRegionClass = OBO.BFO_0000008
ContentToBearingRelation = OBO.RO_0010002

def load_graph(url,graph: Graph=Graph()):
    parsed_url=urlparse(url)
    format=guess_format(parsed_url.path)
    graph.parse(unquote(parsed_url.geturl()), format=format)
    return graph

def get_all_sub_classes(uri: URIRef):
    results = list(
        mseo_graph.query(
                sub_classes,
                initBindings={'parent': uri},
                initNs={'cco': CCO, 'mseo': MSEO},
                ),
            )
    classes = [result[0] for result in results]
    return classes


def get_methods():
    """
    Get all ttl filenames and URLs in the MSEO methods folder.

    Get all ttl files from methods folder of mseo repo,
    returns dict with method name aas key and url to file as value.
    """
    mseo_repo = github.Github().get_repo("Mat-O-Lab/MSEO")
    folder_index = mseo_repo.get_contents("methods")
    print(folder_index)
    if folder_index:
        methods_urls = [
            method.download_url for method in folder_index if method.download_url and method.download_url.endswith('ttl')]
        methods = {re_search('[^/\\&\?]+\.\w{3,4}(?=([\?&].*$|$))', url)
                   [0].split('.')[0]: url for url in methods_urls}
        return methods
    else:
        return None

class Mapper:
    def __init__(
            self,
            data_url: str,
            method_url: str,
            data_subject_super_class_uris: List[URIRef] = [InformtionContentEntity,TemporalRegionClass],
            mapping_predicate_uri: URIRef = ContentToBearingRelation,
            method_object_super_class_uris: List[URIRef] = [OA.Annotation,CSVW.Column],
            objects=None,
            subjects=None,
            maplist=list()
            ):
        """Constructor"""
        self.data_url = data_url
        self.method_url = method_url
        self.mapping_predicate_uri=mapping_predicate_uri
        #file_data, file_name =open_file(data_url)
        if not objects:
            self.objects = get_methode_ices(self.method_url,data_subject_super_class_uris)
        else:
            self.objects = objects
        if not subjects:
            self.subjects = get_data_informationbearingentities(
                self.data_url,method_object_super_class_uris)
        else:
            self.subjects = subjects
        self.maplist = maplist

    def __str__(self):
        return f"Mapper: {self.data_url} {self.method_url}"

    def to_yaml(self):
        # return filename and yaml file content
        return get_mapping_output(
            self.data_url,
            self.method_url,
            self.maplist,
            self.subjects,
            self.mapping_predicate_uri
            )


def get_data_informationbearingentities(data_url,entity_classes: List[URIRef]):
    data=load_graph(data_url)
    info_lines = {s.split('/')[-1]: {
        'uri': str(s),
        'text':
            str(data.value(s, RDFS.label)) if
            data.value(s, RDFS.label) else
            data.value(s, CSVW.title),
        'property': 'label' if data.value(s, RDFS.label) else
        'titles'}
        for s, p, o in data.triples((None,  RDF.type, None)) if
        o in entity_classes
        }
    return info_lines


def get_methode_ices(method_url,entity_classes: List[URIRef]):
    # get all types of classes for the given list of superclasses 
    subclasses=[get_all_sub_classes(superclass) for superclass in entity_classes]
    class_list=[item for sublist in subclasses for item in sublist]
    method=load_graph(method_url)
    ices = {s.split('/')[-1]: s for s, p,
            o in method.triples((None,  RDF.type, None)) if o in class_list}
    return ices


def get_mapping_output(data_url: str, method_url: str, map_list: List, subjects_dict: dict, mapping_predicate_uri: URIRef):
    g=Graph()
    g.bind('method', Namespace( method_url+'/'))
    g.bind('data_url', Namespace( method_url+'/'))
    g.bind('obo', OBO)
    
    result = OrderedDict()
    result['prefixes'] = {'obo': str(OBO),
                          'data': data_url+'/',
                          'method': method_url+'/'}
    result['base'] = 'http://purl.matolab.org/mseo/mappings/'
    # data_file should be url at best
    result['sources'] = {
        'data_notes': {
          'access': data_url,
          'referenceFormulation': 'jsonpath',
          'iterator': '$.notes[*]'
          },
        'data_columns': {
          'access': data_url,
          'referenceFormulation': 'jsonpath',
          'iterator': '$.tableSchema.columns[*]'
          },
        }
    result['mappings'] = OrderedDict()


    for ice_key, il_id in map_list:
        _il = subjects_dict[il_id]
        lookup_property = '$({})'.format(_il['property'])
        compare_string = str(_il['text'])

        result['mappings'][ice_key] = OrderedDict({
          'sources': ['data_notes', 'data_columns'],
          's': 'data:$(@id)',
          'condition': {
              'function': 'equal',
              'parameters': [
                    ['str1', lookup_property],
                    ['str2', compare_string],
                ],
              },
          # 'po':[['obo:0010002', 'method:'+str(mapping[0]).split('/')[-1]],]
          'po': [[mapping_predicate_uri.n3(g.namespace_manager), 'method:'+ice_key+'~iri'], ]
          })
        # self.mapping_yml=result
    filename = data_url.split('/')[-1].split('-metadata')[0]+'-map.yaml'
    data = dump(result, Dumper=Dumper)
    return filename, data
