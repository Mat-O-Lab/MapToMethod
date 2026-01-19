# forms.py

import uuid
from typing import List

from markupsafe import Markup
from starlette_wtf import StarletteForm
from wtforms import BooleanField, FieldList, Form, FormField, SelectField, URLField
from wtforms.validators import URL, Optional
from wtforms.widgets import ListWidget, html_params

import maptomethod


class ListWidgetBootstrap(ListWidget):
    def __init__(self, html_tag="div", prefix_label=True, col_class=""):
        assert html_tag in ("div", "a")
        self.html_tag = html_tag
        self.prefix_label = prefix_label
        self.col_class = col_class

    def __call__(self, field, **kwargs):
        kwargs.setdefault("id", field.id)
        html = [f"<{self.html_tag} {html_params(**kwargs)}>"]
        for subfield in field:
            # if subfield we have to traverse once more down
            if isinstance(subfield, Form):
                for subsubfield in subfield:
                    if self.prefix_label:
                        html.append(
                            f"<div class={self.col_class}>{subsubfield.label} {subsubfield()}</div>"
                        )
                    else:
                        html.append(
                            f"<div class={self.col_class}>{subsubfield()} {subsubfield.label}</div>"
                        )
            # print(dir(subfield))
            else:
                if self.prefix_label:
                    html.append(
                        f"<div class={self.col_class}>{subfield.label} {subfield()}</div>"
                    )
                else:
                    html.append(
                        f"<div class={self.col_class}>{subfield()} {subfield.label}</div>"
                    )
        html.append("</%s>" % self.html_tag)
        return Markup("".join(html))


from wtforms import StringField

class AdvancedForm(Form):
    # Hidden field to store data subject types as comma-separated values (using StringField to avoid URL validation)
    data_subject_types = StringField(
        "Data Subject Types",
        validators=[Optional()],
        render_kw={"class": "form-control d-none", "id": "data-subject-types-hidden"},
        default=f"{maptomethod.OA.Annotation},{maptomethod.CSVW.Column}",
        description="Types to query for subjects in data document.",
    )
    
    mapping_predicate_uri = URLField(
        "URL Mapping Predicat",
        # validators=[DataRequired(),URL()],
        render_kw={"class": "form-control"},
        default=maptomethod.ContentToBearingRelation,
        description="URI of object property to use as predicate.",
    )
    
    # Hidden field to store template object types as comma-separated values (using StringField to avoid URL validation)
    template_object_types = StringField(
        "Template Object Types",
        validators=[Optional()],
        render_kw={"class": "form-control d-none", "id": "template-object-types-hidden"},
        default=f"{maptomethod.InformtionContentEntity},{maptomethod.TemporalRegionClass}",
        description="Types to query for objects in template document.",
    )


class StartForm(StarletteForm):
    data_url = URLField(
        "URL Meta Data",
        # validators=[DataRequired(),URL()],
        render_kw={
            "placeholder": "https://github.com/Mat-O-Lab/CSVToCSVW/raw/main/examples/example-metadata.json",
            "class": "form-control",
        },
        description="Paste URL to meta data json file create from CSVToCSVW",
    )
    template_url = URLField(
        "URL Template Data",
        render_kw={
            "placeholder": "https://raw.githubusercontent.com/Mat-O-Lab/MSEO/main/methods/DIN_EN_ISO_527-3.drawio.ttl",
            "class": "form-control"
        },
        validators=[Optional(), URL()],
        description="Paste URL to template graph create with MSEO",
    )
    # disabled uing d-none bootrap class
    use_template_rowwise = BooleanField(
        "Duplicate Template for Table Data",
        render_kw={
            "class": "form-check form-check-input form-control-lg",
            "role": "switch",
        },
        description="Check to duplicate the template template for each row in the table.",
        default=False,
    )
    advanced = FormField(
        AdvancedForm, render_kw={"class": "collapse"}, widget=ListWidgetBootstrap()
    )


class SelectForm(Form):
    select = SelectField(
        "Placeholder",
        default=(0, "None"),
        choices=[],
        validate_choice=False,
        render_kw={"class": "form-control col-s-3"},
    )


class MappingFormList(StarletteForm):
    assignments = FieldList(
        FormField(SelectForm, render_kw={"class": "form-control"}),
        widget=ListWidgetBootstrap(col_class="col-sm-4"),
        render_kw={"class": "row"},
    )


def get_select_entries(objects_dict: dict, choices: List, abbreviate_fn=None) -> List[SelectForm]:
    """Converts custom metadata to a forms.SelectForm(), which can then be
    used by SelectFormlist() to dynamically render select items.

    Args:
        objects_dict (dict): Dict of objects with their metadata including types
        choices (List): List of choices for the selects
        abbreviate_fn (callable): Function to abbreviate IRIs

    Returns:
        List[SelectForm]: _description_
    """
    all_select_items = []
    for name, value in objects_dict.items():
        _id = uuid.uuid1()  # allows for multiple selects
        select_form = SelectForm()
        
        # Create label with type badge
        entity_type = value.get("type") if isinstance(value, dict) else None
        if entity_type and abbreviate_fn:
            type_abbrev = abbreviate_fn(entity_type)
            # Extract prefix for color coding
            prefix = type_abbrev.split('#')[0] if '#' in type_abbrev else type_abbrev.split(':')[0]
            # Create HTML with badge - will be colored by JavaScript
            label_html = Markup(f'{name} <span class="badge type-badge" data-prefix="{prefix}" title="{entity_type}">{type_abbrev}</span>')
            select_form.select.label = label_html
        else:
            select_form.select.label = name
            
        select_form.select.name = name
        select_form.select.id = f"{name}-{_id}"
        select_form.select.choices = choices
        all_select_items.append(select_form)
    return all_select_items
