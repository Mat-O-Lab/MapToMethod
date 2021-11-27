from rdflib import Graph, URIRef, Namespace
from rdflib.namespace import DC, OWL, RDF, RDFS, XSD
from rdflib.plugins.sparql import prepareQuery
import github
from re import search as re_search
import base64
#from ruamel import yaml
import yaml
#import requests
from urllib.request import urlopen

#disable ssl verification
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

# try to use LibYAML bindings if possible
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper
from yaml.representer import SafeRepresenter
_mapping_tag = yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG

from collections import OrderedDict
def dict_representer(dumper, data):
    return dumper.represent_dict(data.items())
def dict_constructor(loader, node):
    return OrderedDict(loader.construct_pairs(node))

Dumper.add_representer(OrderedDict, dict_representer)
Loader.add_constructor(_mapping_tag, dict_constructor)

Dumper.add_representer(str, SafeRepresenter.represent_str)


mseo = Namespace('https://purl.matolab.org/mseo/mid/')
cco = Namespace('http://www.ontologyrepository.com/CommonCoreOntologies/')
csvw = Namespace('http://www.w3.org/ns/csvw#')
sub_classes = prepareQuery(
  "SELECT ?entity WHERE {?entity rdfs:subClassOf* ?parent}",
  initNs ={"rdf": RDF,"rdsf": RDFS}
)
#github credatials
mseo_repo=github.Github().get_repo("Mat-O-Lab/MSEO")
res_repo=github.Github().get_repo("Mat-O-Lab/resources")

#github credatials
mseo_repo=github.Github().get_repo("Mat-O-Lab/MSEO")
res_repo=github.Github().get_repo("Mat-O-Lab/resources")

def get_methods():
  #get all ttl files from methods folder of mseo repo, create dict with method name key and url to file
  repo = mseo_repo
  methods_urls=[method.download_url for method in repo.get_contents("methods") if method.download_url.endswith('ttl')]
  methods={re_search('[^/\\&\?]+\.\w{3,4}(?=([\?&].*$|$))', url)[0].split('.')[0]: url for url in methods_urls}
  return methods

class Mapper:
    def __init__(self, data_url, method_url,ICEs=None,InfoLines=None,maplist=list()):
        self.data_url = data_url
        self.method_url = method_url
        if not ICEs:
            self.ICEs=get_methode_ICE(self.method_url)
        else:
            self.ICEs=ICEs
        if not InfoLines:
            self.InfoLines=get_data_Info(self.data_url)
        else:
            self.InfoLines=InfoLines
        self.maplist=maplist
    def __str__(self):
        return f"Mapper: {self.data_url} {self.method_url}"
    def to_yaml(self):
        #return filename and yaml file content
        return get_mapping_output(self.data_url,self.method_url,self.maplist,self.InfoLines)

def get_data_Info(data_url):
    # all Information Line individuals
    InformationLineClass = URIRef("http://www.ontologyrepository.com/CommonCoreOntologies/InformationLine")
    ColumnClass=URIRef("http://www.w3.org/ns/csvw#Column")
    data = Graph()
    try:
        data.parse(location=data_url,format='json-ld')
    except:
        raise ValueError('url target is not a valid json-ld file')
    else:
        InfoLines={s.split('/')[-1]: {'uri': str(s), 'text': str(data.label(s)) if data.label(s) else data.value(s,csvw.title), 'property': 'label' if data.label(s) else 'titles'} for s, p, o in data.triples((None,  RDF.type , None)) if o in (InformationLineClass,ColumnClass)}
        return InfoLines

def get_methode_ICE(method_url):
  # get all the ICE individuals in the method graph
  ICE_classes=get_ICE_classes()
  TR_classes=get_temporal_region_classes()
  class_list=ICE_classes+TR_classes
  method = Graph()
  method.parse(method_url,format='turtle')
  ICEs={s.split('/')[-1]: s for s, p, o in method.triples((None,  RDF.type , None)) if o in class_list}
  return ICEs

def get_mapping_output(data_url,method_url,map_list,infolines_dict):
    result=OrderedDict()
    result['prefixes']={'obo': 'http://purl.obolibrary.org/obo/',
                        'data': data_url+'/',
                        'method': method_url+'/'}
    result['base']='http://purl.matolab.org/mseo/mappings/'
    #data_file should be url at best
    result['sources']={
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
    result['mappings']={}
    print(map_list)
    for ice_key, il_id in map_list:
        il=infolines_dict[il_id]
        lookup_property='$({})'.format(il['property'])
        compare_string=str(il['text'])

        result['mappings'][ice_key]=OrderedDict({
          'sources': ['data_notes','data_columns'],
          's': 'data:$(@id)',
          'condition': {
              'function': 'equal',
              'parameters': [['str1', lookup_property],['str2', compare_string]]
              },
          #'po':[['obo:0010002', 'method:'+str(mapping[0]).split('/')[-1]],]
          'po':[['obo:0010002', method_url+'/'+ice_key],]
          })
        #self.mapping_yml=result
    mapping_filename=data_url.split('/')[-1].split('-metadata')[0]+'-map.yaml'
    mapping_data=yaml.dump(result,Dumper=Dumper)
    return mapping_filename, mapping_data

def get_ICE_classes():
  g=Graph()
  g.parse('https://raw.githubusercontent.com/CommonCoreOntology/CommonCoreOntologies/master/cco-merged/MergedAllCoreOntology-v1.3-2021-03-01.ttl',format='turtle')
  #mseo = Graph()
  g.parse("https://purl.matolab.org/mseo/mid",format='xml')
  InformtionContentEntity = URIRef("http://www.ontologyrepository.com/CommonCoreOntologies/InformationContentEntity")
  #mseo_ICE=list(mseo.query(sub_classes, initBindings={'parent': InformtionContentEntity}, initNs={ 'mseo': mseo }))
  g_ICE=list(g.query(sub_classes, initBindings={'parent': InformtionContentEntity}, initNs={ 'cco': cco , 'mseo': mseo }))
  ICE_classes=[result[0] for result in g_ICE]#+[result[0] for result in mseo_ICE]
  return ICE_classes

def get_temporal_region_classes():
  g=Graph()
  g.parse('https://raw.githubusercontent.com/CommonCoreOntology/CommonCoreOntologies/master/cco-merged/MergedAllCoreOntology-v1.3-2021-03-01.ttl',format='turtle')
  #mseo = Graph()
  g.parse("https://purl.matolab.org/mseo/mid",format='xml')
  TemporalRegionClass = URIRef("http://purl.obolibrary.org/obo/BFO_0000008")
  #mseo_ICE=list(mseo.query(sub_classes, initBindings={'parent': InformtionContentEntity}, initNs={ 'mseo': mseo }))
  g_TR=list(g.query(sub_classes, initBindings={'parent': TemporalRegionClass}, initNs={ 'cco': cco , 'mseo': mseo }))
  TR_classes=[result[0] for result in g_TR]#+[result[0] for result in mseo_ICE]
  return TR_classes
