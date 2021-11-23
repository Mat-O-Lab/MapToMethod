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

Dumper.add_representer(str,
                       SafeRepresenter.represent_str)


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

class Mapper:
    def __init__(self, data_url, method_url):
        self.data_url = data_url
        self.method_url = method_url
        self.methode_ICEs=get_methode_ICE(self.method_url)
        self.info_lines=self.get_data_Info()
        self.info_lines=[(value, label) for label, value in self.info_lines.items()]
        self.info_lines.insert(0,(None,'None'))
        self.map_elements=list()
    def __str__(self):
        return f"Mapper: {self.data_url} {self.method_url}"
    def get_data_Info(self):
        # all Information Line individuals
        InformationLineClass = URIRef("http://www.ontologyrepository.com/CommonCoreOntologies/InformationLine")
        ColumnClass=URIRef("http://www.w3.org/ns/csvw#Column")
        data = Graph()
        try:
            data.parse(location=self.data_url,format='json-ld')
        except:
            raise ValueError('url target is not a valid json-ld file')
        else:
            InfoLines={s.split('/')[-1]: s for s, p, o in data.triples((None,  RDF.type , None)) if o in (InformationLineClass,ColumnClass)}
            return InfoLines

def get_methods():
  #get all ttl files from methods folder of mseo repo, create dict with method name key and url to file
  repo = mseo_repo
  methods_urls=[method.download_url for method in repo.get_contents("methods") if method.download_url.endswith('ttl')]
  methods={re_search('[^/\\&\?]+\.\w{3,4}(?=([\?&].*$|$))', url)[0].split('.')[0]: url for url in methods_urls}
  return methods

def get_mappings():
  #get all ttl files from methods folder of mseo repo, create dict with method name key and url to file
  print('input github access token')
  repo = res_repo
  urls=[file.download_url for file in repo.get_contents("mappings") if file.download_url.endswith('yaml')]
  mappings={re_search('[^/\\&\?]+\.\w{3,4}(?=([\?&].*$|$))', url)[0].split('.')[0]: url for url in urls}
  return mappings

def save_mapping(filename, data):
  repo = github.Github(getpass.getpass()).get_repo("Mat-O-Lab/resources")
  #repo = github.Github().get_repo("Mat-O-Lab/resources")

  filename='test.yaml'
  data='test'
  # Upload to github
  git_prefix = 'mappings/'
  git_file = git_prefix + filename
  mapping_files=[value.split('/')[-1] for key,value in get_mappings().items()]
  print(filename in mapping_files)
  if filename in mapping_files:
      contents = repo.get_contents(git_file)
      print(contents,git_file)
      repo.update_file(contents.path, "committing mapping", data, contents.sha, branch="main")
      print(git_file + ' UPDATED in '+ repo.full_name)
  else:
      print(git_file)
      repo.create_file(git_file, "committing mapping", data, branch="main")
      print(git_file + ' CREATED in '+ repo.full_name)

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

def get_methode_ICE(method_url):
  # get all the ICE individuals in the method graph
  ICE_classes=get_ICE_classes()
  TR_classes=get_temporal_region_classes()
  class_list=ICE_classes+TR_classes
  method = Graph()
  method.parse(method_url,format='turtle')
  ToMapTo={s.split('/')[-1]: s for s, p, o in method.triples((None,  RDF.type , None)) if o in class_list}
  return ToMapTo

def get_data_Info(data_string):
  # all Information Line individuals
  InformationLineClass = URIRef("http://www.ontologyrepository.com/CommonCoreOntologies/InformationLine")
  ColumnClass=URIRef("http://www.w3.org/ns/csvw#Column")
  data = Graph()
  data.parse(data_string,format='json-ld')
  InfoLines={s.split('/')[-1]: s for s, p, o in data.triples((None,  RDF.type , None)) if o in (InformationLineClass,ColumnClass)}
  return InfoLines

