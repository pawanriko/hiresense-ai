"""Mock-interview question bank and answer checklist scorer — ported from
the original app's ``lib/interview/questions.ts``.

WHAT THIS IS: the deterministic engine, plus the report math both
scorers share. ``pick_questions`` always returns the same set for a
track + difficulty, and ``score_answer_checklist`` scores an answer
with fixed rules, labelled as checklist feedback. The AI paths live in
resumes/ai_provider.py (Groq or Gemini) and are tried first only when
a provider key is configured (see the interview views) — the bank and
the checklist remain the fallback, so the app works fully without any
key.

THE REGRESSION THIS FIXED: relevance used to be measured ONLY against the
topic label word (e.g. "ownership" for a project question), so a strong
answer that never said the label word scored 0 relevance. Now the question's
own content words count too, and the better of the two rates wins.
"""

import re

TRACKS = ["HR", "Technical", "DSA", "Frontend"]

# track -> list of {question, topic, difficulty}. Kept in full so slice 2's
# Interview page can use the bank as-is.
BANK = {
    "HR": [
        {"question": "Tell me about yourself — walk me through your background in under two minutes.", "topic": "Introduction", "difficulty": "easy"},
        {"question": "Why do you want this role, and why this company?", "topic": "Motivation", "difficulty": "easy"},
        {"question": "Describe a project you are most proud of. What was your exact contribution?", "topic": "Ownership", "difficulty": "medium"},
        {"question": "Tell me about a time you failed or got stuck. What did you change afterwards?", "topic": "Resilience", "difficulty": "medium"},
        {"question": "Describe a disagreement in a team setting and how you handled it.", "topic": "Teamwork", "difficulty": "medium"},
        {"question": "Where do you see yourself in two years, and how does this role fit?", "topic": "Goals", "difficulty": "easy"},
        {"question": "What is a weakness you are actively working on, with an example?", "topic": "Self-awareness", "difficulty": "hard"},
        {"question": "Do you have any questions for us?", "topic": "Curiosity", "difficulty": "easy"},
    ],
    "Technical": [
        {"question": "Explain how a web request travels from the browser to the database and back.", "topic": "Web fundamentals", "difficulty": "easy"},
        {"question": "What is the difference between SQL and NoSQL databases, and when would you pick each?", "topic": "Databases", "difficulty": "medium"},
        {"question": "Explain REST vs GraphQL. Which would you choose for a dashboard app and why?", "topic": "APIs", "difficulty": "medium"},
        {"question": "How would you debug a page that loads slowly in production?", "topic": "Debugging", "difficulty": "medium"},
        {"question": "What happens when you run a query with no index on a large table?", "topic": "Databases", "difficulty": "hard"},
        {"question": "Design a rate limiter for an API. What data structure and storage would you use?", "topic": "System design", "difficulty": "hard"},
        {"question": "How do you keep secrets out of a codebase and out of git history?", "topic": "Security", "difficulty": "medium"},
        {"question": "Explain authentication vs authorization, with an example of each.", "topic": "Security", "difficulty": "easy"},
    ],
    "DSA": [
        {"question": "Given an array of numbers, how would you find two that sum to a target? Walk through your approach and its complexity.", "topic": "Arrays & hashing", "difficulty": "easy"},
        {"question": "Reverse a linked list. Explain your approach before writing any steps.", "topic": "Linked lists", "difficulty": "easy"},
        {"question": "How would you detect a cycle in a linked list without extra memory?", "topic": "Linked lists", "difficulty": "medium"},
        {"question": "Explain the difference between a stack and a queue, and give one real use of each.", "topic": "Data structures", "difficulty": "easy"},
        {"question": "You have a sorted array rotated at an unknown pivot. How do you search it efficiently?", "topic": "Binary search", "difficulty": "medium"},
        {"question": "When would you use a heap instead of sorting an array? Give an example.", "topic": "Heaps", "difficulty": "medium"},
        {"question": "Explain dynamic programming in one example you have actually solved.", "topic": "DP", "difficulty": "hard"},
        {"question": "How do you decide between BFS and DFS for a graph problem?", "topic": "Graphs", "difficulty": "hard"},
    ],
    "Frontend": [
        {"question": "Explain the difference between state and props in React, with an example.", "topic": "React", "difficulty": "easy"},
        {"question": "What happens when you call setState? Why is it asynchronous?", "topic": "React", "difficulty": "medium"},
        {"question": "How would you build a form with validation that is also accessible?", "topic": "Forms & a11y", "difficulty": "medium"},
        {"question": "Explain the CSS box model and why margin collapsing surprises people.", "topic": "CSS", "difficulty": "easy"},
        {"question": "How do you decide between client-side rendering and server-side rendering?", "topic": "Rendering", "difficulty": "medium"},
        {"question": "A list of 10,000 rows renders slowly. What do you do?", "topic": "Performance", "difficulty": "hard"},
        {"question": "What is the difference between useMemo, useCallback, and useEffect? When would you skip all three?", "topic": "React hooks", "difficulty": "hard"},
        {"question": "How would you structure a small app so a new feature doesn't break old screens?", "topic": "Architecture", "difficulty": "medium"},
    ],
}


