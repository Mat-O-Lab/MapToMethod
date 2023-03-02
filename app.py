# app.py

import os
import base64

import uvicorn
from starlette.responses import HTMLResponse
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware

from fastapi.middleware.cors import CORSMiddleware
from typing import Any, List

from pydantic import BaseSettings, BaseModel, AnyUrl, Field

from fastapi import Request, FastAPI, Body
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

import logging
from rdflib import URIRef

import maptomethod
import forms

class Settings(BaseSettings):
    app_name: str = "MaptoMethod"
    admin_email: str = os.environ.get("ADMIN_MAIL") or "csvtocsvw@matolab.org"
    items_per_user: int = 50
    version: str = "v1.0.4"
    config_name: str = os.environ.get("APP_MODE") or "development"
    openapi_url: str ="/api/openapi.json"
    docs_url: str = "/api/docs"
settings = Settings()

config_name = os.environ.get("APP_MODE") or "development"

middleware = [Middleware(SessionMiddleware, secret_key=os.getenv("APP_SECRET", "your-secret"))]
app = FastAPI(
    title=settings.app_name,
    description="Tool to map content of JSON-LD files (output of CSVtoCSVW) describing CSV files to Information Content Entities in knowledge graphs describing methods in the method folder of the MSEO Ontology repository at https://github.com/Mat-O-Lab/MSEO.",
    version=settings.version,
    contact={"name": "Thomas Hanke, Mat-O-Lab", "url": "https://github.com/Mat-O-Lab", "email": settings.admin_email},
    license_info={
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    },
    openapi_url=settings.openapi_url,
    docs_url=settings.docs_url,
    redoc_url=None,    
    #to disable highlighting for large output
    #swagger_ui_parameters= {'syntaxHighlight': False},
    middleware=middleware
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allows all origins
    allow_credentials=True,
    allow_methods=["*"], # Allows all methods
    allow_headers=["*"], # Allows all headers
)
app.add_middleware(uvicorn.middleware.proxy_headers.ProxyHeadersMiddleware, trusted_hosts="*")

app.mount("/static/", StaticFiles(directory='static', html=True), name="static")
templates= Jinja2Templates(directory="templates")

if os.environ.get("APP_MODE")=='development':
    app.methods_dict={'DIN_EN_ISO_527': 'https://github.com/Mat-O-Lab/MSEO/raw/main/methods/DIN_EN_ISO_527-3.drawio.ttl'}

else:
    app.methods_dict = maptomethod.get_methods()

#flash integration flike flask flash
def flash(request: Request, message: Any, category: str = "info") -> None:
    if "_messages" not in request.session:
        request.session["_messages"] = []
    request.session["_messages"].append({"message": message, "category": category})

def get_flashed_messages(request: Request):
    return request.session.pop("_messages") if "_messages" in request.session else []

templates.env.globals['get_flashed_messages'] = get_flashed_messages


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def index(request: Request):
    start_form = await forms.StartForm.from_formdata(request)
    start_form.method_sel.choices=[(v, k) for k, v in app.methods_dict.items()]
    return templates.TemplateResponse("index.html",
        {"request": request,
        "start_form": start_form,
        "mapping_form": '',
        "result": ''
        }
    )


@app.post("/create_mapper", response_class=HTMLResponse, include_in_schema=False)
async def create_mapper(request: Request):
    start_form = await forms.StartForm.from_formdata(request)
    start_form.method_sel.choices=[(v, k) for k, v in app.methods_dict.items()]
    mapping_form = ''
    logging.info('create mapping')
    if await start_form.validate_on_submit():
        if not start_form.data_url.data:
            start_form.data_url.data=start_form.data_url.render_kw['placeholder']
            flash(request,'URL Data File empty: using placeholder value for demonstration', 'info')
        data_url = start_form.data_url.data
        request.session['data_url']=data_url
        
        # if url to method graph provided use it if not use select widget
        if start_form.method_url.data:
            method_url = start_form.method_url.data
        else:
            method_url = start_form.method_sel.data
        request.session['method_url']=method_url
        # entrys from advanced form
        mapping_subject_class_uris = start_form.advanced.data_subject_super_class_uris.data
        request.session['mapping_subject_class_uris']=mapping_subject_class_uris
        mapping_predicate_uri = start_form.advanced.mapping_predicate_uri.data
        request.session['mapping_predicate_uri']=mapping_predicate_uri
        mapping_object_class_uris = start_form.advanced.method_object_super_class_uris.data
        request.session['mapping_object_class_uris']=mapping_object_class_uris

        # try:
        with maptomethod.Mapper(
            data_url=data_url,
            method_url=method_url,
            mapping_predicate_uri = URIRef(mapping_predicate_uri),
            data_subject_super_class_uris = [ URIRef(uri) for uri in mapping_subject_class_uris],
            method_object_super_class_uris = [ URIRef(uri) for uri in mapping_object_class_uris]
            ) as mapper:
            info_choices = [(id, value['text']) for
                        id, value in mapper.subjects.items()]
            info_choices.insert(0, (None, 'None'))
            select_forms = forms.get_select_entries(
                mapper.objects.keys(),
                info_choices
            )
            flash(request,str(mapper), 'info')
        # except Exception as err:
        #     flash(request,str(err),'error')
        mapping_form=await forms.MappingFormList.from_formdata(request)
        mapping_form.assignments.entries=select_forms
    return templates.TemplateResponse("index.html",
        {"request": request,
        "start_form": start_form,
        "mapping_form": mapping_form,
        "result": ''
        }
    )

