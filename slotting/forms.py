"""
forms.py
----------
Two dynamic form builders, both driven by the same config objects the
Tkinter and Streamlit UIs use (app/config.py's FieldSpec / AnalysisOption)
- no schema is duplicated here.

build_record_form(table_config): a form for adding/editing one row of a
table. Every field is a CharField (even "int"/"date"/etc.) so the value
stays a plain string end-to-end - real type/required validation is left
to DataManager._validate(), exactly like the Tkinter and Streamlit UIs
do, so there's only one place that validation logic lives.

build_run_form(analysis_config): the date-range + options form shown
before running any analysis/report.
"""

from django import forms


def build_record_form(table_config):
    fields = {}
    for f in table_config.fields:
        if f.type == "choice" and f.choices:
            choices = [("", "-- select --")] + [(c, c) for c in f.choices]
            fields[f.name] = forms.ChoiceField(
                label=f.label, choices=choices, required=False,
                widget=forms.Select(attrs={"class": "form-select"}),
                help_text=f.help,
            )
            continue

        attrs = {"class": "form-control"}
        if f.type in ("int", "float"):
            widget = forms.NumberInput(attrs={**attrs, "step": "any" if f.type == "float" else "1"})
        elif f.type == "date":
            widget = forms.TextInput(attrs={**attrs, "placeholder": "YYYY-MM-DD"})
        elif f.type == "datetime":
            widget = forms.TextInput(attrs={**attrs, "placeholder": "YYYY-MM-DD HH:MM"})
        elif f.type == "email":
            widget = forms.EmailInput(attrs=attrs)
        else:
            widget = forms.TextInput(attrs=attrs)

        fields[f.name] = forms.CharField(
            label=f.label, required=False, widget=widget, help_text=f.help,
        )

    return type(f"{table_config.key.title()}RecordForm", (forms.Form,), fields)


def build_run_form(analysis_config):
    fields = {
        "start": forms.DateField(
            label="Start", required=True,
            widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        ),
        "end": forms.DateField(
            label="End", required=True,
            widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        ),
    }
    for opt in analysis_config.options:
        field_name = f"opt_{opt.name}"
        if opt.type == "choice" and opt.choices:
            fields[field_name] = forms.ChoiceField(
                label=opt.label, choices=[(c, c) for c in opt.choices],
                initial=opt.default, required=False,
                widget=forms.Select(attrs={"class": "form-select"}), help_text=opt.help,
            )
        elif opt.type == "int":
            fields[field_name] = forms.IntegerField(
                label=opt.label, initial=int(float(opt.default)) if opt.default else 0, required=False,
                widget=forms.NumberInput(attrs={"class": "form-control"}), help_text=opt.help,
            )
        elif opt.type == "float":
            fields[field_name] = forms.FloatField(
                label=opt.label, initial=float(opt.default) if opt.default else 0.0, required=False,
                widget=forms.NumberInput(attrs={"class": "form-control", "step": "any"}), help_text=opt.help,
            )
        else:
            fields[field_name] = forms.CharField(
                label=opt.label, initial=opt.default, required=False,
                widget=forms.TextInput(attrs={"class": "form-control"}), help_text=opt.help,
            )

    return type(f"{analysis_config.key.title()}RunForm", (forms.Form,), fields)
