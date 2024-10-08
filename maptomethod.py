import inspect
import logging
import sys
from collections import OrderedDict
from re import search as re_search
from re import split as re_split
from tokenize import Name
from typing import Dict, List, Tuple
from urllib.parse import unquote, urlparse, urljoin
from urllib.request import urlopen, pathname2url
import requests
from fastapi import HTTPException
import os
import github
from pydantic import AnyUrl
from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import CSVW, RDF, RDFS, DefinedNamespaceMeta
from rdflib.plugins.sparql import prepareQuery
from rdflib.util import guess_format
from yaml import Dumper, Loader, dump
from yaml.representer import SafeRepresenter
from yaml.resolver import BaseResolver

SSL_VERIFY = os.getenv("SSL_VERIFY", "True").lower() in ("true", "1", "t")
if not SSL_VERIFY:
    requests.packages.urllib3.disable_warnings()


def dict_representer(dumper, data):
    return dumper.represent_dict(data.items())


def dict_constructor(loader, node):
    return OrderedDict(loader.construct_pairs(node))


Dumper.add_representer(OrderedDict, dict_representer)
Loader.add_constructor(BaseResolver.DEFAULT_MAPPING_TAG, dict_constructor)
Dumper.add_representer(str, SafeRepresenter.represent_str)

sub_classes = prepareQuery("SELECT ?entity WHERE {?entity rdfs:subClassOf* ?parent}")

BFO = Namespace("http://purl.obolibrary.org/obo/")
BFO_URL = "http://purl.obolibrary.org/obo/bfo.owl"
IOF_URL = "./ontologies/iof.rdf"
IOF = Namespace("https://spec.industrialontologies.org/ontology/core/Core/")
IOF_QUAL_URL = (
    "https://github.com/iofoundry/ontology/raw/'qualities'/qualities/qualities.rdf"
)
IOF_QUAL = Namespace("https://spec.industrialontologies.org/ontology/qualities/")
IOF_MAT_URL = (
    "https://github.com/iofoundry/ontology/raw/materials/materials/Materials.rdf"
)
IOF_MAT = Namespace(
    "https://spec.industrialontologies.org/ontology/materials/Materials/"
)

OA = Namespace("http://www.w3.org/ns/oa#")
OA_URL = "http://www.w3.org/ns/oa.ttl"


def strip_namespace(term: URIRef) -> str:
    """Strip the namespace from full URI

    Args:
        term (URIRef): A RDFlib Term

    Returns:
        str: short IRI
    """
    return re_split(r"/|#|:", term[::-1], maxsplit=1)[0][::-1]


def get_rdflib_Namespaces() -> dict:
    """Get all the Namespaces available in rdflib.namespace.

    Returns:
        dict: Namespaces Dict with prefix as key a dict with uri and src as value.
    """
    class_dict = {}
    for name, obj in inspect.getmembers(sys.modules["rdflib.namespace"]):
        if inspect.isclass(obj):
            if isinstance(obj, DefinedNamespaceMeta):
                try:
                    class_dict[str(name)] = {"uri": str(obj), "src": str(obj)}
                except:
                    pass
    return class_dict


ontologies = get_rdflib_Namespaces()
ontologies["BFO"] = {"uri": str(BFO), "src": BFO_URL}
ontologies["OA"] = {"uri": str(OA), "src": OA_URL}
ontologies["CSVW"]["src"] = "https://www.w3.org/ns/csvw.ttl"
ontologies["IOF"] = {"uri": str(IOF), "src": IOF_URL}
ontologies["IOF-MAT"] = {"uri": str(IOF_MAT), "src": IOF_MAT_URL}
ontologies["IOF-QUAL"] = {"uri": str(IOF_QUAL), "src": IOF_QUAL_URL}


