import os
import flask
import copy
from datetime import datetime
from flask import request, url_for, render_template, redirect, flash, send_from_directory, current_app, session, jsonify
from flask import json
from flask.helpers import make_response
from flask_bootstrap import Bootstrap
from flask_cors import CORS
from flask_swagger_ui import get_swaggerui_blueprint
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSON

from flask_wtf import FlaskForm
from wtforms import URLField, SelectField, FieldList, FormField, StringField
from wtforms.validators import DataRequired
#from source.chowlk.transformations import transform_ontology
#from source.chowlk.utils import read_drawio_xml
import xml.etree.ElementTree as ET
from config import config
import uuid
import maptomethod
import base64


config_name = os.environ.get("APP_MODE") or "development"

app = flask.Flask(__name__)
app.config.from_object(config[config_name])
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)
CORS(app)
bootstrap = Bootstrap(app)

# Schema definition
class User(db.Model):

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime)
    input = db.Column(db.String)
    output = db.Column(db.String)
    errors = db.Column(JSON)

    def __init__(self, date, input, output, errors):
        self.date = date
        self.input = input
        self.output = output
        self.errors = errors

    def __repr__(self) -> str:
        return super().__repr__()

methods_dict=maptomethod.get_methods()
#methods_dict={'DIN_EN_ISO_527': 'https://raw.githubusercontent.com/Mat-O-Lab/MSEO/main/methods/DIN_EN_ISO_527-3.drawio.ttl'}

class StartForm(FlaskForm):
    data_url = URLField('URL Meta Data', validators=[DataRequired()], description='Paste URL to meta data json file create form CSVToCSVW')
    method_sel = SelectField('Method Graph', choices=[(v,k) for k,v in methods_dict.items()],description='Select a method graph from https://github.com/Mat-O-Lab/MSEO/tree/main/methods')

class SelectForm(FlaskForm):
    select = SelectField("Placeholder", default=(0, "None"),choices=[],validate_choice=False)

class MappingFormList(FlaskForm):
    items = FieldList(FormField(SelectForm))

def get_select_entries(ice_list,info_list):
    """
    Converts custom metadata to a forms.SelectForm(), which can then be
    used by SelectFormlist() to dynamically render select items.

    :return: <forms.SelectForm object>
    """
    all_select_items = []
    for ice in ice_list:
        id = uuid.uuid1()   # allows for multiple selects
        select_entry = SelectForm()
        select_entry.select.label = ice
        select_entry.select.name = ice
        select_entry.select.id = f"{ice}-{id}"
        select_entry.select.choices = info_list
        all_select_items.append(select_entry)
    return all_select_items


@app.route("/static/<path:path>")
def send_static(path):
    return send_from_directory("static", path)

SWAGGER_URL = "/api/docs"
API_URL = "/static/swagger.json"
swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        "app_name": "MapToMethod"
    }
)

app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)


@app.route("/", methods=["GET", "POST"])
def index():
    logo = './static/resources/MatOLab-Logo.svg'
    start_form = StartForm()
    mapping_form = MappingFormList()
    message = ''
    result= ''
    return render_template("index.html",logo=logo, start_form=start_form, message=message, mapping_form=mapping_form, result=result)

@app.route('/create_mapper', methods=['POST'])
def create_mapper():
    logo = './static/resources/MatOLab-Logo.svg'
    start_form = StartForm()
    mapping_form = MappingFormList()
    message = ''
    result= ''
    #print(request.form)
    if start_form.validate_on_submit():
        # url valid now test if readable -metadata.json
        try:
            mapper=maptomethod.Mapper(data_url=start_form.data_url.data, method_url=start_form.method_sel.data)
        except (ValueError, TypeError) as err:
            flash(str(err))
        else:
            flash(mapper)
            session['data_url'] = mapper.data_url
            session['method_url'] =mapper.method_url
            session['methode_ICEs'] = mapper.ICEs
            session['info_lines'] = mapper.InfoLines
            info_choices=[(id, value['text'])  for id, value in mapper.InfoLines.items()]
            info_choices.insert(0,(None,'None'))
            mapping_form.items=get_select_entries( session.get('methode_ICEs', None).keys(),info_choices)
    return render_template("index.html",logo=logo, start_form=start_form, message=message, mapping_form=mapping_form, result=result)

@app.route('/map', methods=['POST'])
def map():
    logo = './static/resources/MatOLab-Logo.svg'
    start_form = StartForm(data_url=session.get('data_url', None),method_sel=session.get('method_url', None))
    message = ''
    result= ''
    temp=request.form.to_dict()
    temp.pop("csrf_token")
    maplist=[(k, v) for k, v in temp.items() if v != 'None']
    session['maplist'] = maplist
    print(maplist)
    #filename,result_string=maptomethod.get_mapping_output(session.get('data_url', None), session.get('method_url', None), maplist, session.get('info_lines', None))
    filename,result_string=maptomethod.Mapper(session.get('data_url', None), session.get('method_url', None), session.get('info_lines', None), maplist=maplist).to_yaml()
    b64 = base64.b64encode(result_string.encode())
    payload = b64.decode()
    return render_template("index.html",logo=logo, start_form=start_form, message=message, mapping_form=None, result=result_string, filename=filename, payload=payload)

@app.route("/api/ices", methods=["GET"])
def ices():
    if request.method == "GET":
        url = request.args.get('url')
        return json.dumps(maptomethod.get_methode_ICE(url))

@app.route("/api/infolines", methods=["GET"])
def infolines():
    if request.method == "GET":
        url = request.args.get('url')
        return json.dumps(maptomethod.get_data_Info(url))

@app.route("/api/mappingfile", methods=["POST"])
def mappingfile():
    if request.method == "POST":
        content = request.get_json()
        filename, file_data = maptomethod.Mapper(content['data_url'],content['method_url'], content['info_lines'], maplist=content['maplist'].items()).to_yaml()
        return jsonify({"filename": filename, "filedata": file_data})



@app.errorhandler(500)
def handle_500_error(e):
    return jsonify({"error": "Server error, review the input"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=app.config["DEBUG"])
