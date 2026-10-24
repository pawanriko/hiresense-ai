// Groq client — the ONLY place the app talks to an LLM.
// Every function returns null on any failure so callers can fall back to the
// deterministic path (heuristic criteria, template rewrites, checklist feedback)
// and label the result honestly. The scoring engine never calls this file.

export function isGroqConfigured(): boolean {
  return Boolean(process.env.GROQ_API_KEY);
}

async function groqChat(system: string, user: string): Promise<string | null> {
  const key = process.env.GROQ_API_KEY;
  if (!key) return null;
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 30000);
    const res = await fetch("https://api.groq.com/openai/v1/chat/completions", {
      method: "POST",
      headers: { Authorization: `Bearer ${key}`, "Content-Type": "application/json" },
      body: JSON.stringify({
        model: "llama-3.3-70b-versatile",
        messages: [
          { role: "system", content: system },
          { role: "user", content: user },
        ],
        temperature: 0.3,
        response_format: { type: "json_object" },
      }),
      signal: controller.signal,
    });
    clearTimeout(timer);
    if (!res.ok) return null;
    const json = await res.json();
    return json?.choices?.[0]?.message?.content ?? null;
  } catch {
    return null;
  }
}

function parseJsonArray(text: string | null): unknown[] | null {
  if (!text) return null;
  try {
    const parsed = JSON.parse(text);
    return Array.isArray(parsed) ? parsed : parsed.criteria ?? parsed.items ?? null;
  } catch {
    return null;
  }
}

export interface AiCriterion {
  name: string;
  category: string;
  weight: number;
  required: boolean;
}

export async function extractCriteriaAi(jdText: string): Promise<AiCriterion[] | null> {
  const text = await groqChat(
    "You extract hiring criteria from a job description. Return ONLY a JSON object {\"criteria\": [{\"name\": string, \"category\": \"skill\"|\"tool\"|\"language\"|\"education\"|\"soft\", \"weight\": number (suggested, sum ~100), \"required\": boolean}]}. Required skills weigh more than preferred ones; education and soft requirements weigh less. Keep 5-12 criteria, each a short skill or requirement name.",
    jdText.slice(0, 8000)
  );
  const arr = parseJsonArray(text);
  if (!arr) return null;
  const cleaned = arr
    .filter(
      (c): c is Record<string, unknown> =>
        typeof c === "object" && c !== null && typeof (c as Record<string, unknown>).name === "string"
    )
    .map((c) => ({
      name: String(c.name).slice(0, 80),
      category: typeof c.category === "string" ? c.category : "skill",
      weight: typeof c.weight === "number" && c.weight > 0 ? Math.round(c.weight) : 10,
      required: c.required === true,
    }));
  return cleaned.length > 0 ? cleaned : null;
}

export async function rewriteBulletsAi(
  bullets: string[],
  gaps: string[],
  jdTitle: string
): Promise<string[] | null> {
  const text = await groqChat(
    "You rewrite resume bullets to be stronger and evidence-led. Return ONLY a JSON object {\"rewrites\": [string, ...]} with one rewritten bullet per input bullet, in the same order. Keep each under 25 words, start with an action verb, keep every fact from the original (never invent employers, numbers, or tools), and where a gap skill is listed, suggest how the bullet could evidence it WITHOUT inventing experience — use phrasing like 'Applied X in…' only if the original supports it; otherwise keep the bullet honest and note the gap separately is not needed, just rewrite.",
    JSON.stringify({ jdTitle, gaps, bullets: bullets.slice(0, 8) })
  );
  const arr = parseJsonArray(text);
  if (!arr) return null;
  const out = arr.filter((s): s is string => typeof s === "string");
  return out.length > 0 ? out : null;
}

export async function coverLetterAi(
  resumeText: string,
  jdText: string,
  matchScore: number,
  strengths: string[]
): Promise<string | null> {
  const text = await groqChat(
    "Write a concise, honest cover letter (under 300 words) for the candidate below applying to the job described. Return ONLY a JSON object {\"letter\": string}. Use only facts present in the resume — never invent experience, skills, or achievements. Mention 1-2 genuine strengths that match the JD. Professional, warm tone.",
    JSON.stringify({
      matchScore,
      strengths,
      resume: resumeText.slice(0, 4000),
      jd: jdText.slice(0, 4000),
    })
  );
  if (!text) return null;
  try {
    const parsed = JSON.parse(text);
    return typeof parsed.letter === "string" ? parsed.letter : null;
  } catch {
    return null;
  }
}

export async function interviewQuestionsAi(
  track: string,
  difficulty: string,
  resumeText: string,
  jdText: string
): Promise<{ question: string; topic: string }[] | null> {
  const text = await groqChat(
    "Generate a mock interview question set. Return ONLY a JSON object {\"questions\": [{\"question\": string, \"topic\": string}, ...]} with exactly 5 questions for the given track and difficulty, grounded in the resume and JD (no invented candidate facts in the questions themselves). Mix resume-based, JD-based, and fundamentals questions.",
    JSON.stringify({ track, difficulty, resume: resumeText.slice(0, 3000), jd: jdText.slice(0, 3000) })
  );
  const arr = parseJsonArray(text);
  if (!arr) return null;
  const out = arr
    .filter(
      (q): q is Record<string, unknown> =>
        typeof q === "object" && q !== null && typeof (q as Record<string, unknown>).question === "string"
    )
    .map((q) => ({
      question: String(q.question),
      topic: typeof q.topic === "string" ? q.topic : track,
    }));
  return out.length > 0 ? out : null;
}

export interface AiAnswerScore {
  relevance: number;
  depth: number;
  structure: number;
  confidence: number;
  conciseness: number;
  feedback: string;
}

export async function scoreAnswerAi(
  question: string,
  answer: string
): Promise<AiAnswerScore | null> {
  const text = await groqChat(
    "Score this mock-interview answer against a fixed rubric. Return ONLY a JSON object {\"relevance\": 0-100, \"depth\": 0-100, \"structure\": 0-100, \"confidence\": 0-100, \"conciseness\": 0-100, \"feedback\": string (2-3 sentences: one strength, one concrete improvement)}. Rubric weights: relevance 30%, depth 25%, structure 20%, confidence 15%, conciseness 10%. Be honest and specific; do not inflate scores.",
    JSON.stringify({ question, answer: answer.slice(0, 3000) })
  );
  if (!text) return null;
  try {
    const parsed = JSON.parse(text);
    const num = (v: unknown) => (typeof v === "number" ? Math.max(0, Math.min(100, Math.round(v))) : 50);
    return {
      relevance: num(parsed.relevance),
      depth: num(parsed.depth),
      structure: num(parsed.structure),
      confidence: num(parsed.confidence),
      conciseness: num(parsed.conciseness),
      feedback: typeof parsed.feedback === "string" ? parsed.feedback : "Answer recorded.",
    };
  } catch {
    return null;
  }
}
