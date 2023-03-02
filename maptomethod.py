from re import search as re_search
from re import split as re_split

import ssl
from collections import OrderedDict
from pydantic import AnyUrl
from typing import Dict, List, Tuple

from yaml import Loader, Dumper, dump
from yaml.representer import SafeRepresenter
from yaml.resolver import BaseResolver

from rdflib import Graph, URIRef, Namespace
from rdflib.namespace import CSVW, RDF, RDFS, DefinedNamespaceMeta
import logging
import sys, inspect
            

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

BFO = Namespace('http://purl.obolibrary.org/obo/')
BFO_URL = "http://purl.obolibrary.org/obo/bfo.owl"
MSEO_URL = './ontologies/mseo.ttl'
CCO_URL = './ontologies/cco.ttl'
MSEO = Namespace('https://purl.matolab.org/mseo/mid')
CCO = Namespace('http://www.ontologyrepository.com/CommonCoreOntologies/')
OA = Namespace('http://www.w3.org/ns/oa#')

def get_rdflib_Namespaces() -> dict:
    """Get all the Namespaces available in rdflib.namespace.

    Returns:
        dict: Namespaces Dict with prefix as key a dict with uri and src as value.  
    """
    class_dict={}
    for name, obj in inspect.getmembers(sys.modules['rdflib.namespace']):
        if inspect.isclass(obj):
            if isinstance(obj , DefinedNamespaceMeta):
                try:
                    class_dict[str(name)]={'uri': str(obj), 'src': str(obj)}
                except:
                    pass
    return class_dict

def parse_graph(url: AnyUrl, graph: Graph) -> Graph:
    """Parse a Graph from web url to rdflib graph object

    Args:
        url (AnyUrl): Url to an web ressource
        graph (Graph): Existing Rdflib Graph object to parse data to.

    Returns:
        Graph: Rdflib graph Object
    """
    parsed_url=urlparse(url)
    format=guess_format(parsed_url.path)
    if not format:
        format='xml'
    #print(parsed_url.geturl())
    graph.parse(unquote(parsed_url.geturl()), format=format)
    return graph

def get_all_sub_classes(superclass: URIRef) -> List[URIRef]:
    """Gets all subclasses of a given class.

    Args:
        superclass (URIRef): Rdflib URIRef of the superclass

    Returns:
        List[URIRef]: List of all subclasses
    """
    ontology_url=re_split(r'/|#', superclass[::-1],maxsplit=1)[-1][::-1]
    #lookup in ontologies
    result=[ (key, item['src']) for key,item in ontologies.items() if ontology_url in item['uri']]
    if result:
        ontology_url=result[0][1]
    logging.info('Fetching all subclasses of {} in ontology at {}'.format(superclass,ontology_url))
    ontology=parse_graph(ontology_url, graph = Graph())
    results = list(
        ontology.query(
                sub_classes,
                initBindings={'parent': superclass},
                #initNs={'cco': CCO, 'mseo': MSEO},
                ),
            )
    classes = [result[0] for result in results]
    logging.info('Found following subclasses of {}: {}'.format(superclass,classes))
    return classes


def get_methods() -> Dict:
    """Get all ttl filenames and URLs in the MSEO methods folder.

    Returns:
        Dict: Dict with method name aas key and url to file as value
    """
    mseo_repo = github.Github().get_repo("Mat-O-Lab/MSEO")
    folder_index = mseo_repo.get_contents("methods")
    #print(folder_index)
    if folder_index:
        methods_urls = [
            method.download_url for method in folder_index if method.download_url and method.download_url.endswith('ttl')]
        methods = {re_search('[^/\\&\?]+\.\w{3,4}(?=([\?&].*$|$))', url)
                   [0].split('.')[0]: url for url in methods_urls}
    else:
        methods={}
    logging.info('Following methods are available as select: {}'.format(methods))
    return methods

ontologies=get_rdflib_Namespaces()
ontologies['BFO']={'uri': str(BFO), 'src': BFO_URL}
ontologies['MSEO']={'uri': str(MSEO), 'src': MSEO_URL}
ontologies['CCO']={'uri': str(CCO), 'src': CCO_URL}
ontologies['OA']={'uri': str(OA), 'src': OA}

InformtionContentEntity = CCO.InformationContentEntity
TemporalRegionClass = BFO.BFO_0000008
ContentToBearingRelation = BFO.RO_0010002