@app.post("/map", response_class=HTMLResponse, include_in_schema=False)
async def map(request: Request):
    formdata = await request.form()
    data_url=request.session.get('data_url', None)
    method_url=request.session.get('method_url', None)
    method_sel=request.session.get('method_url', None)
    start_form = forms.StartForm(request,
        data_url=data_url,
        method_url=method_url,
        method_sel=method_sel)
    start_form.method_sel.choices=[(v, k) for k, v in app.methods_dict.items()]
    result = ''
    filename = ''
    result_string= ''
    payload = ''
    select_dict=dict(formdata)
    maplist = [(k, v) for k, v in select_dict.items() if v != 'None']
    logging.info('Creating mapping file for mapping list: {}'.format(maplist))
    request.session['maplist'] = maplist
    with maptomethod.Mapper(data_url=data_url, method_url=method_url,maplist=maplist) as mapper:
        result=mapper.to_pretty_yaml()
        filename = result['filename']
        result_string = result['filedata']
        b64 = base64.b64encode(result_string.encode())
        payload = b64.decode()
    return templates.TemplateResponse("index.html",
        {"request": request,
        "start_form": start_form,
        "mapping_form": '',
        'filename': filename,
        'payload': payload,
        "result": result_string
        }
    )

class QueryRequest(BaseModel):
    url: AnyUrl = Field('', title='Graph Url', description='Url to the sematic dataset to query')
    entity_classes: List = Field([], title='Class List', description='List of super classes to query for',)

@app.post("/api/subjects")
def informationbearingentities(request: QueryRequest= Body(
        examples={
                "normal": {
                    "summary": "A normal example",
                    "description": "A **normal** item works correctly.",
                    "value": {
                        "url": "https://github.com/Mat-O-Lab/CSVToCSVW/raw/main/examples/example-metadata.json",
                        "entity_classes": [
                            "http://www.w3.org/ns/csvw#Column",
                            "http://www.w3.org/ns/oa#Annotation"
                        ]
                    },
                },
        }
    )):
    #translate urls in entity_classes list to URIRef objects
    request.entity_classes=[ URIRef(url) for url in request.entity_classes]
    return maptomethod.get_data_informationbearingentities(request.url, request.entity_classes)


@app.post("/api/objects")
def informationcontententities(request: QueryRequest = Body(
        examples={
                "normal": {
                    "summary": "A normal example",
                    "description": "A **normal** item works correctly.",
                    "value": {
                        "url": "https://github.com/Mat-O-Lab/MSEO/raw/main/methods/DIN_EN_ISO_527-3.drawio.ttl",
                        "entity_classes": [
                            'http://www.ontologyrepository.com/CommonCoreOntologies/InformationContentEntity', #cco:InformationContentEntity
                            'http://purl.obolibrary.org/obo/BFO_0000008' # bfo:temporal region
                            ]
                    },
                },
        }
    )):
    #translate urls in entity_classes list to URIRef objects
    request.entity_classes=[ URIRef(url) for url in request.entity_classes]
    return maptomethod.get_methode_ices(request.url, request.entity_classes)


class MappingRequest(BaseModel):
    data_url: AnyUrl = Field('', title='Graph Url', description='Url to data metadata to use.')
    method_url: AnyUrl = Field('', title='Graph Url', description='Url to knowledge graph to use.')
    map_list: dict = Field( title='Map Dict', description='Dict of with key as individual name of objects in knowledge graph and labels of indivuals in data metadata as values to create mapping rules for.',)


@app.post("/api/mapping")
def mapping(request: MappingRequest = Body(
        examples={
                "normal": {
                    "summary": "A normal example",
                    "description": "A **normal** item works correctly.",
                    "value": {
                        "data_url": "https://github.com/Mat-O-Lab/CSVToCSVW/raw/main/examples/example-metadata.json",
                        "method_url": "https://github.com/Mat-O-Lab/MSEO/raw/main/methods/DIN_EN_ISO_527-3.drawio.ttl",
                        "map_list": {
                            "SpecimenName": "AktuelleProbe0",
                            "StrainMeasurementInformation": "Dehnung"
                        },
                    },
                },
        }
    )):
    result = maptomethod.Mapper(
        request.data_url,
        request.method_url,
        maplist=request.map_list.items()
    ).to_yaml()
    return result

@app.get("/info", response_model=Settings)
async def info() -> dict:
    return settings

import yaml

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app_mode=os.environ.get("APP_MODE") or 'production'
    with open('log_config.yml') as f:
        config = yaml.load(f)
        logging.config.dictConfig(config)
    if app_mode=='development':
        reload=True
        access_log=True
        config['root']['level']='DEBUG'
    else:
        reload=False
        access_log=False
        config['root']['level']='ERROR'
    print('Log Level Set To {}'.format(config['root']['level']))
    uvicorn.run("app:app",host="0.0.0.0",port=port, reload=reload, access_log=access_log,log_config=config)