"""Forms for the resumes app.

WHAT A FORM IS: Django's way to take user input, validate it, and hand you
clean data. A Form (unlike a ModelForm) is not tied to a database table —
we use a plain Form here because uploading involves extra steps (extract
text, score it) before anything is saved, so the view stays in control.

VALIDATION: ``clean_file`` runs automatically when the form is validated.
Raising ValidationError there shows a friendly error on the page instead
of crashing the upload.
"""

from django import forms


class ResumeUploadForm(forms.Form):
    file = forms.FileField(
        label="Resume file (PDF or DOCX)",
        help_text="Only PDF and DOCX resumes are supported.",
    )

    def clean_file(self):
        uploaded = self.cleaned_data["file"]
        name = uploaded.name.lower()
        if not (name.endswith(".pdf") or name.endswith(".docx")):
            raise forms.ValidationError(
                "Only PDF and DOCX resumes are supported."
            )
        return uploaded