class Mapper:
    def __init__(
            self,
            data_url: AnyUrl,
            method_url: AnyUrl,
            method_object_super_class_uris: List[URIRef] = [InformtionContentEntity,TemporalRegionClass],
            mapping_predicate_uri: URIRef = ContentToBearingRelation,
            data_subject_super_class_uris: List[URIRef] = [OA.Annotation,CSVW.Column],
            subjects: List[URIRef]=[],
            objects: List[URIRef]=[],
            maplist: List[Tuple[str, str]]=[]
            ):
        """Mapper Class for creating Rule based yarrrml mappings for data metadata to link to a knowledge graph.

        Args:
            data_url (AnyUrl): Url to metadata describing the data to link
            method_url (AnyUrl): Url to knowledgegraph describing context to link data to.
            data_subject_super_class_uris (List[URIRef], optional): List of rdflib URIRef objects defining classes to query for as subjects of the mapping rules. Defaults to [InformtionContentEntity,TemporalRegionClass].
            mapping_predicate_uri (URIRef, optional): Object property to use as predicate to link. Defaults to ContentToBearingRelation.
            method_object_super_class_uris (List[URIRef], optional): List of rdflib URIRef objects defining classes to query for as objects of the mapping rules. Defaults to [OA.Annotation,CSVW.Column].
            subjects (List[URIRef], optional): List of rdflib URIRef objects which are individuals in the data metadata. Defaults to [].
            objects (List[URIRef], optional): List of rdflib URIRef objects which are individuals in the knowledge grph. Defaults to [].
            maplist (List[Tuple[str, str]], optional): List of pairs of individual name of objects in knowledge graph and labels of indivuals in data metadata to create mapping rules for. Defaults to [].
        """
        logging.info('Following Namespaces available to Mapper: {}'.format(ontologies.keys()))
        self.data_url = data_url
        self.method_url = method_url
        self.mapping_predicate_uri=mapping_predicate_uri
        #file_data, file_name =open_file(data_url)
        if not objects:
            self.objects = get_methode_ices(self.method_url,method_object_super_class_uris)
        else:
            self.objects = objects
        if not subjects:
            self.subjects = get_data_informationbearingentities(
                self.data_url,data_subject_super_class_uris)
        else:
            self.subjects = subjects
        self.maplist = maplist
    #methods for context managers
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_value, traceback):
        yield (exc_type, exc_value)
    def __str__(self) -> str:
        """String representation

        Returns:
            str: String representation
        """
        return f"Mapper: {self.data_url} {self.method_url}"

    def to_yaml(self) -> dict:
        """Return filename and yarrrml yaml file content

        Returns:
            dict: Dict with keys filename, suggested mapping file name and filedata, yarrrml mapping file yaml content
        """
        return get_mapping_output(
            self.data_url,
            self.method_url,
            self.maplist,
            self.subjects,
            self.mapping_predicate_uri
            )
    def to_pretty_yaml(self) -> str:
        result=self.to_yaml()
        result['filedata'] = dump(result['filedata'], Dumper=Dumper)
        return result



def get_data_informationbearingentities(data_url: AnyUrl, entity_classes: List[URIRef]) -> dict:
    """Get all named individuals at data_url location that are of any type in entitty_classes.

    Args:
        data_url (AnyUrl): Url to metadata to use
        entity_classes (List[URIRef]): List of rdflib URIRef as class types to query for.

    Returns:
        dict: Dict with short entity IRI as key
    """
    data=parse_graph(data_url, graph = Graph())
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


def get_methode_ices(method_url: AnyUrl, entity_classes: List[URIRef]) -> dict:
    """Get all types of classes for the given list of superclasses 

    Args:
        method_url (AnyUrl): Url to knowledge graph to use
        entity_classes (List[URIRef]): List of rdflib URIRef as class types to query for.

    Returns:
        dict: Dict with short entity IRI as key
    """
    subclasses=[get_all_sub_classes(superclass) for superclass in entity_classes]
    class_list=[item for sublist in subclasses for item in sublist]
    method=parse_graph(method_url, graph = Graph())
    # filters out entities not belonging to the graph directly
    ices = {s.split('/')[-1]: s for s, p,
            o in method.triples((None,  RDF.type, None)) if o in class_list}
    # filter for entities belonging to the graph only
    return ices

def get_mapping_output(data_url: AnyUrl, method_url: AnyUrl, map_list: List, subjects_dict: dict, mapping_predicate_uri: URIRef) -> dict:
    """Get yaml definging the yarrrml mapping rules.

    Args:
        data_url (AnyUrl): Url to data metadata to use
        method_url (AnyUrl): Url to knowledge graph to use
        map_list (List): List of pairs of individual name of objects in knowledge graph and labels of indivuals in data metadata to create mapping rules for.
        subjects_dict (dict): Dict of subjects to create mapping rules for with short entity IRI as key
        mapping_predicate_uri (URIRef): Object property to use as predicate to link

    Returns:
        dict: Dict with key filename with value the sugested mapping filenaem and filedata with value the string content of the generated yarrrml yaml file.
    """
    g=Graph()
    g.bind('method', Namespace( method_url+'/'))
    g.bind('data_url', Namespace( data_url+'/'))
    g.bind('bfo', BFO)
    prefixes={prefix: str(url) for (prefix, url) in g.namespaces()}
    result = OrderedDict()
    result['prefixes'] = prefixes
    result['base'] = 'http://purl.matolab.org/mseo/mappings/'
    # data_file should be url at best
    result['sources'] = {
        'data_entities': {
          'access': data_url,
          'referenceFormulation': 'jsonpath',
          'iterator': '$..[*]'
          }
        }
    result['mappings'] = OrderedDict()


    for ice_key, il_id in map_list:
        _il = subjects_dict[il_id]
        lookup_property = '$({})'.format(_il['property'])
        compare_string = str(_il['text'])

        result['mappings'][ice_key] = OrderedDict({
          'sources': ['data_entities'],
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
    data=result
    return {'filename':filename, 'filedata': data}
