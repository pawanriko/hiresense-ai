"""Provider dispatch — the views call THESE functions, never a provider
module directly. That is what makes a second provider a small change
instead of a rewrite: the views ask for "AI criteria" and this module
decides which provider answers.

WHICH PROVIDER RUNS (settings.AI_PROVIDER + the two keys):
  * AI_PROVIDER = "groq" or "gemini": that provider is PINNED. If its
    key is missing, the answer is None — no silent switch to the other
    provider, because an explicit choice should mean something. The
    caller then runs its deterministic fallback.
  * AI_PROVIDER unset (the default) or an unknown value: Groq first if
    its key is set, else Gemini if its key is set, else None. Groq
    wins the default only because it was the first provider; both are
    equal citizens otherwise.
  * No keys at all: None, and the app behaves exactly as it did before
    any AI module existed.

The dispatch never raises: a provider function returning None flows
straight through to the caller's fallback, same as a provider failure.
"""

from django.conf import settings

from . import gemini, groq

_PROVIDERS = {
    "groq": (groq, groq.is_groq_configured),
    "gemini": (gemini, gemini.is_gemini_configured),
}


def _active_provider():
    """The provider module to use, or None when no provider applies."""
    pinned = str(getattr(settings, "AI_PROVIDER", "") or "").strip().lower()
    if pinned in _PROVIDERS:
        module, is_configured = _PROVIDERS[pinned]
        return module if is_configured() else None
    for name in ("groq", "gemini"):
        module, is_configured = _PROVIDERS[name]
        if is_configured():
            return module
    return None


def is_ai_configured():
    """True when some provider is available for the views to try."""
    return _active_provider() is not None


def extract_criteria(title, company, jd_text):
    """AI criteria draft from the active provider, or None."""
    provider = _active_provider()
    if provider is None:
        return None
    return provider.extract_criteria_ai(title, company, jd_text)


def interview_questions(track, difficulty, jd_text, company):
    """AI interview questions from the active provider, or None."""
    provider = _active_provider()
    if provider is None:
        return None
    return provider.interview_questions_ai(track, difficulty, jd_text, company)


def score_answer(question, answer):
    """AI answer score from the active provider, or None."""
    provider = _active_provider()
    if provider is None:
        return None
    return provider.score_answer_ai(question, answer)
