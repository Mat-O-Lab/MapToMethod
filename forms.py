# forms.py

from starlette_wtf import StarletteForm
from wtforms import URLField, SelectField, FieldList, FormField, Form
from wtforms.validators import Optional, URL
from wtforms.widgets import ListWidget, html_params
from markupsafe import Markup
from typing import List
import uuid




import maptomethod

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



class AdvancedForm(Form):
    data_subject_super_class_uris = FieldList(
        URLField('URI', validators=[Optional(), URL()], 
        render_kw={"class":"form-control"}),
        min_entries=2,
        default=[maptomethod.OA.Annotation,maptomethod.CSVW.Column],
        widget=ListWidgetBootstrap(col_class='col-sm-6'),
        render_kw={"class":"row"},
        description='URI of superclass to query for subjects in data.'
        )
    mapping_predicate_uri = URLField('URL Mapping Predicat',
        #validators=[DataRequired(),URL()],
        render_kw={"class":"form-control"},
        default=maptomethod.ContentToBearingRelation,
        description='URI of object property to use as predicate.'
        )
    method_object_super_class_uris = FieldList(
        URLField('URI', validators=[Optional(), URL()], 
        render_kw={"class":"form-control"}),
        min_entries=2,
        default=[maptomethod.InformtionContentEntity,maptomethod.TemporalRegionClass],
        widget=ListWidgetBootstrap(col_class='col-sm-6'),
        render_kw={"class":"row"},
        description='URI of superclass to query for objects in methode.'
        )

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
        #[(v, k) for k, v in app.methods_dict.items()]
        choices=[],
        description=('Alternativly select a method graph'
                     'from https://github.com/Mat-O-Lab/MSEO/tree/main/methods'
                     )
    )
    advanced=FormField(AdvancedForm,
        render_kw={"class":"collapse"},
        widget=ListWidgetBootstrap())
    

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


def get_select_entries(names: List, choices: List) -> List[SelectForm]:
    """Converts custom metadata to a forms.SelectForm(), which can then be
    used by SelectFormlist() to dynamically render select items.

    Args:
        names (List): List of names for selects to create
        choices (List): List of choices for the selects

    Returns:
        List[SelectForm]: _description_
    """
    all_select_items = []
    for name in names:
        _id = uuid.uuid1()   # allows for multiple selects
        select_form = SelectForm()
        select_form.select.label = name
        select_form.select.name = name
        select_form.select.id = f"{name}-{_id}"
        select_form.select.choices = choices
        all_select_items.append(select_form)
    return all_select_items