def open_file(uri: AnyUrl, authorization=None) -> Tuple["filedata":str, "filename":str]:
    try:
        uri_parsed = urlparse(uri)
        # print(uri_parsed, urljoin('file:', pathname2url(os.path.abspath(uri_parsed.path))))
    except:
        raise HTTPException(
            status_code=400,
            detail=uri + " is not an uri - if local file add file:// as prefix",
        )
    else:
        if uri_parsed.path.startswith("."):
            # is local file path create a proper file url
            uri_parsed = urlparse(
                urljoin("file:", pathname2url(os.path.abspath(uri_parsed.path)))
            )
        filename = unquote(uri_parsed.path).rsplit("/download/upload")[0].split("/")[-1]
        if uri_parsed.scheme in ["https", "http"]:
            # r = urlopen(uri)
            s = requests.Session()
            s.verify = SSL_VERIFY
            s.headers.update({"Authorization": authorization})
            r = s.get(uri, allow_redirects=True, stream=True)
            # print(r.content)
            if r.status_code != 200:
                # logging.info(r.content)
                raise HTTPException(
                    status_code=r.status_code, detail="cant get file at {}".format(uri)
                )
            filedata = r.content
            # charset=r.info().get_content_charset()
            # if not charset:
            #     charset='utf-8'
            # filedata = r.read().decode(charset)
        elif uri_parsed.scheme == "file":
            filedata = open(unquote(uri_parsed.path), "rb").read()
        else:
            raise HTTPException(
                status_code=400, detail="unknown scheme {}".format(uri_parsed.scheme)
            )
        return filedata, filename


def get_all_sub_classes(superclass: URIRef, authorization=None) -> List[URIRef]:
    """Gets all subclasses of a given class.

    Args:
        superclass (URIRef): Rdflib URIRef of the superclass

    Returns:
        List[URIRef]: List of all subclasses
    """
    if not str(superclass):
        return []
    ontology_url = re_split(r"/|#", superclass[::-1], maxsplit=1)[-1][::-1]
    # lookup in ontologies
    result = [
        (key, item["src"])
        for key, item in ontologies.items()
        if ontology_url in item["uri"]
    ]
    # print(ontology_url,result)
    if result:
        ontology_url = result[0][1]
        logging.info(
            "Fetching all subclasses of {} in ontology at {}".format(
                superclass, ontology_url
            )
        )
        onto_data, onto_name = open_file(ontology_url, authorization)
        ontology = Graph()
        # parse template and add mapping results
        ontology.parse(data=onto_data, format=guess_format(onto_name))
        results = list(
            ontology.query(
                sub_classes,
                initBindings={"parent": superclass},
                # initNs={'cco': CCO, 'mseo': MSEO},
            ),
        )
        # print(list(ontology[ : RDFS.subClassOf]))
        classes = [result[0] for result in results]
    else:
        classes = [
            superclass,
        ]
    logging.info("Found following subclasses of {}: {}".format(superclass, classes))
    return classes


def get_methods() -> Dict:
    """Get all ttl filenames and URLs in the MSEO methods folder.

    Returns:
        Dict: Dict with method name aas key and url to file as value
    """
    mseo_repo = github.Github().get_repo("Mat-O-Lab/MSEO")
    folder_index = mseo_repo.get_contents("methods")
    # print(folder_index)
    if folder_index:
        methods_urls = [
            method.download_url
            for method in folder_index
            if method.download_url and method.download_url.endswith("ttl")
        ]
        methods = {
            re_search("[^/\\&\?]+\.\w{3,4}(?=([\?&].*$|$))", url)[0].split(".")[0]: url
            for url in methods_urls
        }
    else:
        methods = {}
    logging.info("Following methods are available as select: {}".format(methods))
    return methods


# InformtionContentEntity = CCO.InformationContentEntity
InformtionContentEntity = IOF.InformationContentEntity
TemporalRegionClass = BFO.BFO_0000008
ContentToBearingRelation = BFO.RO_0010002


