"""Gemini provider — the second of the app's LLM contacts (see
ai_provider.py for how a provider is chosen, and ai_common.py for the
shared validation every provider's replies go through).

Same contract as resumes/groq.py: one small client plus one function
per AI feature, gated on GEMINI_API_KEY, with the same failure rule —
any failure returns None and the caller falls back to the deterministic
path. The two providers differ only in transport and prompts; the
views cannot tell them apart.

TRANSPORT NOTES (Google AI Studio / Gemini API, v1beta):
  * The key travels in the ``x-goog-api-key`` header, never in the URL
    — URLs land in logs, headers do not.
  * The system prompt goes in ``systemInstruction``; the user payload
    goes in ``contents``. ``responseMimeType: application/json`` asks
    the model for JSON directly, but replies are still validated —
    a mime hint is not a guarantee.
  * A blocked or empty reply (no candidates) is a normal None, not an
    error to surface: the page works fine without AI.

NO NEW DEPENDENCIES: stdlib ``urllib`` only, like the Groq provider.
Get a key at aistudio.google.com.
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

__all__ = [
    "extract_criteria_ai",
    "gemini_chat",
    "interview_questions_ai",
    "is_gemini_configured",
    "score_answer_ai",
]

DEFAULT_MODEL = "gemini-2.0-flash"
REQUEST_TIMEOUT_SECONDS = 30


def is_gemini_configured():
    """True when a Gemini key is set — the single switch for this provider."""
    return bool(getattr(settings, "GEMINI_API_KEY", ""))


def _api_url():
    model = getattr(settings, "GEMINI_MODEL", DEFAULT_MODEL)
    return (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent"
    )


def gemini_chat(system, user):
    """One Gemini generation. Returns the reply text, or None on ANY
    failure — callers treat None as 'run the deterministic fallback'."""
    key = getattr(settings, "GEMINI_API_KEY", "")
    if not key:
        return None
    body = json.dumps({
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"parts": [{"text": user}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }).encode("utf-8")
    request = urllib.request.Request(
        _api_url(),
        data=body,
        headers={
            "x-goog-api-key": key,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
        parts = payload["candidates"][0]["content"]["parts"]
        text = "".join(part.get("text", "") for part in parts)
        return text or None
    except Exception:
        # Deliberately broad, same rule as the Groq provider: every
        # failure mode means 'fall back', never 'break the page'.
        return None


def extract_criteria_ai(title, company, jd_text):
    """Draft JD criteria with Gemini. Same contract as the Groq
    version: {name, category, weight, required} list, or None."""
    text = gemini_chat(
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
    """Generate exactly 5 interview questions with Gemini, grounded in
    the JD and the company. Same contract as the Groq version: a list
    of {question, topic}, or None (fallback to the bank)."""
    text = gemini_chat(
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
    """Score one interview answer with Gemini, on the checklist's
    rubric. Same contract as the Groq version: the checklist dict's
    exact shape, or None (fallback to the checklist scorer)."""
    text = gemini_chat(
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