def pick_questions(track, difficulty, count=5):
    """Return ``count`` questions for a track, ordered by difficulty.

    The order puts the requested difficulty first, then the neighbours:
    easy -> easy, medium, hard; hard -> hard, medium, easy; anything else
    (medium) -> medium, easy, hard. Python's sort is stable, so questions
    keep their bank order inside each difficulty — same as the original.
    """
    questions = BANK.get(track, BANK["HR"])
    if difficulty == "easy":
        order = ["easy", "medium", "hard"]
    elif difficulty == "hard":
        order = ["hard", "medium", "easy"]
    else:
        order = ["medium", "easy", "hard"]
    ordered = sorted(questions, key=lambda q: order.index(q["difficulty"]))
    return ordered[:count]


# Words that signal STAR-style structure (Situation, Task, Action, Result).
STAR_WORDS = ["situation", "task", "action", "result", "first", "then",
              "finally", "because", "so we"]

# Generic question words that carry no topic signal — excluded when deriving
# keywords from the question itself.
QUESTION_STOPWORDS = {
    "tell", "describe", "explain", "about", "your", "you", "what", "when",
    "where", "which", "would", "should", "could", "walk", "through",
    "under", "minutes", "difference", "between", "example", "given",
    "before", "writing", "steps", "approach", "discuss", "share", "think",
}


def _js_round(value):
    """Same rounding as scoring.js_round: halves go up."""
    import math
    return math.floor(value + 0.5)


