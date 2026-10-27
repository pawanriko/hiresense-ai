"""Forms for the interview app (slice 3).

WHAT: a Django form validates user input and shows friendly errors —
the same job the original app's API validation did (e.g. "answer of at
least a few words"). Two forms here:

- StartSessionForm: track + difficulty pickers. The choices come from the
  ported question bank, so the page can never offer a track the bank does
  not have — an invalid value fails validation instead of crashing.
- AnswerForm: one textarea. Its clean() enforces the original's rule:
  a trimmed answer of at least 5 characters.
"""

from django import forms

from resumes.interview import TRACKS

DIFFICULTY_CHOICES = [
    ("easy", "Easy"),
    ("medium", "Medium"),
    ("hard", "Hard"),
]


class StartSessionForm(forms.Form):
    """Pick a track and a difficulty, then start a 5-question session.

    Company and JD text are optional context for AI questions: when an
    AI provider is configured, the generator grounds its 5 questions in
    the JD + company + track + difficulty; without a key (or when the
    AI call fails) the deterministic bank runs instead, ignoring both
    fields. Nothing about scoring changes either way — match and ATS
    scores stay deterministic, and answer feedback is checklist unless
    the AI scorer runs.
    """

    track = forms.ChoiceField(
        choices=[(track, track) for track in TRACKS],
        initial="HR",
        help_text="Question bank: HR, Technical, DSA, or Frontend.",
    )
    difficulty = forms.ChoiceField(
        choices=DIFFICULTY_CHOICES,
        initial="medium",
        help_text="Questions of this difficulty come first, then neighbours.",
    )
    company = forms.CharField(
        max_length=255,
        required=False,
        label="Company (optional)",
        help_text="Used for AI questions when a Groq key is configured.",
    )
    jd_text = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 5}),
        required=False,
        label="Job description (optional)",
        help_text="Paste the JD to ground AI questions in it. Ignored "
        "when questions come from the bank.",
    )


class AnswerForm(forms.Form):
    """One answer to the current question."""

    answer = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 6, "cols": 70}),
        help_text="Write at least a few words — short answers cannot show depth.",
    )

    def clean_answer(self):
        # CharField strips surrounding whitespace by default, so this
        # mirrors the original's `answer.trim()` before the length check.
        answer = self.cleaned_data["answer"]
        if len(answer) < 5:
            raise forms.ValidationError(
                "Please write an answer of at least a few words."
            )
        return answer
