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

#methods_dict=maptomethod.get_methods()
methods_dict={'DIN_EN_ISO_527': 'https://raw.githubusercontent.com/Mat-O-Lab/MSEO/main/methods/DIN_EN_ISO_527-3.drawio.ttl', 'test2': 'values2'}

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

SWAGGER_URL = "/swagger"
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
    print(request.form)
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
            session['methode_ICEs'] = mapper.methode_ICEs
            session['info_lines'] = mapper.info_lines
            print(mapper.info_lines)
            info_choices=[(value['uri'], value['label'] if 'label' in value.keys() else value['titles']) for id, value in mapper.info_lines.items()]
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
    print(temp)
    map_dict={k: v for k, v in temp.items() if v != 'None'}
    session['map_dict'] = map_dict
    filename,result_string=maptomethod.get_mapping_output(session.get('data_url', None), session.get('method_url', None), map_dict, session.get('info_lines', None))
    return render_template("index.html",logo=logo, start_form=start_form, message=message, mapping_form=None, result=result_string)


@app.route("/api", methods=["GET", "POST"])
def api():

    if request.method == "POST":
        file = request.files["data"]
        filename = file.filename

        if filename == "":
            error = "No file choosen. Please choose a diagram."
            flash(error)
            return redirect(url_for("index"))

        os.makedirs("data", exist_ok=True)
        input_path = os.path.join("data", filename)

        ttl_filename = filename[:-3] + "ttl"

        if not os.path.exists(app.config["TEMPORAL_FOLDER"]):
            os.makedirs(app.config["TEMPORAL_FOLDER"])

        ttl_filepath = os.path.join(app.config["TEMPORAL_FOLDER"], ttl_filename)

        # Reading and transforming the diagram
        #root = read_drawio_xml(file)
        #turtle_file_string, xml_file_string, new_namespaces, errors = transform_ontology(root)
        turtle_file_string, xml_file_string, new_namespaces, errors = file, "", None

        # Eliminating keys that do not contain errors
        new_errors = copy.copy(errors)
        for key, error in errors.items():
            if len(error) == 0:
                del new_errors[key]

        with open(ttl_filepath, "w") as file:
            file.write(turtle_file_string)

        session["ttl_filename"] = ttl_filename

        with open(ttl_filepath, "r") as f:
            ttl_data = f.read()

        user = User(datetime.now(), input_path, ttl_filepath, errors)
        db.session.add(user)
        db.session.commit()

        return {"ttl_data": ttl_data, "errors": new_errors, "new_namespaces": new_namespaces}


@app.errorhandler(500)
def handle_500_error(e):
    return jsonify({"error": "Server error, review the input diagram"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=app.config["DEBUG"])