class Mapper:
    def __init__(
        self,
        data_url: str,
        method_url: str,
        use_template_rowwise: bool,
        method_object_super_class_uris: List[URIRef] = [
            InformtionContentEntity,
            TemporalRegionClass,
        ],
        mapping_predicate_uri: URIRef = ContentToBearingRelation,
        data_subject_super_class_uris: List[URIRef] = [OA.Annotation, CSVW.Column],
        subjects: List[URIRef] = [],
        objects: List[URIRef] = [],
        maplist: List[Tuple[str, str]] = [],
        authorization=None,
    ):
        """Mapper Class for creating Rule based yarrrml mappings for data metadata to link to a knowledge graph.

        Args:
            data_url (AnyUrl): Url to metadata describing the data to link
            method_url (AnyUrl): Url to knowledgegraph describing context to link data to.
            method_subject_super_class_uris (List[URIRef], optional): List of rdflib URIRef objects defining classes to query for as subjects of the mapping rules. Defaults to [InformtionContentEntity,TemporalRegionClass].
            mapping_predicate_uri (URIRef, optional): Object property to use as predicate to link. Defaults to ContentToBearingRelation.
            data_object_super_class_uris (List[URIRef], optional): List of rdflib URIRef objects defining classes to query for as objects of the mapping rules. Defaults to [OA.Annotation,CSVW.Column].
            subjects (List[URIRef], optional): List of rdflib URIRef objects which are individuals in the data metadata. Defaults to [].
            objects (List[URIRef], optional): List of rdflib URIRef objects which are individuals in the knowledge grph. Defaults to [].
            maplist (List[Tuple[str, str]], optional): List of pairs of individual name of objects in knowledge graph and labels of indivuals in data metadata to create mapping rules for. Defaults to [].
            authorization (str): Json strint to use as Authorization Header on requests to external urls.
        """
        logging.info(
            "Following Namespaces available to Mapper: {}".format(ontologies.keys())
        )
        self.data_url = data_url
        self.method_url = method_url
        self.use_template_rowwise = use_template_rowwise
        self.mapping_predicate_uri = mapping_predicate_uri
        self.authorization = authorization
        logging.debug("checking objects and subjects populated")
        # file_data, file_name =open_file(data_url)
        if not objects:
            self.objects, base_ns_objects = query_entities(
                self.method_url, method_object_super_class_uris, self.authorization
            )
            self.base_ns_objects = base_ns_objects
        else:
            self.objects = objects
            self.base_ns_objects = self.method_url + "/"
        logging.debug("namespace objects: " + self.base_ns_objects)

        if not subjects:
            self.subjects, base_ns_subjects = query_entities(
                self.data_url, data_subject_super_class_uris, self.authorization
            )
            self.base_ns_subjects = base_ns_subjects
        else:
            self.subjects = subjects
            self.base_ns_subjects = self.data_url + "/"
        logging.debug("namespace subjects: " + self.base_ns_subjects)

        self.maplist = maplist

    # methods for context managers
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
        results = get_mapping_output(
            self.data_url,
            self.use_template_rowwise,
            self.base_ns_subjects,
            self.base_ns_objects,
            self.maplist,
            self.subjects,
            self.mapping_predicate_uri,
        )
        return results

    def to_pretty_yaml(self) -> str:
        result = self.to_yaml()
        result["filedata"] = dump(result["filedata"], Dumper=Dumper, allow_unicode=True)
        return result


def query_entities(
    data_url: str, entity_classes: List[URIRef], authorization=None
) -> dict:
    """Get all named individuals at data_url location that are of any type in entity_classes.

    Args:
        data_url (AnyUrl): Url to metadata to use
        entity_classes (List[URIRef]): List of rdflib URIRef as class types to query for.

    Returns:
        dict: Dict with short entity IRI as key
    """
    subclasses = [
        get_all_sub_classes(superclass, authorization) for superclass in entity_classes
    ]
    class_list = [item for sublist in subclasses for item in sublist]
    logging.info(
        "query data at url: {}\nfor entitys classes: {}".format(data_url, class_list)
    )
    # fix for crude ckan url
    if data_url.endswith("/download/upload"):
        format = "json-ld"
    else:
        format = guess_format(data_url)
    data_data, data_name = open_file(data_url, authorization)
    data = Graph()
    # parse template and add mapping results
    data.parse(data=data_data, format=format)
    # find base iri if any
    # print(list(data.namespaces()))
    base_ns = None
    for ns_prefix, namespace in data.namespaces():
        if ns_prefix == "base":
            logging.debug("found base namespace: {}.".format(namespace))
            base_ns = namespace
            break
    if not base_ns:
        base_ns = data_url + "/"

    data_entities = dict()
    subjects = [
        s for s, p, o in data.triples((None, RDF.type, None)) if o in class_list
    ]
    for s in subjects:
        pos = [
            (p, o)
            for (p, o) in data.predicate_objects(s)
            if p in [RDFS.label, CSVW.name]
        ]
        # name=s.rsplit('/',1)[-1].rsplit('#',1)[-1]
        name = strip_namespace(s)
        print(s, pos)
        if pos:
            p, o = pos[0]
            data_entities[name] = {
                "uri": str(s),
                "property": strip_namespace(p),
                "text": str(o),
            }
        else:
            data_entities[name] = {"uri": str(s)}
    logging.info("query resuls: {}".format(data_entities))
    return data_entities, base_ns