def score_answer_checklist(question, answer, topic_keywords):
    """Score one interview answer with fixed checklist rules.

    Returns relevance, depth, structure, confidence, conciseness, overall
    (weights 30/25/20/15/10), and a feedback sentence. Weights and thresholds
    are ported exactly from the original — change them here and in the
    original together, or the two apps will grade the same answer differently.
    """
    text = answer.lower()
    words = len(answer.split())

    # Relevance: better of (topic-keyword hit rate, question-word hit rate).
    topic_keywords = [k.lower() for k in topic_keywords]
    topic_rate = None
    if topic_keywords:
        hits = sum(1 for k in topic_keywords if k in text)
        topic_rate = hits / len(topic_keywords)
    question_keywords = [
        w for w in re.split(r"[^a-z]+", question.lower())
        if len(w) >= 4 and w not in QUESTION_STOPWORDS
    ]
    question_rate = None
    if question_keywords:
        hits = sum(1 for k in question_keywords if k in text)
        question_rate = hits / len(question_keywords)
    if topic_rate is None and question_rate is None:
        relevance = 60
    else:
        relevance = _js_round(max(topic_rate or 0, question_rate or 0) * 100)

    # Depth is purely length-based: short answers cannot show depth.
    if words < 20:
        depth = 30
    elif words < 60:
        depth = 60
    elif words < 150:
        depth = 85
    else:
        depth = 95

    # Structure: STAR words, capped at 100 (30 base + 15 per word found).
    star_hits = sum(1 for w in STAR_WORDS if w in text)
    structure = min(100, 30 + star_hits * 15)

    # Confidence: strong opening ("I built...") scores high; hedging scores low.
    if re.match(r"^(i|we)\s+(built|designed|led|delivered|improved)", text):
        confidence = 80
    elif "i think" in text or "maybe" in text:
        confidence = 45
    else:
        confidence = 65

    # Conciseness: an interview answer should land, not ramble.
    if words <= 180:
        conciseness = 90
    elif words <= 300:
        conciseness = 70
    else:
        conciseness = 45

    overall = _js_round(
        relevance * 0.3 + depth * 0.25 + structure * 0.2
        + confidence * 0.15 + conciseness * 0.1
    )

    if words < 20:
        feedback = ("Too short to judge depth — expand with a concrete example: "
                    "what you did, and what changed.")
    elif relevance < 30:
        feedback = ("The answer drifts from the question's topic — anchor the "
                    "first sentence directly to what was asked, then give one example.")
    else:
        feedback = ("Solid structure. To push higher, add one measurable outcome "
                    "to your example (a number, a before/after, or a user impact).")

    return {
        "relevance": relevance,
        "depth": depth,
        "structure": structure,
        "confidence": confidence,
        "conciseness": conciseness,
        "overall": overall,
        "feedback": feedback,
    }


def topic_keywords(topic):
    """Topic-label words for the relevance check, exactly as the original
    derives them: lowercase the topic label and split on anything that is
    not a letter. "Ownership" -> ["ownership"]; "Arrays & hashing" ->
    ["arrays", "hashing"]. The scorer then takes the better of this rate
    and the question-word rate, so a label-only miss cannot zero relevance.
    """
    return [w for w in re.split(r"[^a-z]+", topic.lower()) if w]


def build_report(answered):
    """Build the final session report from answered transcript items.

    Ported from the original answer route: overall = rounded mean of the
    per-answer overalls; topic_scores = rounded mean per topic; weakest
    areas = the 2 lowest-scoring topics; weakest question = the lowest
    overall answer (first one wins ties, as with the original's stable
    sort). feedback_source derives from each answered item's "source"
    ("ai" or "checklist"; items from before sources were tracked carry
    no source and read as checklist): all AI -> "ai", a mix -> "mixed",
    otherwise "checklist".

    ``answered`` is a list of transcript items with non-None overall.
    Returns (overall_score, report_dict).
    """
    if not answered:
        return None, {
            "topic_scores": [],
            "weakest_areas": [],
            "weakest_question": None,
            "feedback_source": "checklist",
        }
    sources = {item.get("source") for item in answered}
    if sources == {"ai"}:
        feedback_source = "ai"
    elif "ai" in sources:
        feedback_source = "mixed"
    else:
        feedback_source = "checklist"
    overall_score = _js_round(
        sum(item["overall"] for item in answered) / len(answered)
    )
    by_topic = {}
    for item in answered:
        by_topic.setdefault(item["topic"], []).append(item["overall"])
    topic_scores = [
        {"topic": topic, "score": _js_round(sum(vals) / len(vals))}
        for topic, vals in by_topic.items()
    ]
    # sorted() is stable like the original's sort, so ties keep transcript
    # order and the weakest areas/question match the original's picks.
    weakest = sorted(topic_scores, key=lambda t: t["score"])[:2]
    weakest_question = min(answered, key=lambda item: item["overall"])
    return overall_score, {
        "topic_scores": topic_scores,
        "weakest_areas": [w["topic"] for w in weakest],
        "weakest_question": weakest_question,
        "feedback_source": feedback_source,
    }
