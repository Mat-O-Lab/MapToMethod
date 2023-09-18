# app.py

import os
import base64

import uvicorn
from starlette_wtf import CSRFProtectMiddleware, csrf_protect
from starlette.responses import HTMLResponse
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware
from typing import Any, List

from pydantic import BaseModel, AnyUrl, Field

from fastapi import Request, FastAPI, Body, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, StreamingResponse

import logging
from io import BytesIO
import yaml
from rdflib import URIRef

import maptomethod
import forms

import settings
setting = settings.Setting()


config_name = os.environ.get("APP_MODE") or "development"

middleware = [
    Middleware(SessionMiddleware, secret_key=os.environ.get('APP_SECRET','changemeNOW')),
    #Middleware(CSRFProtectMiddleware, csrf_secret=os.environ.get('APP_SECRET','changemeNOW')),
    Middleware(CORSMiddleware, 
            allow_origins=["*"], # Allows all origins
            allow_methods=["*"], # Allows all methods
            allow_headers=["*"] # Allows all headers
            ),
    Middleware(uvicorn.middleware.proxy_headers.ProxyHeadersMiddleware, trusted_hosts="*")
    ]

app = FastAPI(
    title=setting.name,
    description=setting.desc,
    version=setting.version,
    contact={"name": setting.contact_name, "url": setting.org_site, "email": setting.admin_email},
    license_info={
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    },
    openapi_url=setting.openapi_url,
    #openapi_tags=tags_metadata,
    docs_url=setting.docs_url,
    redoc_url=None,
    swagger_ui_parameters= {'syntaxHighlight': False},
    #swagger_favicon_url="/static/resources/favicon.svg",
    middleware=middleware

)

app.mount("/static/", StaticFiles(directory='static', html=True), name="static")
templates= Jinja2Templates(directory="templates")

print(os.environ.get("APP_MODE", "production"))
if os.environ.get("APP_MODE", "production")=='development':
    print('fetching methods form MSEO repo')
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
        "result": '',
        "setting": setting
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

        try:
            mapper=maptomethod.Mapper(
                data_url=data_url,
                method_url=method_url,
                mapping_predicate_uri = URIRef(mapping_predicate_uri),
                data_subject_super_class_uris = [ URIRef(uri) for uri in mapping_subject_class_uris],
                method_object_super_class_uris = [ URIRef(uri) for uri in mapping_object_class_uris]
                )
            flash(request,str(mapper), 'info')
        except Exception as err:
            flash(request,str(err),'error')
        print(mapper.objects.keys())
        #only named instances in the data can be mapped
        info_choices = [(id, value['text']) for id, value in mapper.subjects.items() if 'text' in value.keys()]
        info_choices.insert(0, (None, 'None'))
        select_forms = forms.get_select_entries(mapper.objects.keys(), info_choices)
        mapping_form=await forms.MappingFormList.from_formdata(request)
        mapping_form.assignments.entries=select_forms
    return templates.TemplateResponse("index.html",
        {"request": request,
        "start_form": start_form,
        "mapping_form": mapping_form,
        "result": '',
        "setting": setting
        }
    )

@app.post("/map", response_class=HTMLResponse, include_in_schema=False)
async def map(request: Request):
    formdata = await request.form()
    data_url=request.session.get('data_url', None)
    method_url=request.session.get('method_url', None)
    method_sel=request.session.get('method_url', None)
    mapping_subject_class_uris = request.session.get('mapping_subject_class_uris',None)
    mapping_predicate_uri = request.session.get('mapping_predicate_uri',None)
    mapping_object_class_uris = request.session.get('mapping_object_class_uris',None)
    start_form = forms.StartForm(request,
        data_url=data_url,
        method_url=method_url,
        method_sel=method_sel)
    start_form.method_sel.choices=[(v, k) for k, v in app.methods_dict.items()]
    # entrys from advanced form
    
    
    result = ''
    filename = ''
    result_string= ''
    payload = ''
    select_dict=dict(formdata)
    maplist = [(k, v) for k, v in select_dict.items() if v != 'None']
    logging.info('Creating mapping file for mapping list: {}'.format(maplist))
    request.session['maplist'] = maplist
    with maptomethod.Mapper(
        data_url=data_url, 
        method_url=method_url,
        mapping_predicate_uri = URIRef(mapping_predicate_uri),
        data_subject_super_class_uris = [ URIRef(uri) for uri in mapping_subject_class_uris],
        method_object_super_class_uris = [ URIRef(uri) for uri in mapping_object_class_uris],
        maplist=maplist
        ) as mapper:
        result=mapper.to_pretty_yaml()
        filename = result['filename']
        result_string = result['filedata']
        print(type(result_string))
        print(result_string)
        b64 = base64.b64encode(result_string.encode())
        payload = b64.decode()
    return templates.TemplateResponse("index.html",
        {"request": request,
        "start_form": start_form,
        "mapping_form": '',
        'filename': filename,
        'payload': payload,
        "result": result_string,
        "setting": setting
        }
    )

