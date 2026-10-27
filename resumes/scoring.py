"""Deterministic scoring for HireSense AI — ported from the original app.

WHAT THIS IS: pure functions (input in, answer out, no database, no network,
no AI). The same input always gives the same output, which is the whole
point: the AI never computes a score here. It may *draft* criteria, but the
numbers below come only from these rules.

WHERE IT CAME FROM: a line-by-line port of the original TypeScript in
``lib/scoring/`` (evidence, engine, ats, extract) and ``lib/parsing/``.
Rule changes belong in BOTH places until the old app is retired, or the two
apps will disagree about the same resume.

THREE SCORERS LIVE HERE:
1. ``segment_sections`` — split resume text into named sections (header,
   summary, skills, experience, ...).
2. ``score_resume`` — the JD Match rubric: 100 / 70 / 40 / 0 per criterion,
   then a weighted average.
3. ``compute_ats`` — a JD-independent resume health score (sections,
   quantification, action verbs, contact info, length/format).

A NOTE ON ROUNDING: JavaScript's Math.round() rounds halves UP (2.5 -> 3),
but Python's round() rounds halves to EVEN (2.5 -> 2). To keep scores
identical to the original app we use ``js_round`` everywhere the original
used Math.round.
"""

import math
import re

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def js_round(value):
    """Round like JavaScript's Math.round: halves go up (for non-negative
    numbers, which is all our scores ever are)."""
    return math.floor(value + 0.5)