def get_mapping_output(
    data_url: str,
    use_template_rowwise: bool,
    data_ns: str,
    method_ns: str,
    map_list: List,
    subjects_dict: dict,
    mapping_predicate_uri: URIRef,
) -> dict:
    """Get yaml definging the yarrrml mapping rules.

    Args:
        data_url (AnyUrl): Url to data metadata to use
        data_ns (AnyUrl): Namespace of the data entities to map
        method_ns (AnyUrl): Namespace of the method entities to relate to
        method_url (AnyUrl): Url to knowledge graph to use
        map_list (List): List of pairs of individual name of objects in knowledge graph and labels of indivuals in data metadata to create mapping rules for.
        subjects_dict (dict): Dict of subjects to create mapping rules for with short entity IRI as key
        mapping_predicate_uri (URIRef): Object property to use as predicate to link

    Returns:
        dict: Dict with key filename with value the sugested mapping filenaem and filedata with value the string content of the generated yarrrml yaml file.
    """
    g = Graph(bind_namespaces="core")
    g.bind("method", Namespace(method_ns))
    g.bind("data", Namespace(data_ns))
    g.bind("bfo", BFO)
    g.bind("csvw", CSVW)
    prefixes = {prefix: str(url) for (prefix, url) in g.namespaces()}
    result = OrderedDict()
    result["prefixes"] = prefixes
    result["base"] = "http://purl.matolab.org/mseo/mappings/"
    # data_file should be url at best
    result["sources"] = {
        "data_entities": {
            "access": str(data_url),
            "referenceFormulation": "jsonpath",
            "iterator": "$..[*]",
        }
    }
    result["use_template_rowwise"] = str(use_template_rowwise).lower()
    result["mappings"] = OrderedDict()
    print(subjects_dict)
    logging.debug(subjects_dict)
    for ice_key, il_id in map_list:
        _il = subjects_dict.get(il_id, None)
        logging.debug("{} {} {}".format(ice_key, il_id, _il))
        if _il:
            lookup_property = "$({})".format(_il["property"])
            if lookup_property == "$(title)":
                lookup_property = "$(titles)"
            compare_string = str(_il["text"])

            result["mappings"][ice_key] = OrderedDict(
                {
                    "sources": ["data_entities"],
                    #'s': 'data:$(@id)',
                    "s": "$(@id)",
                    "condition": {
                        "function": "equal",
                        "parameters": [
                            ["str1", lookup_property],
                            ["str2", compare_string],
                        ],
                    },
                    # 'po':[['obo:0010002', 'method:'+str(mapping[0]).split('/')[-1]],]
                    "po": [
                        [str(mapping_predicate_uri), "method:" + ice_key + "~iri"],
                    ],
                    #'po': [[str(mapping_predicate_uri), _il+'~iri'], ]
                }
            )
            # self.mapping_yml=result
    filename = (
        data_url.rsplit("/", 1)[-1].rsplit(".", 1)[0].rsplit("-", 1)[0] + "-map.yaml"
    )
    data = result
    return {"filename": filename, "filedata": data}