class QueryRequest(BaseModel):
    url: AnyUrl = Field('', title='Graph Url', description='Url to the sematic dataset to query')
    entity_classes: List = Field([], title='Class List', description='List of super classes to query for',)
    class Config:
        schema_extra = {
            "example": {
                        "url": "https://github.com/Mat-O-Lab/CSVToCSVW/raw/main/examples/example-metadata.json",
                        "entity_classes": [
                            "http://www.w3.org/ns/csvw#Column",
                            "http://www.w3.org/ns/oa#Annotation"
                        ]
                    },
        }
@app.post("/api/entities")
def query_entities(request: QueryRequest):
    #translate urls in entity_classes list to URIRef objects
    request.entity_classes=[ URIRef(url) for url in request.entity_classes]
    return maptomethod.query_entities(request.url, request.entity_classes)



class MappingRequest(BaseModel):
    data_url: AnyUrl = Field('', title='Graph Url', description='Url to data metadata to use.')
    method_url: AnyUrl = Field('', title='Graph Url', description='Url to knowledge graph to use.')
    data_super_classes: List = Field([maptomethod.OA.Annotation,maptomethod.CSVW.Column], title='Subject Super Classes', description='List of subject super classes to query for mapping partners in data.')
    predicate: AnyUrl = Field(maptomethod.ContentToBearingRelation, title='predicate property', description='Predicate Property to connect data to method entities.')
    method_super_classes: List = Field([maptomethod.InformtionContentEntity,maptomethod.TemporalRegionClass], title='Object Super Classes', description='List of object super classes to query for mapping partners in method graph.')
    map: dict = Field( title='Map Dict', description='Dict of with key as individual name of objects in knowledge graph and ids of indivuals in data metadata as values to create mapping rules for.',)
    class Config:
        schema_extra = {
            "example": {
                        "data_url": "https://github.com/Mat-O-Lab/CSVToCSVW/raw/main/examples/example-metadata.json",
                        "method_url": "https://github.com/Mat-O-Lab/MSEO/raw/main/methods/DIN_EN_ISO_527-3.drawio.ttl",
                        "data_super_classes": [maptomethod.OA.Annotation,maptomethod.CSVW.Column],
                        "predicate": maptomethod.ContentToBearingRelation,
                        "method_super_classes": [maptomethod.InformtionContentEntity,maptomethod.TemporalRegionClass],
                        "map": {
                            "SpecimenName": "AktuelleProbe0",
                            "StrainMeasurementInformation": "table-1-Dehnung"
                        },
                    },
        }

class YAMLResponse(StreamingResponse):
    media_type = "application/x-yaml"

@app.post("/api/mapping", response_class=YAMLResponse)
def mapping(request: MappingRequest) -> StreamingResponse:
    try:
        result = maptomethod.Mapper(
            request.data_url,
            request.method_url,
            method_object_super_class_uris=[URIRef(uri) for uri in request.method_super_classes],
            mapping_predicate_uri=URIRef(request.predicate),
            data_subject_super_class_uris=[URIRef(uri) for uri in request.data_super_classes],
            maplist=request.map.items()
        ).to_pretty_yaml()
    except Exception as err:
        print(err)
        raise HTTPException(status_code=500, detail=str(err))
    data_bytes=BytesIO(result['filedata'].encode())
    filename=result['filename']
    headers = {
        'Content-Disposition': 'attachment; filename={}'.format(filename),
        'Access-Control-Expose-Headers': 'Content-Disposition'
    }
    media_type="application/x-yaml"
    return StreamingResponse(content=data_bytes, media_type=media_type, headers=headers)

@app.get("/info", response_model=settings.Setting)
async def info() -> dict:
    return setting

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
