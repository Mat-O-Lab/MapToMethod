from re import search as re_search
import ssl
from collections import OrderedDict
from pydantic import AnyUrl
from typing import Dict, List, Tuple

from yaml import Loader, Dumper, dump
from yaml.representer import SafeRepresenter
from yaml.resolver import BaseResolver

from rdflib import Graph, URIRef, Namespace
from rdflib.namespace import RDF, RDFS
from rdflib.plugins.sparql import prepareQuery
from rdflib.util import guess_format
import github
from urllib.parse import urlparse, unquote
import gc

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

def load_graph(url: AnyUrl,graph: Graph=Graph()) -> Graph:
    """_summary_

    Args:
        url (AnyUrl): Url to an web ressource
        graph (Graph, optional): Existing Rdflib Graph object to parse data to. Defaults to Graph().

    Returns:
        Graph: Rdflib graph Object
    """
    parsed_url=urlparse(url)
    format=guess_format(parsed_url.path)
    #print(url,format)
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
    results = list(
        mseo_graph.query(
                sub_classes,
                initBindings={'parent': superclass},
                initNs={'cco': CCO, 'mseo': MSEO},
                ),
            )
    classes = [result[0] for result in results]
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
        return methods
    else:
        return None

class Mapper:
    def __init__(
            self,
            data_url: AnyUrl,
            method_url: AnyUrl,
            data_subject_super_class_uris: List[URIRef] = [InformtionContentEntity,TemporalRegionClass],
            mapping_predicate_uri: URIRef = ContentToBearingRelation,
            method_object_super_class_uris: List[URIRef] = [OA.Annotation,CSVW.Column],
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
    #methods for context managers
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_value, traceback):
        yield (exc_type, exc_value)
        # del self
        # gc.collect()
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
    method=load_graph(method_url)
    ices = {s.split('/')[-1]: s for s, p,
            o in method.triples((None,  RDF.type, None)) if o in class_list}
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
        dict: _description_
    """
    g=Graph()
    g.bind('method', Namespace( method_url+'/'))
    g.bind('data_url', Namespace( method_url+'/'))
    g.bind('obo', OBO)
    print(map_list)
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
    #data = dump(result, Dumper=Dumper)
    data=result
    return {'filename':filename, 'filedata': data}
