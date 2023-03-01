# app.py

from dataclasses import fields
import os
import base64
from tkinter import Widget
import uuid

import uvicorn
from starlette_wtf import StarletteForm
from starlette.datastructures import FormData
from starlette.responses import HTMLResponse
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware

#from starlette.middleware.cors import CORSMiddleware
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Any, List

from pydantic import BaseSettings, BaseModel, AnyUrl, Field

from fastapi import Request, FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from wtforms import URLField, SelectField, FieldList, FormField, Form
from wtforms.validators import Optional, URL
from wtforms.widgets import ListWidget, html_params
from markupsafe import Markup

import logging
from rdflib import URIRef

import maptomethod

if os.environ.get("APP_MODE")=='development':
    logging.basicConfig(level=logging.DEBUG)


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

#flash integration flike flask flash
def flash(request: Request, message: Any, category: str = "info") -> None:
    if "_messages" not in request.session:
        request.session["_messages"] = []
    request.session["_messages"].append({"message": message, "category": category})

def get_flashed_messages(request: Request):
    return request.session.pop("_messages") if "_messages" in request.session else []
templates.env.globals['get_flashed_messages'] = get_flashed_messages

#app.methods_dict = maptomethod.get_methods()
app.methods_dict={'DIN_EN_ISO_527': 'https://raw.githubusercontent.com/Mat-O-Lab/MSEO/main/methods/DIN_EN_ISO_527-3.drawio.ttl'}


class ListWidgetBootstrap(ListWidget):
    def __init__(self, html_tag="div", prefix_label=True, col_class=''):
        assert html_tag in ("div", "a")
        self.html_tag = html_tag
        self.prefix_label = prefix_label
        self.col_class=col_class

    def __call__(self, field, **kwargs):
        kwargs.setdefault("id", field.id)
        html = [f"<{self.html_tag} {html_params(**kwargs)}>"]
        for subfield in field:
            # if subfield we have to traverse once more down
            if isinstance(subfield,Form):
                for subsubfield in subfield:
                    if self.prefix_label:
                        html.append(f"<div class={self.col_class}>{subsubfield.label} {subsubfield()}</div>")
                    else:
                        html.append(f"<div class={self.col_class}>{subsubfield()} {subsubfield.label}</div>")
            # print(dir(subfield))
            else:
                if self.prefix_label:
                    html.append(f"<div class={self.col_class}>{subfield.label} {subfield()}</div>")
                else:
                    html.append(f"<div class={self.col_class}>{subfield()} {subfield.label}</div>")
        html.append("</%s>" % self.html_tag)
        return Markup("".join(html))

class StartForm(StarletteForm):
    data_url = URLField('URL Meta Data',
        #validators=[DataRequired(),URL()],
        render_kw={"placeholder": "https://github.com/Mat-O-Lab/CSVToCSVW/raw/main/examples/example-metadata.json",
        "class":"form-control"},
        description='Paste URL to meta data json file create from CSVToCSVW'
    )
    method_url = URLField(
        'URL Method Data',
        render_kw={"class":"form-control"},
        validators=[Optional(), URL()],
        description='Paste URL to method graph create with MSEO',
    )
    method_sel = SelectField(
        'Method Graph',
        render_kw={"class":"form-control"},
        choices=[(v, k) for k, v in app.methods_dict.items()],
        description=('Alternativly select a method graph'
                     'from https://github.com/Mat-O-Lab/MSEO/tree/main/methods'
                     )
    )
    data_data_subject_super_class_uris = FieldList(
        URLField('URI', validators=[Optional(), URL()], 
        render_kw={"class":"form-control"}),
        min_entries=2,
        widget=ListWidgetBootstrap(col_class='col-sm-6'),
        render_kw={"class":"row"})
    mapping_predicate_uri = URLField('URL Mapping Predicat',
        #validators=[DataRequired(),URL()],
        render_kw={
            "placeholder": "http://purl.obolibrary.org/obo/RO_0010002",
            "class":"form-control"
            },
        description='URI of object property to use as predicate.'
        )
    method_object_super_class_uris = FieldList(
        URLField('URI', validators=[Optional(), URL()], 
        render_kw={"class":"form-control"}),
        min_entries=2,
        widget=ListWidgetBootstrap(col_class='col-sm-6'),
        render_kw={"class":"row"}
        )
    

