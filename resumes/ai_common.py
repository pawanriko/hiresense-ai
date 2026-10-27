"""Shared validation for the AI providers (Groq, Gemini).

WHY THIS MODULE EXISTS: both providers answer the same three questions
(criteria draft, interview questions, answer score) with the same JSON
shapes, and the views only accept one contract. Validating in one place
means a new provider cannot accidentally loosen the contract — a bad
reply from ANY provider returns None, and the caller falls back to the
deterministic path.

Nothing here talks to the network. Provider modules (resumes/groq.py,
resumes/gemini.py) own the transport and the prompts; they hand the
parsed JSON to these validators and return the result (or None).
"""

import math

CRITERION_CATEGORIES = {"skill", "tool", "language", "education", "soft"}
ANSWER_SCORE_KEYS = (
    "relevance",
    "depth",
    "structure",
    "confidence",
    "conciseness",
)


def _round_half_up(value):
    """Halves go up, matching JS Math.round (see scoring.js_round)."""
    return math.floor(value + 0.5)


def _parse_json_object(text):
    """Parse a JSON object out of model text, tolerating ```json fences.
    Returns the dict, or None when the text is not a JSON object."""
    if not text:
        return None
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").strip()
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
    try:
        import json

        parsed = json.loads(cleaned)
    except (ValueError, TypeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _clamp_score(value):
    """Coerce an AI subscore to an int in 0..100, or None if unusable."""
    try:
        number = int(value)
    except (TypeError, ValueError):
        try:
            number = int(float(value))
        except (TypeError, ValueError):
            return None
    return max(0, min(100, number))


def _normalize_weights(criteria):
    """Scale weights to sum exactly 100, largest criterion absorbing the
    rounding — the same rule as the heuristic draft in scoring.py."""
    total = sum(c["weight"] for c in criteria)
    if total <= 0:
        return None
    normalised = []
    acc = 0
    for i, criterion in enumerate(criteria):
        if i == len(criteria) - 1:
            normalised.append({**criterion, "weight": 100 - acc})
        else:
            weight = _round_half_up(criterion["weight"] / total * 100)
            acc += weight
            normalised.append({**criterion, "weight": weight})
    normalised.sort(key=lambda c: c["weight"], reverse=True)
    return normalised


def validate_criteria_rows(rows):
    """Validate an AI criteria list into the heuristic draft's exact
    shape ({name, category, weight, required}, weights summing to 100,
    at most 12, heaviest first), or None when unusable. Bad categories
    fall back to "skill"; blank rows are dropped."""
    criteria = []
    for row in (rows or [])[:12]:
        if not isinstance(row, dict) or not str(row.get("name", "")).strip():
            continue
        try:
            weight = int(row.get("weight", 20))
        except (TypeError, ValueError):
            weight = 20
        category = row.get("category", "skill")
        criteria.append({
            "name": str(row["name"]).strip(),
            "category": category if category in CRITERION_CATEGORIES else "skill",
            "weight": max(0, weight),
            "required": bool(row.get("required", False)),
        })
    if not criteria:
        return None
    return _normalize_weights(criteria)


def validate_question_rows(rows, track):
    """Validate an AI question list into the bank's item shape
    ({question, topic}), exactly 5. Fewer than 5 usable questions
    returns None — the session invariant is 5 questions, so a short
    reply must fall back to the bank, not start a short session."""
    questions = []
    for row in rows or []:
        if not isinstance(row, dict) or not str(row.get("question", "")).strip():
            continue
        questions.append({
            "question": str(row["question"]).strip(),
            "topic": str(row.get("topic") or track).strip(),
        })
    if len(questions) < 5:
        return None
    return questions[:5]


def validate_answer_scores(parsed):
    """Validate an AI answer score into the checklist dict's exact
    shape (five subscores, overall, feedback), or None when any
    subscore is missing or unusable. Overall uses the checklist's
    rubric weights (30/25/20/15/10)."""
    if not isinstance(parsed, dict):
        return None
    scores = {}
    for key in ANSWER_SCORE_KEYS:
        value = _clamp_score(parsed.get(key))
        if value is None:
            return None
        scores[key] = value
    feedback = parsed.get("feedback", "")
    scores["overall"] = _round_half_up(
        scores["relevance"] * 0.3 + scores["depth"] * 0.25
        + scores["structure"] * 0.2 + scores["confidence"] * 0.15
        + scores["conciseness"] * 0.1
    )
    scores["feedback"] = str(feedback) if feedback else (
        "AI feedback was empty — the checklist scorer has the detail."
    )
    return scores
