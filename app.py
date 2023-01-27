import os
import base64
import uuid

from config import config
import flask
from flask import request, render_template, flash
from flask import send_from_directory, session, jsonify, json
from flask_bootstrap import Bootstrap
from flask_swagger_ui import get_swaggerui_blueprint

from flask_wtf import FlaskForm
from wtforms import URLField, SelectField, FieldList, FormField
from wtforms.validators import DataRequired, Optional, URL
import maptomethod

config_name = os.environ.get("APP_MODE") or "development"

print(config)
app = flask.Flask(__name__)
app.config.from_object(config[config_name])

app.methods_dict = maptomethod.get_methods()
#app.methods_dict={'DIN_EN_ISO_527': 'https://raw.githubusercontent.com/Mat-O-Lab/MSEO/main/methods/DIN_EN_ISO_527-3.drawio.ttl'}

bootstrap = Bootstrap(app)



swaggerui_blueprint = get_swaggerui_blueprint(
    app.config['SWAGGER_URL'],
    app.config['API_URL'],
    config={
        "app_name": "MapToMethod"
    }
)

app.register_blueprint(swaggerui_blueprint, url_prefix=app.config['SWAGGER_URL'])

class StartForm(FlaskForm):
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


class SelectForm(FlaskForm):
    select = SelectField("Placeholder", default=(
        0, "None"), choices=[], validate_choice=False)


class MappingFormList(FlaskForm):
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


@app.route("/static/<path:path>")
def send_static(path):
    return send_from_directory("static", path)

@app.route("/", methods=["GET", "POST"])
def index():
    logo = './static/resources/MatOLab-Logo.svg'
    start_form = StartForm()
    mapping_form = MappingFormList()
    message = ''
    result = ''
    return render_template(
        "index.html",
        logo=logo,
        start_form=start_form,
        message=message,
        mapping_form=mapping_form,
        result=result
    )


@app.route('/create_mapper', methods=['POST'])
def create_mapper():
    logo = './static/resources/MatOLab-Logo.svg'
    start_form = StartForm()
    mapping_form = MappingFormList()
    message = ''
    result = ''
    # print(request.form)
    if start_form.validate_on_submit():
        # url valid now test if readable -metadata.json
        if not start_form.data_url.data:
            start_form.data_url.data=start_form.data_url.render_kw['placeholder']
            flash('URL Data File empty: using placeholder value for demonstration', 'info')
        data_url = start_form.data_url.data
        
        # if url to method graph provided use it if not use select widget
        if start_form.method_url.data:
            method_url = start_form.method_url.data
        else:
            method_url = start_form.method_sel.data

        try:
            mapper = maptomethod.Mapper(
                data_url=data_url, method_url=method_url)
        except (ValueError, TypeError) as err:
            flash(str(err),'error')
        else:
            flash(mapper, 'info')
            session['data_url'] = mapper.data_url
            session['method_url'] = mapper.method_url
            session['methode_ices'] = mapper.ices
            session['info_lines'] = mapper.info_lines
            info_choices = [(id, value['text']) for
                            id, value in mapper.info_lines.items()]
            info_choices.insert(0, (None, 'None'))
            mapping_form.items = get_select_entries(
                session.get('methode_ices', None).keys(), info_choices)
    return render_template(
        "index.html",
        logo=logo,
        start_form=start_form,
        message=message,
        mapping_form=mapping_form,
        result=result
    )


@app.route('/map', methods=['POST'])
def map():
    logo = './static/resources/MatOLab-Logo.svg'
    start_form = StartForm(
        data_url=session.get('data_url', None),
        method_url=session.get('method_url', None),
        method_sel=session.get('method_url', None))
    #start_form = StartForm()
    message = ''
    temp = request.form.to_dict()
    temp.pop("csrf_token")
    maplist = [(k, v) for k, v in temp.items() if v != 'None']
    session['maplist'] = maplist
    # print(maplist)
    filename, result_string = maptomethod.Mapper(
        session.get('data_url', None),
        session.get('method_url', None),
        session.get('info_lines', None),
        maplist=maplist).to_yaml()
    b64 = base64.b64encode(result_string.encode())
    payload = b64.decode()
    return render_template(
        "index.html",
        logo=logo,
        start_form=start_form,
        message=message,
        mapping_form=None,
        result=result_string,
        filename=filename,
        payload=payload
    )


@app.route("/api/informationcontententities", methods=["GET"])
def informationcontententities():
    if request.method == "GET":
        url = request.args.get('url')
        return json.dumps(maptomethod.get_methode_ices(url))


@app.route("/api/informationbearingentities", methods=["GET"])
def informationbearingentities():
    if request.method == "GET":
        url = request.args.get('url')
        return json.dumps(maptomethod.get_data_informationbearingentities(url))


@app.route("/api/mappingfile", methods=["POST"])
def mappingfile():
    if request.method == "POST":
        content = request.get_json()
        filename, file_data = maptomethod.Mapper(
            content['data_url'],
            content['method_url'],
            #content['informationbearingentities'],
            maplist=content['maplist'].items()
        ).to_yaml()
        return jsonify({"filename": filename, "filedata": file_data})


@app.errorhandler(500)
def handle_500_error(e):
    return jsonify({"error": "Server error, review the input"}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=app.config["DEBUG"])