def normalize(text):
    """Lowercase, then turn every character that is not a letter, digit, +,
    # or whitespace into a space, then collapse repeated spaces.

    This is what makes "React.js" match the criterion "react" — punctuation
    disappears before comparing, so matching is forgiving about formatting.
    """
    text = text.lower()
    text = re.sub(r"[^a-z0-9+#\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def split_sentences(text):
    """Split text into sentences/bullets.

    Splits on line breaks and bullet characters, and also after ``. ! ? ;``
    when whitespace follows. Short fragments (1 character) are dropped.
    Mirrors the original's split so evidence quotes line up.
    """
    parts = re.split(r"[\n\r•·\-–—]+|(?<=[.!?;])\s+", text)
    out = []
    for part in parts:
        cleaned = re.sub(r"\s+", " ", part).strip()
        if len(cleaned) > 1:
            out.append(cleaned)
    return out


# ---------------------------------------------------------------------------
# Section segmentation (original: lib/parsing/sections.ts)
# ---------------------------------------------------------------------------

# Heading text (after normalising) -> section name. A line is a heading only
# if it matches one of these EXACTLY, so "work experience" counts but
# "my work experience so far" does not — that keeps body text out of headings.
HEADINGS = {
    "contact": ["contact", "contact information", "personal details"],
    "summary": ["summary", "professional summary", "profile", "objective",
                "about me", "about"],
    "skills": ["skills", "technical skills", "core skills", "technologies",
               "tech stack", "key skills"],
    "experience": ["experience", "work experience", "professional experience",
                   "employment history", "internship experience", "internships"],
    "projects": ["projects", "personal projects", "key projects",
                 "academic projects", "side projects"],
    "education": ["education", "academic background", "qualifications",
                  "academics"],
    "certifications": ["certifications", "certificates", "courses",
                       "achievements", "awards"],
    "links": ["links", "profiles", "social links", "online profiles"],
}

SECTION_ORDER = ["header", "contact", "summary", "skills", "experience",
                 "projects", "education", "certifications", "links"]


def _normalize_heading(line):
    line = line.lower()
    line = re.sub(r"[^a-z\s]", "", line)
    line = re.sub(r"\s+", " ", line)
    return line.strip()


def _match_section(line):
    normalized = _normalize_heading(line)
    if not normalized or len(normalized) > 40:
        return None
    for section, variants in HEADINGS.items():
        if normalized in variants:
            return section
    return None


def segment_sections(text):
    """Split resume text into a dict of section name -> body text.

    WHY: scoring looks at WHERE evidence appears, not just whether a word
    exists. A skill named in Experience (with a verb and a number) is proof;
    the same word in a Skills list is only a claim. Everything before the
    first heading lands in the "header" section (name, contact details).
    """
    sections = {}
    current = "header"
    buffer = []

    def flush():
        body = "\n".join(buffer).strip()
        if body:
            if current in sections:
                sections[current] = sections[current] + "\n" + body
            else:
                sections[current] = body
        buffer.clear()

    for raw_line in text.split("\n"):
        line = raw_line.strip()
        matched = _match_section(line) if line else None
        if matched:
            flush()
            current = matched
            continue
        buffer.append(raw_line)
    flush()
    return sections


# ---------------------------------------------------------------------------
# Evidence search + rubric (original: lib/scoring/evidence.ts)
# ---------------------------------------------------------------------------

# Canonical skill name -> other names that mean the same thing. This is why
# a criterion of "JavaScript" still matches a resume that only says "JS".
SYNONYMS = {
    "javascript": ["js", "ecmascript", "es6", "es2015"],
    "typescript": ["ts"],
    "react": ["reactjs", "react.js"],
    "next.js": ["nextjs", "next js"],
    "node.js": ["nodejs", "node js", "node"],
    "postgresql": ["postgres", "psql"],
    "mongodb": ["mongo"],
    "github": ["gh"],
    "c++": ["cpp", "c plus plus"],
    "c#": ["csharp", "c sharp"],
    "machine learning": ["ml"],
    "artificial intelligence": ["ai"],
    "user interface": ["ui"],
    "user experience": ["ux"],
}

# Reverse map: alias -> canonical name, built once at import time.
ALIAS_TO_CANONICAL = {}
for _canonical, _aliases in SYNONYMS.items():
    for _alias in _aliases:
        ALIAS_TO_CANONICAL[_alias] = _canonical

# Verbs that signal "I actually did this" rather than "I know this word".
ACTION_VERBS = [
    "built", "developed", "designed", "implemented", "created", "launched",
    "improved", "increased", "reduced", "optimized", "automated", "led",
    "delivered", "shipped", "engineered", "architected", "migrated",
    "refactored", "integrated", "deployed", "scaled", "boosted",
    "streamlined", "achieved", "grew", "drove", "owned", "mentored",
    "collaborated",
]

# A "quantified result": a number, money, a percent, or a scale word.
QUANTIFIED = re.compile(
    r"(\d+\s?(%|x|k|\+)?|\$|₹|percent|users|customers|requests|ms|s\b)",
    re.IGNORECASE,
)


def search_forms(criterion_name):
    """All searchable spellings of a criterion: itself, its aliases, and its
    canonical name when the criterion itself is an alias ("js" -> "javascript"
    plus all of javascript's aliases)."""
    norm = normalize(criterion_name)
    forms = [norm]
    for alias in SYNONYMS.get(norm, []):
        if alias not in forms:
            forms.append(alias)
    canonical = ALIAS_TO_CANONICAL.get(norm)
    if canonical:
        if canonical not in forms:
            forms.append(canonical)
        for alias in SYNONYMS.get(canonical, []):
            if alias not in forms:
                forms.append(alias)
    return forms


def _sentence_matches(sentence_norm, forms):
    """True if any search form appears as a whole word in the sentence.
    Whole-word matching matters: "java" must not match "javascript"."""
    for form in forms:
        pattern = r"(^|\s)" + re.escape(form) + r"(\s|$)"
        if re.search(pattern, sentence_norm):
            return True
    return False


def find_evidence(sections, criterion_name):
    """Find every evidence sentence for a criterion across the sections.

    Returns a list of dicts: section, quote (truncated at 220 chars),
    has_action_verb, has_quantified_result. The quote is what the UI shows
    the user as proof — never just a bare score.
    """
    forms = search_forms(criterion_name)
    hits = []
    for section, body in sections.items():
        if not body:
            continue
        for sentence in split_sentences(body):
            norm = normalize(sentence)
            if not _sentence_matches(norm, forms):
                continue
            verb_hit = any(
                re.search(r"(^|\s)" + verb + r"(\s|$|ed\b|ing\b)", norm)
                for verb in ACTION_VERBS
            )
            quote = sentence if len(sentence) <= 220 else sentence[:217] + "…"
            hits.append({
                "section": section,
                "quote": quote,
                "has_action_verb": verb_hit,
                "has_quantified_result": bool(QUANTIFIED.search(sentence)),
            })
    return hits


STRONG_SECTIONS = {"experience", "projects"}
CONTEXT_SECTIONS = {"experience", "projects", "summary", "header"}


def rubric_score(hits):
    """The rubric (original docs §3.4), applied to one criterion's hits:

    100 — Experience/Projects bullet WITH action verb and/or quantified result
     70 — Experience/Projects bullet, or context in Summary/Header
     40 — Skills list only (claimed, not demonstrated)
      0 — not found anywhere

    Returns (score, status, best_hit_or_None). The order matters: a strong
    hit beats a merely contextual one even if the contextual one comes first.
    """
    if not hits:
        return 0, "missing", None
    for hit in hits:
        if hit["section"] in STRONG_SECTIONS and (
            hit["has_action_verb"] or hit["has_quantified_result"]
        ):
            return 100, "strong", hit
    for hit in hits:
        if hit["section"] in CONTEXT_SECTIONS:
            return 70, "present", hit
    for hit in hits:
        if hit["section"] == "skills":
            return 40, "weak", hit
    return 70, "present", hits[0]


# ---------------------------------------------------------------------------
# JD Match engine (original: lib/scoring/engine.ts)
# ---------------------------------------------------------------------------

# Fix-action templates per category and status. Gaps become "fix actions" in
# the UI — the whole point of the app is not the score, it is what to do next.
ACTION_TEMPLATES = {
    "skill": {
        "weak": "Add a project or experience bullet showing this skill in use, with "
                "a result — a Skills-list mention alone scores 40.",
        "missing": "Build or convert a small project using this skill, then add an "
                   "evidence bullet describing what you built and its result.",
    },
    "tool": {
        "weak": "Show this tool in a project bullet (what you used it for, what it "
                "changed) instead of only listing it.",
        "missing": "Ship one small thing with this tool and write it up as a bullet: "
                   "tool, task, and outcome.",
    },
    "language": {
        "weak": "Add a bullet where you used this language to build or fix something "
                "real, not just a Skills mention.",
        "missing": "Complete a small project in this language and add it to Projects "
                   "with a concrete outcome.",
    },
    "education": {
        "weak": "Make the education evidence explicit: degree, institution, and any "
                "relevant coursework or grade.",
        "missing": "If you are pursuing this qualification, list it as in-progress with "
                   "an expected date; otherwise cover it with equivalent "
                   "coursework or a certification.",
    },
    "default": {
        "weak": "Turn this mention into evidence: a bullet showing where you applied "
                "it and what changed.",
        "missing": "Create one concrete proof point for this requirement — a project, "
                   "a contribution, or coursework — and add it to the resume.",
    },
}


def _action_for(category, status):
    key = category.lower()
    template = ACTION_TEMPLATES.get(key)
    if template is None:
        template = ACTION_TEMPLATES["tool"] if "tool" in key else ACTION_TEMPLATES["default"]
    return template[status]


def score_resume(sections, criteria):
    """Score a resume against JD criteria.

    ``criteria`` is a list of dicts: {name, category, weight, required}.
    Returns a dict with:
      match_score      — weighted average, rounded to 1 decimal place
      criteria_results — one entry per criterion (score, status, evidence
                         quote, section)
      gaps             — weak/missing criteria with a suggested fix action
    """
    criteria_results = []
    for criterion in criteria:
        hits = find_evidence(sections, criterion["name"])
        score, status, best = rubric_score(hits)
        criteria_results.append({
            "name": criterion["name"],
            "category": criterion["category"],
            "weight": criterion["weight"],
            "score": score,
            "status": status,
            "evidence": best["quote"] if best else None,
            "section": best["section"] if best else None,
        })

    total_weight = sum(r["weight"] for r in criteria_results)
    if total_weight > 0:
        weighted = sum(r["weight"] * r["score"] for r in criteria_results)
        match_score = js_round(weighted / total_weight * 10) / 10
    else:
        match_score = 0

    gaps = [
        {
            "criterion": r["name"],
            "current_status": r["status"],
            "suggested_action": _action_for(r["category"], r["status"]),
        }
        for r in criteria_results
        if r["status"] in ("weak", "missing")
    ]
    return {
        "match_score": match_score,
        "criteria_results": criteria_results,
        "gaps": gaps,
    }


# ---------------------------------------------------------------------------
# Heuristic criteria drafting (original: lib/scoring/extract.ts)
# ---------------------------------------------------------------------------
# The no-AI fallback for turning JD text into criteria. The candidate always
# edits criteria before scoring, so this draft only needs to be a good start.

_SKILLS_VOCAB = [
    ("React", "skill", ["reactjs", "react.js"]),
    ("Next.js", "skill", ["nextjs", "next js"]),
    ("JavaScript", "skill", ["js", "javascript"]),
    ("TypeScript", "skill", ["ts", "typescript"]),
    ("Python", "skill", ["python"]),
    ("Java", "skill", ["java"]),
    ("C++", "skill", ["c++", "cpp"]),
    ("SQL", "skill", ["sql", "mysql", "postgres", "postgresql"]),
    ("Node.js", "skill", ["nodejs", "node js", "node"]),
    ("HTML", "skill", ["html", "html5"]),
    ("CSS", "skill", ["css", "css3", "tailwind", "tailwindcss"]),
    ("Git", "tool", ["git", "github", "gitlab"]),
    ("Docker", "tool", ["docker"]),
    ("Kubernetes", "tool", ["kubernetes", "k8s"]),
    ("AWS", "tool", ["aws", "amazon web services"]),
    ("Figma", "tool", ["figma"]),
    ("REST APIs", "skill", ["rest", "rest api", "rest apis", "api"]),
    ("GraphQL", "skill", ["graphql"]),
    ("Data Structures", "skill", ["data structures", "dsa", "algorithms"]),
    ("Machine Learning", "skill", ["machine learning", "ml"]),
]

_SOFT_VOCAB = [
    ("Communication", "soft", ["communication", "communicator"]),
    ("Teamwork", "soft", ["teamwork", "team player", "collaboration"]),
    ("Problem Solving", "soft", ["problem solving", "problem-solving", "analytical"]),
    ("Leadership", "soft", ["leadership", "leading"]),
]


def _contains(haystack, term):
    pattern = r"(^|[^a-z0-9])" + re.escape(term) + r"([^a-z0-9]|$)"
    return re.search(pattern, haystack) is not None


def _looks_required(text, term):
    """True if a "required"-style word appears near the term (80 chars
    before to 40 after). This is how required criteria get weight 35."""
    idx = text.find(term)
    if idx == -1:
        return False
    window = text[max(0, idx - 80):idx + len(term) + 40]
    return re.search(r"(required|must have|must-have|mandatory|essential)", window) is not None


def extract_criteria_heuristic(jd_text):
    """Draft criteria from JD text. Weights: required 35, soft skills 10,
    everything else 20 — then normalised to sum exactly 100 (the largest
    criterion absorbs rounding), capped at 12, heaviest first."""
    norm = normalize(jd_text)
    found = []
    for name, category, aliases in _SKILLS_VOCAB + _SOFT_VOCAB:
        hit_alias = None
        for alias in [name] + aliases:
            if _contains(norm, normalize(alias)):
                hit_alias = alias
                break
        if hit_alias is None:
            continue
        required = _looks_required(norm, normalize(hit_alias))
        weight = 35 if required else (10 if category == "soft" else 20)
        found.append({"name": name, "category": category, "weight": weight,
                      "required": required})

    # Education requirement. NOTE: this regex is inherited verbatim from the
    # original, including its quirk — on normalised text "B.Tech" becomes
    # "b tech", which matches neither "b\.tech" nor "btech", so only words
    # like "bachelor" or "degree" trigger it. Kept as-is so both apps agree.
    if re.search(r"(bachelor|b\.tech|btech|bca|degree|undergraduate)", norm):
        found.append({"name": "Bachelor's degree (or pursuing)",
                      "category": "education", "weight": 15, "required": True})

    if not found:
        return []
    limited = found[:12]
    total = sum(c["weight"] for c in limited)
    normalised = []
    acc = 0
    for i, criterion in enumerate(limited):
        if i == len(limited) - 1:
            normalised.append({**criterion, "weight": 100 - acc})
        else:
            weight = js_round(criterion["weight"] / total * 100)
            acc += weight
            normalised.append({**criterion, "weight": weight})
    normalised.sort(key=lambda c: c["weight"], reverse=True)
    return normalised


# ---------------------------------------------------------------------------
# ATS health score (original: lib/scoring/ats.ts)
# ---------------------------------------------------------------------------
# JD-independent: how parseable and recruiter-ready is this resume on its own?
# Five weighted categories; each category's score is the share of its checks
# passed; the total is the weighted average. Every check carries a "detail"
# string explaining itself, so the UI can always say WHY, not just a number.

_EMAIL_RE = re.compile(r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}", re.IGNORECASE)
_LINK_RE = re.compile(
    r"(github\.com|linkedin\.com|portfolio|vercel\.app|netlify\.app|behance|dribbble)",
    re.IGNORECASE,
)
_DATE_LIKE_RE = re.compile(
    r"\b(20\d{2}|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b",
    re.IGNORECASE,
)


def _ats_bullets(sections):
    """Experience + Projects sentences longer than 10 chars — the bullets
    that quantification and action-verb checks measure."""
    body = "\n".join([sections.get("experience", ""), sections.get("projects", "")])
    return [s for s in split_sentences(body) if len(s) > 10]


def compute_ats(sections, parsed_text=None):
    """Return {"score": int, "categories": [...]}. Categories carry weight,
    score, and checks; each check has name, passed, and a detail string."""
    all_text = "\n".join(sections.values())
    words = len((parsed_text if parsed_text is not None else all_text).split())

    def present(key):
        return bool(sections.get(key, "").strip())

    bullets = _ats_bullets(sections)
    quantified = sum(1 for b in bullets if re.search(r"\d", b))
    verb_led = sum(
        1 for b in bullets
        if any(b.lower().startswith(v) or f" {v} " in b.lower() for v in ACTION_VERBS)
    )

    contact_or_header = present("contact") or present("header")
    exp_or_proj = present("experience") or present("projects")
    email_found = bool(_EMAIL_RE.search(all_text))
    link_found = bool(_LINK_RE.search(all_text))
    dates_found = bool(_DATE_LIKE_RE.search(all_text))

    categories = [
        {
            "name": "Sections",
            "weight": 35,
            "checks": [
                {"name": "Contact info present", "passed": contact_or_header,
                 "detail": "Found a header/contact block." if contact_or_header
                 else "No header or contact section detected — add name, email, phone."},
                {"name": "Summary present", "passed": present("summary"),
                 "detail": "Summary detected." if present("summary")
                 else "No summary section — add a 2–3 line professional summary."},
                {"name": "Skills present", "passed": present("skills"),
                 "detail": "Skills detected." if present("skills")
                 else "No skills section detected."},
                {"name": "Experience or Projects present", "passed": exp_or_proj,
                 "detail": "Experience/Projects detected." if exp_or_proj
                 else "Neither experience nor projects detected — recruiters need proof of work."},
                {"name": "Education present", "passed": present("education"),
                 "detail": "Education detected." if present("education")
                 else "No education section detected."},
            ],
        },
        {
            "name": "Quantification",
            "weight": 20,
            "checks": [
                {"name": "Bullets carry numbers/results",
                 "passed": len(bullets) > 0 and quantified / len(bullets) >= 0.3,
                 "detail": "No experience/project bullets found to measure." if not bullets
                 else f"{quantified} of {len(bullets)} bullets contain a number or result "
                      f"({js_round(quantified / len(bullets) * 100)}%; aim for 30%+)."},
            ],
        },
        {
            "name": "Action verbs",
            "weight": 20,
            "checks": [
                {"name": "Bullets start with action verbs",
                 "passed": len(bullets) > 0 and verb_led / len(bullets) >= 0.5,
                 "detail": "No experience/project bullets found to measure." if not bullets
                 else f"{verb_led} of {len(bullets)} bullets use an action verb "
                      f"({js_round(verb_led / len(bullets) * 100)}%; aim for 50%+)."},
            ],
        },
        {
            "name": "Contact & links",
            "weight": 15,
            "checks": [
                {"name": "Email present", "passed": email_found,
                 "detail": "Email found." if email_found
                 else "No email address detected — ATS parsers and recruiters need one."},
                {"name": "Portfolio / GitHub / LinkedIn link", "passed": link_found,
                 "detail": "A profile link was found." if link_found
                 else "No GitHub, LinkedIn, or portfolio link detected."},
            ],
        },
        {
            "name": "Length & format",
            "weight": 10,
            "checks": [
                {"name": "Parseable text (not image-only)", "passed": words >= 50,
                 "detail": f"{words} words extracted." if words >= 50
                 else f"Only {words} words extracted — the file may be image-based or nearly empty."},
                {"name": "Reasonable length (150–1500 words)",
                 "passed": 150 <= words <= 1500,
                 "detail": f"Only {words} words — likely too thin for a full resume." if words < 150
                 else f"{words} words — likely too long; aim for a tight 1–2 page resume." if words > 1500
                 else f"{words} words — in range."},
                {"name": "Dates present", "passed": dates_found,
                 "detail": "Dates detected in experience/education." if dates_found
                 else "No dates detected — add timelines to experience and education."},
            ],
        },
    ]

    for category in categories:
        checks = category["checks"]
        passed = sum(1 for c in checks if c["passed"])
        category["score"] = js_round(passed / len(checks) * 100) if checks else 0

    total_weight = sum(c["weight"] for c in categories)
    score = js_round(
        sum(c["score"] * c["weight"] for c in categories) / total_weight
    )
    return {"score": score, "categories": categories}
