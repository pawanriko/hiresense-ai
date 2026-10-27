"""Forms for the applications app.

TWO FORMS, mirroring the original's two write endpoints:

1. ApplicationForm — a tracker row. Company and role are required (the
   original rejects a row without them with a 400); status must be one
   of the four pipeline stages (the model's choices enforce this, and
   an invalid choice fails validation instead of crashing); notes and
   the JD link are optional. The JD dropdown's queryset is set
   per-request in the view, because a form cannot know the current user
   on its own — the same pattern slice 2 uses for its resume dropdown.
2. GapTaskForm — a manual checklist task. Title is required and capped
   at 200 characters (the original slices titles at 200 on insert);
   source_gap is optional because a hand-typed task has no gap behind it.
"""

from django import forms

from jdmatch.models import JobDescription

from .models import Application, GapTask


class ApplicationForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ["company", "role", "status", "notes", "jd"]
        labels = {"jd": "Linked job description (optional)"}

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Only the user's own JDs may be linked — another user's JD must
        # never appear in the dropdown, even if its id is guessed.
        if user is not None:
            self.fields["jd"].queryset = JobDescription.objects.filter(
                owner=user
            )
        self.fields["jd"].required = False


class GapTaskForm(forms.Form):
    title = forms.CharField(
        max_length=200, label="Task, e.g. Build a React project"
    )
    source_gap = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2}),
        required=False,
        label="Why this task (optional)",
    )
