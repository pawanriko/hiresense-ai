"""Groq provider — one of the app's LLM contacts (see ai_provider.py
for how a provider is chosen, and ai_common.py for the shared
validation every provider's replies go through).

Mirrors the original app's ``lib/ai/groq.ts``: one small client plus
one function per AI feature, all gated on GROQ_API_KEY.

TWO STATES, BY DESIGN (same pattern as Google OAuth in settings.py):
  * GROQ_API_KEY absent (the default): ``is_groq_configured()`` is False
    and this provider is never called.
  * GROQ_API_KEY set (e.g. in .env): the dispatch in ai_provider.py may
    call these functions, and any failure returns None — the caller
    then runs its deterministic fallback. An AI failure NEVER crashes a
    page: ``groq_chat`` catches every transport/parse error.

WHAT AI DOES AND DOES NOT DECIDE — the boundary matters, so it is
stated here and in the README, not buried in a view:
  * AI drafts criteria, generates interview questions, and scores
    answers with feedback. Those are drafts and feedback, always shown
    as such, and the candidate edits criteria before any scoring.
  * AI NEVER computes a match score or an ATS score. Those stay
    deterministic (see resumes/scoring.py): the same input always gives
    the same output, which is the whole point of an explainable score.

NO NEW DEPENDENCIES: the client is stdlib ``urllib`` only, so Windows
setup stays ``pip install -r requirements.txt`` with nothing extra.
"""

import json
import urllib.request

from django.conf import settings

from .ai_common import (
    _parse_json_object,
    validate_answer_scores,
    validate_criteria_rows,
    validate_question_rows,
)

# Re-exported so existing imports (and tests) keep working:
# ``from resumes.groq import _parse_json_object``.
__all__ = [
    "_parse_json_object",
    "extract_criteria_ai",
    "groq_chat",
    "interview_questions_ai",
    "is_groq_configured",
    "score_answer_ai",
]

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "llama-3.3-70b-versatile"
REQUEST_TIMEOUT_SECONDS = 30


def is_groq_configured():
    """True when a Groq key is set — the single switch for this provider."""
    return bool(getattr(settings, "GROQ_API_KEY", ""))


def groq_chat(system, user):
    """One Groq chat completion. Returns the reply text, or None on ANY
    failure — callers treat None as 'run the deterministic fallback'."""
    key = getattr(settings, "GROQ_API_KEY", "")
    if not key:
        return None
    body = json.dumps({
        "model": getattr(settings, "GROQ_MODEL", DEFAULT_MODEL),
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }).encode("utf-8")
    request = urllib.request.Request(
        GROQ_API_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return payload["choices"][0]["message"]["content"]
    except Exception:
        # Deliberately broad: network error, bad key, rate limit, bad
        # JSON, unexpected shape — all mean the same thing here, which
        # is 'fall back'. Surfacing any of them would break a page that
        # works fine without AI.
        return None


def extract_criteria_ai(title, company, jd_text):
    """Draft JD criteria with Groq. Returns a list of
    {name, category, weight, required} in the heuristic draft's exact
    shape (so the JD detail page edits it the same way), or None when
    the AI path fails — the caller then uses the heuristic draft."""
    text = groq_chat(
        "Draft job criteria from a job description. Return ONLY a JSON "
        "object {\"criteria\": [{\"name\": string, \"category\": string, "
        "\"weight\": number, \"required\": boolean}, ...]} with at most 12 "
        "criteria. Category must be one of: skill, tool, language, "
        "education, soft. Weights are relative importance; they do not "
        "need to sum to 100. Never invent requirements the JD does not "
        "state.",
        json.dumps({
            "title": title,
            "company": company,
            "jd": jd_text[:4000],
        }),
    )
    parsed = _parse_json_object(text)
    if not parsed:
        return None
    return validate_criteria_rows(parsed.get("criteria"))


def interview_questions_ai(track, difficulty, jd_text, company):
    """Generate exactly 5 interview questions for a track + difficulty,
    grounded in the JD and the company. Returns a list of
    {question, topic} — the bank's item shape — or None when the AI path
    fails or returns fewer than 5 usable questions, so the caller falls
    back to the bank and the '5 questions' invariant never breaks."""
    text = groq_chat(
        "Generate a mock interview question set. Return ONLY a JSON "
        "object {\"questions\": [{\"question\": string, \"topic\": string}, "
        "...]} with exactly 5 questions for the given track and "
        "difficulty, grounded in the job description and company (no "
        "invented candidate facts in the questions themselves). Mix "
        "JD-based and fundamentals questions.",
        json.dumps({
            "track": track,
            "difficulty": difficulty,
            "company": company,
            "jd": (jd_text or "")[:3000],
        }),
    )
    parsed = _parse_json_object(text)
    if not parsed:
        return None
    return validate_question_rows(parsed.get("questions"), track)


def score_answer_ai(question, answer):
    """Score one interview answer with Groq, on the checklist's rubric
    (relevance 30, depth 25, structure 20, confidence 15, conciseness
    10). Returns the checklist dict's exact shape — the five subscores,
    overall, and feedback — or None when the AI path fails, so the
    caller falls back to the checklist scorer."""
    text = groq_chat(
        "Score a mock interview answer. Return ONLY a JSON object "
        "{\"relevance\": number, \"depth\": number, \"structure\": number, "
        "\"confidence\": number, \"conciseness\": number, \"feedback\": "
        "string} with each score 0-100 and one concrete feedback "
        "sentence naming what to improve. Relevance: does the answer "
        "address the question's topic. Depth: concrete examples and "
        "detail. Structure: clear order (situation, action, result). "
        "Confidence: direct, assured tone, not hedging. Conciseness: "
        "lands the point without rambling.",
        json.dumps({"question": question, "answer": answer[:3000]}),
    )
    parsed = _parse_json_object(text)
    if not parsed:
        return None
    return validate_answer_scores(parsed)