class SelectForm(Form):
    select = SelectField("Placeholder", default=(
        0, "None"), choices=[], validate_choice=False, render_kw={"class":"form-control col-s-3"})


class MappingFormList(StarletteForm):
    assignments = FieldList(
        FormField(SelectForm,
        render_kw={"class":"form-control"}),
        widget=ListWidgetBootstrap(col_class='col-sm-4'),
        render_kw={"class":"row"},
        )


def get_select_entries(ice_list, info_list):
    """
    Converts custom metadata to a forms.SelectForm(), which can then be
    used by SelectFormlist() to dynamically render select items.

    :return: <forms.SelectForm object>
    """
    all_select_items = []
    for ice in ice_list:
        _id = uuid.uuid1()   # allows for multiple selects
        select_form = SelectForm()
        select_form.select.label = ice
        select_form.select.name = ice
        select_form.select.id = f"{ice}-{_id}"
        select_form.select.choices = info_list
        all_select_items.append(select_form)
    return all_select_items



@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    start_form = await StartForm.from_formdata(request)
    return templates.TemplateResponse("index.html",
        {"request": request,
        "start_form": start_form,
        "mapping_form": '',
        "result": ''
        }
    )


@app.post("/create_mapper", response_class=HTMLResponse)
async def create_mapper(request: Request):
    start_form = await StartForm.from_formdata(request)
    mapping_form = ''
    if await start_form.validate_on_submit():
        if not start_form.data_url.data:
            start_form.data_url.data=start_form.data_url.render_kw['placeholder']
            flash(request,'URL Data File empty: using placeholder value for demonstration', 'info')
        data_url = start_form.data_url.data
        request.session['data_url']=data_url
        if not start_form.mapping_predicate_uri.data:
            start_form.mapping_predicate_uri.data=start_form.mapping_predicate_uri.render_kw['placeholder']
            flash(request,'URL mapping predicate uri empty: using placeholder value for demonstration', 'info')
        mapping_predicate_uri = start_form.mapping_predicate_uri.data
        request.session['mapping_predicate_uri']=mapping_predicate_uri
        
        # if url to method graph provided use it if not use select widget
        if start_form.method_url.data:
            method_url = start_form.method_url.data
        else:
            method_url = start_form.method_sel.data
        request.session['method_url']=method_url
        try:
            with maptomethod.Mapper(
                data_url=data_url,
                method_url=method_url,
                mapping_predicate_uri=URIRef(mapping_predicate_uri)
                ) as mapper:
                    info_choices = [(id, value['text']) for
                                id, value in mapper.subjects.items()]
                    info_choices.insert(0, (None, 'None'))
                    select_forms = get_select_entries(
                        mapper.objects.keys(),
                        info_choices
                    )
                    flash(request,str(mapper), 'info')
        except Exception as err:
            flash(request,str(err),'error')
        mapping_form=await MappingFormList.from_formdata(request)
        mapping_form.assignments.entries=select_forms
    return templates.TemplateResponse("index.html",
        {"request": request,
        "start_form": start_form,
        "mapping_form": mapping_form,
        "result": ''
        }
    )

@app.post("/map", response_class=HTMLResponse)
async def map(request: Request):
    formdata = await request.form()
    data_url=request.session.get('data_url', None)
    method_url=request.session.get('method_url', None)
    method_sel=request.session.get('method_url', None)
    start_form = StartForm(request,
        data_url=data_url,
        method_url=method_url,
        method_sel=method_sel)
    result = ''
    payload = ''
    select_dict=dict(formdata)
    maplist = [(k, v) for k, v in select_dict.items() if v != 'None']
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