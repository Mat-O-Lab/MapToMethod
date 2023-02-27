# app.py

import os
import base64
import uuid
from wsgiref.validate import validator

from config import config
import uvicorn
from starlette_wtf import StarletteForm
from starlette.responses import HTMLResponse
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
#from starlette.middleware.cors import CORSMiddleware
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool
from typing import Optional, Any, List

from pydantic import BaseSettings, BaseModel, AnyUrl, Field, Json

from fastapi import Request, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from wtforms import URLField, SelectField, FieldList, FormField
from wtforms.validators import DataRequired, Optional, URL
import logging

from rdflib import URIRef
import maptomethod

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

middleware = [Middleware(SessionMiddleware, secret_key='super-secret')]
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
    swagger_ui_parameters= {'syntaxHighlight': False},
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

#app.methods_dict = maptomethod.get_methods()
app.methods_dict={'DIN_EN_ISO_527': 'https://raw.githubusercontent.com/Mat-O-Lab/MSEO/main/methods/DIN_EN_ISO_527-3.drawio.ttl'}

logging.basicConfig(level=logging.DEBUG)

class StartForm(StarletteForm):
    data_url = URLField('URL Meta Data',
        #validators=[DataRequired(),URL()],
        render_kw={"placeholder": "https://github.com/Mat-O-Lab/CSVToCSVW/raw/main/examples/example-metadata.json"},
        description='Paste URL to meta data json file create from CSVToCSVW'
        )
    method_url = URLField(
        'URL Method Data',
        validators=[Optional(), URL()],
        description='Paste URL to method graph create with MSEO',
    )
    method_sel = SelectField(
        'Method Graph',
        choices=[(v, k) for k, v in app.methods_dict.items()],
        description=('Alternativly select a method graph'
                     'from https://github.com/Mat-O-Lab/MSEO/tree/main/methods'
                     )
    )
    data_data_subject_super_class_uris = FieldList(URLField('URI', validators=[Optional(), URL()]))
    method_object_super_class_uris = FieldList(URLField('URI', validators=[Optional(), URL()]))
    mapping_predicate_uri = URLField('URL Meta Data',
        #validators=[DataRequired(),URL()],
        render_kw={"placeholder": "http://purl.obolibrary.org/obo/RO_0010002"},
        description='URI of object property to use as predicate to link.'
        )
    


class SelectForm(StarletteForm):
    select = SelectField("Placeholder", default=(
        0, "None"), choices=[], validate_choice=False)


class MappingFormList(StarletteForm):
    items = FieldList(FormField(SelectForm))


def get_select_entries(ice_list, info_list):
    """
    Converts custom metadata to a forms.SelectForm(), which can then be
    used by SelectFormlist() to dynamically render select items.

    :return: <forms.SelectForm object>
    """
    all_select_items = []
    for ice in ice_list:
        _id = uuid.uuid1()   # allows for multiple selects
        select_entry = SelectForm()
        select_entry.select.label = ice
        select_entry.select.name = ice
        select_entry.select.id = f"{ice}-{_id}"
        select_entry.select.choices = info_list
        all_select_items.append(select_entry)
    return all_select_items


# @app.route("/", methods=["GET", "POST"])
# def index():
#     logo = './static/resources/MatOLab-Logo.svg'
#     start_form = StartForm()
#     mapping_form = MappingFormList()
#     message = ''
#     result = ''
#     return render_template(
#         "index.html",
#         logo=logo,
#         start_form=start_form,
#         message=message,
#         mapping_form=mapping_form,
#         result=result
#     )


# @app.route('/create_mapper', methods=['POST'])
# def create_mapper():
#     logo = './static/resources/MatOLab-Logo.svg'
#     start_form = StartForm()
#     mapping_form = MappingFormList()
#     message = ''
#     result = ''
#     # print(request.form)
#     if start_form.validate_on_submit():
#         # url valid now test if readable -metadata.json
#         if not start_form.data_url.data:
#             start_form.data_url.data=start_form.data_url.render_kw['placeholder']
#             flash('URL Data File empty: using placeholder value for demonstration', 'info')
#         data_url = start_form.data_url.data
        
#         # if url to method graph provided use it if not use select widget
#         if start_form.method_url.data:
#             method_url = start_form.method_url.data
#         else:
#             method_url = start_form.method_sel.data