# class MapDialog():
#     def __init__(self, csv_meta_url='', method_url=''):
#       self.csv_meta_url = csv_meta_url
#       self.method_url = method_url
#       self.methods=get_methods()
#     def _create_initial_widgets(self):
#       self.meta_url_widget=widgets.Text(
#           value='',
#           placeholder='put ur url to a *-metadata.json here',
#           description='Url:',
#           disabled=False
#           )
#       self.uploader = widgets.FileUpload(accept='',  # Accepted file extension e.g. '.txt', '.pdf', 'image/*', 'image/*,.pdf'
#                                          multiple=False,  # True to accept multiple files upload else False
#                                          description='Upload'
#                                          )
#       self.clear_button = widgets.Button(description='Clear!', layout=widgets.Layout(width='100px'));
#       self.file_dialog= widgets.HBox([widgets.Label(value="File:"), self.meta_url_widget ,self.uploader,self.clear_button])
#       self.clear_button.on_click(self._on_clear)
#       self.data_type_sel=widgets.Box(
#           [
#             widgets.Label(value='primary or secondary data:'),
#             widgets.RadioButtons(
#                 options=[
#                         'primary - the data describes one experiment with one specimen',
#                         'secondary - data table with results of multiple experiments',
#                         ],
#                 layout={'width': 'max-content'}
#                 )
#             ]
#         )
#       self.method_sel = widgets.Dropdown(
#           options=list(self.methods.keys()),
#           #value=list(methods.items())[0][1],
#           description='method:',
#           disabled=False,
#           )
#       self.out = widgets.Output()  # this is the output widget in which the df is displayed
#       self.start_mapping_button = widgets.Button(description='Start Mapping!', layout=widgets.Layout(width='200px'));
#       self.start_mapping_button.on_click(self._start_mapping)
#     def _on_clear(self,button):
#       self.uploader.value.clear()
#       self.uploader._counter = 0
#     def _start_mapping(self,button):
#       # "linking function with output"
#       with self.out:
#       # what happens when we press the button
#         clear_output()
#         if not (self.meta_url_widget.value or self.uploader.value.keys()):
#           print('pls upload a file first or insert a url')
#           return
#         if self.meta_url_widget.value:
#           self.csv_meta_url=self.meta_url_widget.value
#           file_name=self.csv_meta_url.split('/')[-1]
#           #response=requests.get(self.csv_meta_url)
#           #self.file_data = response.text
#           self.file_data = urlopen(self.csv_meta_url).read()
#         else:
#           input_file=self.uploader.value[list(self.uploader.value.keys())[0]]
#           self.csv_meta_url=input_file['metadata']['name']
#           file_name = input_file['metadata']['name']
#           self.file_data = input_file['content']
#           #print(file_name,self.methods[self.method_sel.value])
#         self.method_url=self.methods[self.method_sel.value]
#         self.methode_ICEs=get_methode_ICE(self.method_url)
#         self.data_info=get_data_Info(self.file_data)
#         info_lines=[(label, value) for label, value in self.data_info.items()]
#         info_lines.insert(0,('None',None))
#         self.map_elements=list()
#         for id, url in self.methode_ICEs.items():
#           self.map_elements.append(widgets.HBox([
#                                             widgets.Label(id),
#                                             widgets.Dropdown(
#                                                 options=info_lines,
#                                                 #value='auto',
#                                                 #description='separator:',
#                                                 disabled=False,)
#                                             ]))
#         #print(map_elements)
#         display(widgets.VBox(self.map_elements))
#         self.create_mapping_button = widgets.Button(description='Create Mapping!', layout=widgets.Layout(width='200px'));
#         buttons= widgets.HBox([self.create_mapping_button,])
#         self.create_mapping_button.on_click(self._create_mapping)
#         display(buttons)
#     def _create_mapping(self,button):
#       # "linking function with output"
#       with self.out:
#         clear_output()
#         map_list=[element.children for element in self.map_elements]
#         map_list=[(self.methode_ICEs[widget_label.value],select.value) for (widget_label,select) in map_list if select.value]
#         #print(map_list)
#         data = Graph()
#
#         data.parse(self.file_data,format='json-ld')
#         #print(data)
#         result=OrderedDict()
#         result['prefixes']={'obo': 'http://purl.obolibrary.org/obo/',
#                             'data': self.csv_meta_url+'/',
#                             'method': self.method_url+'/'}
#         result['base']='http://purl.matolab.org/mseo/mappings/'
#         #data_file should be url at best
#         result['sources']={
#             'data_notes': {
#               'access': self.csv_meta_url,
#               'referenceFormulation': 'jsonpath',
#               'iterator': '$.notes[*]'
#               },
#             'data_columns': {
#               'access': self.csv_meta_url,
#               'referenceFormulation': 'jsonpath',
#               'iterator': '$.tableSchema.columns[*]'
#               },
#             }
#         result['mappings']={}
#
#         for mapping in map_list:
#           #print(mapping)
#           #print(data.label(mapping[1]))
#           if str(data.label(mapping[1])):
#             lookup_property='$(label)'
#             compare_string=str(data.label(mapping[1]))
#           elif str(data.value(mapping[1],csvw.title)):
#             lookup_property='$(titles)'
#             compare_string=str(data.value(mapping[1],csvw.title))
#           else:
#             continue
#           result['mappings'][str(mapping[0]).split('/')[-1]]=OrderedDict({
#               'sources': ['data_notes','data_columns'],
#               's': 'data:$(@id)',
#               'condition': {
#                   'function': 'equal',
#                   'parameters': [['str1', lookup_property],['str2', compare_string]]
#                   },
#               #'po':[['obo:0010002', 'method:'+str(mapping[0]).split('/')[-1]],]
#               'po':[['obo:0010002', str(mapping[0])],]
#           })
#         self.mapping_yml=result
#         #print(yaml.dump(result, Dumper=Dumper,default_flow_style=False))
#         print(yaml.dump(result, Dumper=Dumper))
#
#         mapping_filename=self.csv_meta_url.split('/')[-1].split('-metadata')[0]+'-map.yaml'
#         #mapping_data=yaml.dump(result, default_flow_style=False)
#         mapping_data=yaml.dump(result, Dumper=Dumper)
#
#         res = mapping_data
#         b64 = base64.b64encode(res.encode())
#         payload = b64.decode()
#         button_html = '''<html>
#         <head>
#         <meta name="viewport" content="width=device-width, initial-scale=1">
#         </head>
#         <body>
#         <a download="{filename}" href="data:text/json;base64,{payload}" download>
#         <button class="p-Widget jupyter-widgets jupyter-button widget-button mod-warning">{title}</button>
#         </a>
#         </body>
#         </html>
#         '''
#         download_button = button_html.format(title='Download File',payload=payload,filename=mapping_filename)
#         #buttons= widgets.HBox([create_mapping,widgets.HTML(download_button)])
#         display(widgets.HTML(download_button))
#
#     def display_widgets(self):
#         self._create_initial_widgets()
#         display(widgets.VBox(
#                     [
#                       self.file_dialog,
#                       self.data_type_sel,
#                       self.method_sel,
#                       self.start_mapping_button,
#                       self.out
#                     ]
#                 )
#         )
