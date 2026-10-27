"""Forms for the jdmatch app.

THREE FORMS, ONE PER USER ACTION (mirroring the original page's three
sections: 1 · Job description, 2 · Criteria, 3 · Run the match):

1. JobDescriptionForm — paste a JD. Validation mirrors the original API:
   a title is required and the JD text must be at least 30 characters, so
   a two-word paste cannot produce meaningless criteria.
2. CriterionForm — one editable criterion row (name, category, weight,
   required). Used inside a formset on the JD detail page, so the user can
   edit, delete, and add rows before scoring. Category drives the gap
   fix-action template in ``resumes/scoring.py``.
3. RunMatchForm — pick one of the user's parsed resumes. The queryset is
   set per-request in the view (a form cannot know the current user on its
   own), and it only offers resumes with extracted text — the Django
   equivalent of the original's "parse_status == parsed" filter.
"""

from django import forms

from resumes.models import Resume

CATEGORY_CHOICES = [
    ("skill", "Skill"),
    ("tool", "Tool"),
    ("language", "Language"),
    ("education", "Education"),
    ("soft", "Soft skill"),
]


class JobDescriptionForm(forms.Form):
    title = forms.CharField(
        max_length=255, label="Role title, e.g. Frontend Intern"
    )
    company = forms.CharField(
        max_length=255, required=False, label="Company (optional)"
    )
    raw_text = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 7}),
        label="Paste the full job description here…",
    )

    def clean_raw_text(self):
        text = self.cleaned_data["raw_text"]
        if len(text.strip()) < 30:
            raise forms.ValidationError(
                "A job description of at least 30 characters is required."
            )
        return text


class CriterionForm(forms.Form):
    # NOTE: name and weight are required=False ON THE FORM, on purpose.
    # The formset's blank "add a criterion" row is always submitted by the
    # browser (a <select> always sends its category), so a truly blank row
    # still arrives with category set — Django would then reject it for a
    # missing name. Instead the form accepts blank rows and clean() below
    # enforces the real rule: a row WITH a name must also have a weight.
    # Rows with no name are dropped when saving (see _formset_to_criteria).
    name = forms.CharField(max_length=255, required=False, label="Criterion")
    category = forms.ChoiceField(choices=CATEGORY_CHOICES, label="Category")
    weight = forms.IntegerField(
        min_value=0, max_value=100, required=False, label="Weight",
        help_text="Weights are used as-is in the weighted average.",
    )
    required = forms.BooleanField(required=False, label="Required")

    def clean(self):
        data = super().clean()
        if data.get("name") and data.get("weight") is None:
            self.add_error(
                "weight", "Weight is required when a criterion name is given."
            )
        return data


class RunMatchForm(forms.Form):
    # Queryset starts empty and is replaced in the view with the current
    # user's parsed resumes. A form field cannot see request.user by itself.
    resume = forms.ModelChoiceField(
        queryset=Resume.objects.none(),
        label="Pick a resume…",
        empty_label="Pick a resume…",
    )