#         try:
#             mapper = maptomethod.Mapper(
#                 data_url=data_url, method_url=method_url)
#         except (ValueError, TypeError) as err:
#             flash(str(err),'error')
#         else:
#             flash(mapper, 'info')
#             session['data_url'] = mapper.data_url
#             session['method_url'] = mapper.method_url
#             session['methode_ices'] = mapper.objects
#             session['info_lines'] = mapper.subjects
#             info_choices = [(id, value['text']) for
#                             id, value in mapper.subjects.items()]
#             info_choices.insert(0, (None, 'None'))
#             mapping_form.items = get_select_entries(
#                 session.get('methode_ices', None).keys(), info_choices)
#     return render_template(
#         "index.html",
#         logo=logo,
#         start_form=start_form,
#         message=message,
#         mapping_form=mapping_form,
#         result=result
#     )


# @app.route('/map', methods=['POST'])
# def map():
#     logo = './static/resources/MatOLab-Logo.svg'
#     start_form = StartForm(
#         data_url=session.get('data_url', None),
#         method_url=session.get('method_url', None),
#         method_sel=session.get('method_url', None))
#     #start_form = StartForm()
#     message = ''
#     temp = request.form.to_dict()
#     temp.pop("csrf_token")
#     maplist = [(k, v) for k, v in temp.items() if v != 'None']
#     session['maplist'] = maplist
#     # print(maplist)
#     result=maptomethod.Mapper(
#         session.get('data_url', None),
#         session.get('method_url', None),
#         session.get('info_lines', None),
#         maplist=maplist).to_yaml()
#     filename = result['filename']
#     result_string = result['filedata']
#     b64 = base64.b64encode(result_string.encode())
#     payload = b64.decode()
#     return render_template(
#         "index.html",
#         logo=logo,
#         start_form=start_form,
#         message=message,
#         mapping_form=None,
#         result=result_string,
#         filename=filename,
#         payload=payload
#     )

class QueryRequest(BaseModel):
    url: AnyUrl = Field('', title='Graph Url', description='Url to the sematic dataset to query')
    entity_classes: List = Field([], title='Class List', description='List of super classes to query for',)
    class Config:
        schema_extra = {
            "example": {
                "url": "https://github.com/Mat-O-Lab/MSEO/raw/main/methods/DIN_EN_ISO_527-3.drawio.ttl",
                "entity_classes": [
                    'http://www.ontologyrepository.com/CommonCoreOntologies/InformationContentEntity', #cco:InformationContentEntity
                    'http://purl.obolibrary.org/obo/BFO_0000008' # bfo:temporal region
                    ]
            }
        }


from rdflib import URIRef


@app.post("/api/subjects")
def informationcontententities(request: QueryRequest):
    #translate urls in entity_classes list to URIRef objects
    request.entity_classes=[ URIRef(url) for url in request.entity_classes]
    return maptomethod.get_data_informationbearingentities(request.url, request.entity_classes)


@app.post("/api/objects")
def informationcontententities(request: QueryRequest):
    #translate urls in entity_classes list to URIRef objects
    request.entity_classes=[ URIRef(url) for url in request.entity_classes]
    return maptomethod.get_methode_ices(request.url, request.entity_classes)


class MappingRequest(BaseModel):
    data_url: AnyUrl = Field('', title='Graph Url', description='Url to data metadata to use.')
    method_url: AnyUrl = Field('', title='Graph Url', description='Url to knowledge graph to use.')
    map_list: dict = Field( title='Map Dict', description='Dict of with key as individual name of objects in knowledge graph and labels of indivuals in data metadata as values to create mapping rules for.',)
    class Config:
        schema_extra = {
            "example": {
                "data_url": "https://github.com/Mat-O-Lab/CSVToCSVW/raw/main/examples/example-metadata.json",
                "method_url": "https://github.com/Mat-O-Lab/MSEO/raw/main/methods/DIN_EN_ISO_527-3.drawio.ttl",
                "map_list": {
                    "SpecimenName": "AktuelleProbe0",
                    "StrainMeasurementInformation": "Dehnung"
                }
            }
        }



@app.post("/api/mapping")
def mapping(request: MappingRequest):
    # content = request.get_json()
    result = maptomethod.Mapper(
        request.data_url,
        request.method_url,
        maplist=request.map_list.items()
    ).to_yaml()
    # return jsonify({"filename": filename, "filedata": file_data})
    return result

@app.get("/info", response_model=Settings)
async def info() -> dict:
    return settings


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app_mode=os.environ.get("APP_MODE") or 'production'
    if app_mode=='development':
        reload=True
        access_log=True
    else:
        reload=False
        access_log=False
    uvicorn.run("app:app",host="0.0.0.0",port=port, reload=reload, access_log=access_log)