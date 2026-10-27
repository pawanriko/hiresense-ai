"""Views for the resumes app.

WHAT A VIEW IS: a function that takes a request and returns a response.
The typical shape: read input -> do work -> render a template with context.
``@login_required`` is a decorator (a wrapper) that sends anonymous visitors
to the login page instead of running the view at all.

FLOW FOR AN UPLOAD:
1. GET  -> show the empty upload form.
2. POST -> validate the form, extract text, split it into sections,
   compute the ATS score, save a Resume row, redirect to the result page.
   (Redirect-after-POST is a Django habit: it stops the browser from
   re-uploading the file if the user refreshes the result page.)
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .extract import extract_text
from .forms import ResumeUploadForm
from .models import Resume
from .scoring import compute_ats, segment_sections


@login_required
def upload(request):
    if request.method == "POST":
        form = ResumeUploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded = form.cleaned_data["file"]
            # NOTE: extract first, because a corrupt file should fail before
            # we save anything — the user gets an error, not a broken row.
            text = extract_text(uploaded, uploaded.name)
            sections = segment_sections(text)
            result = compute_ats(sections, text)
            resume = Resume.objects.create(
                owner=request.user,
                file=uploaded,
                original_name=uploaded.name,
                extracted_text=text,
                ats_score=result["score"],
                breakdown=result,
            )
            return redirect("resumes:result", pk=resume.pk)
    else:
        form = ResumeUploadForm()
    return render(request, "resumes/upload.html", {"form": form})


@login_required
def result(request, pk):
    # owner=request.user means: you can only open your OWN resumes.
    # Anyone else's id gives a 404, which leaks nothing about its existence.
    resume = get_object_or_404(Resume, pk=pk, owner=request.user)
    return render(request, "resumes/result.html", {"resume": resume})
