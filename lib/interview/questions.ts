// Mock interview question bank — the no-AI fallback.
// Deterministic: same track + difficulty always yields the same set, in order.
// (When GROQ_API_KEY is set, AI-generated questions grounded in the resume + JD
// replace this bank; the bank stays as the offline fallback.)

export interface BankQuestion {
  question: string;
  topic: string;
  difficulty: "easy" | "medium" | "hard";
}

export const TRACKS = ["HR", "Technical", "DSA", "Frontend"] as const;
export type Track = (typeof TRACKS)[number];

const BANK: Record<Track, BankQuestion[]> = {
  HR: [
    { question: "Tell me about yourself — walk me through your background in under two minutes.", topic: "Introduction", difficulty: "easy" },
    { question: "Why do you want this role, and why this company?", topic: "Motivation", difficulty: "easy" },
    { question: "Describe a project you are most proud of. What was your exact contribution?", topic: "Ownership", difficulty: "medium" },
    { question: "Tell me about a time you failed or got stuck. What did you change afterwards?", topic: "Resilience", difficulty: "medium" },
    { question: "Describe a disagreement in a team setting and how you handled it.", topic: "Teamwork", difficulty: "medium" },
    { question: "Where do you see yourself in two years, and how does this role fit?", topic: "Goals", difficulty: "easy" },
    { question: "What is a weakness you are actively working on, with an example?", topic: "Self-awareness", difficulty: "hard" },
    { question: "Do you have any questions for us?", topic: "Curiosity", difficulty: "easy" },
  ],
  Technical: [
    { question: "Explain how a web request travels from the browser to the database and back.", topic: "Web fundamentals", difficulty: "easy" },
    { question: "What is the difference between SQL and NoSQL databases, and when would you pick each?", topic: "Databases", difficulty: "medium" },
    { question: "Explain REST vs GraphQL. Which would you choose for a dashboard app and why?", topic: "APIs", difficulty: "medium" },
    { question: "How would you debug a page that loads slowly in production?", topic: "Debugging", difficulty: "medium" },
    { question: "What happens when you run a query with no index on a large table?", topic: "Databases", difficulty: "hard" },
    { question: "Design a rate limiter for an API. What data structure and storage would you use?", topic: "System design", difficulty: "hard" },
    { question: "How do you keep secrets out of a codebase and out of git history?", topic: "Security", difficulty: "medium" },
    { question: "Explain authentication vs authorization, with an example of each.", topic: "Security", difficulty: "easy" },
  ],
  DSA: [
    { question: "Given an array of numbers, how would you find two that sum to a target? Walk through your approach and its complexity.", topic: "Arrays & hashing", difficulty: "easy" },
    { question: "Reverse a linked list. Explain your approach before writing any steps.", topic: "Linked lists", difficulty: "easy" },
    { question: "How would you detect a cycle in a linked list without extra memory?", topic: "Linked lists", difficulty: "medium" },
    { question: "Explain the difference between a stack and a queue, and give one real use of each.", topic: "Data structures", difficulty: "easy" },
    { question: "You have a sorted array rotated at an unknown pivot. How do you search it efficiently?", topic: "Binary search", difficulty: "medium" },
    { question: "When would you use a heap instead of sorting an array? Give an example.", topic: "Heaps", difficulty: "medium" },
    { question: "Explain dynamic programming in one example you have actually solved.", topic: "DP", difficulty: "hard" },
    { question: "How do you decide between BFS and DFS for a graph problem?", topic: "Graphs", difficulty: "hard" },
  ],
  Frontend: [
    { question: "Explain the difference between state and props in React, with an example.", topic: "React", difficulty: "easy" },
    { question: "What happens when you call setState? Why is it asynchronous?", topic: "React", difficulty: "medium" },
    { question: "How would you build a form with validation that is also accessible?", topic: "Forms & a11y", difficulty: "medium" },
    { question: "Explain the CSS box model and why margin collapsing surprises people.", topic: "CSS", difficulty: "easy" },
    { question: "How do you decide between client-side rendering and server-side rendering?", topic: "Rendering", difficulty: "medium" },
    { question: "A list of 10,000 rows renders slowly. What do you do?", topic: "Performance", difficulty: "hard" },
    { question: "What is the difference between useMemo, useCallback, and useEffect? When would you skip all three?", topic: "React hooks", difficulty: "hard" },
    { question: "How would you structure a small app so a new feature doesn't break old screens?", topic: "Architecture", difficulty: "medium" },
  ],
};

export function pickQuestions(track: Track, difficulty: string, count = 5): BankQuestion[] {
  const all = BANK[track] ?? BANK.HR;
  const order: BankQuestion["difficulty"][] =
    difficulty === "easy"
      ? ["easy", "medium", "hard"]
      : difficulty === "hard"
        ? ["hard", "medium", "easy"]
        : ["medium", "easy", "hard"];
  const sorted = [...all].sort(
    (a, b) => order.indexOf(a.difficulty) - order.indexOf(b.difficulty)
  );
  return sorted.slice(0, count);
}

/** Checklist feedback — the no-AI answer scorer. Honest, deterministic, labelled. */
export interface ChecklistScore {
  relevance: number;
  depth: number;
  structure: number;
  confidence: number;
  conciseness: number;
  overall: number;
  feedback: string;
}

const STAR_WORDS = ["situation", "task", "action", "result", "first", "then", "finally", "because", "so we"];

export function scoreAnswerChecklist(
  question: string,
  answer: string,
  topicKeywords: string[]
): ChecklistScore {
  const text = answer.toLowerCase();
  const words = answer.split(/\s+/).filter(Boolean).length;
  const keywordHits = topicKeywords.filter((k) => text.includes(k.toLowerCase())).length;
  const relevance = topicKeywords.length === 0 ? 60 : Math.round((keywordHits / topicKeywords.length) * 100);
  const depth = words < 20 ? 30 : words < 60 ? 60 : words < 150 ? 85 : 95;
  const starHits = STAR_WORDS.filter((w) => text.includes(w)).length;
  const structure = Math.min(100, 30 + starHits * 15);
  const confidence = /^(i|we)\s+(built|designed|led|delivered|improved)/.test(text) ? 80 : text.includes("i think") || text.includes("maybe") ? 45 : 65;
  const conciseness = words <= 180 ? 90 : words <= 300 ? 70 : 45;
  const overall = Math.round(
    relevance * 0.3 + depth * 0.25 + structure * 0.2 + confidence * 0.15 + conciseness * 0.1
  );
  const feedback =
    words < 20
      ? "Too short to judge depth — expand with a concrete example: what you did, and what changed."
      : keywordHits === 0 && topicKeywords.length > 0
        ? "The answer drifts from the question's topic — anchor the first sentence directly to what was asked, then give one example."
        : "Solid structure. To push higher, add one measurable outcome to your example (a number, a before/after, or a user impact).";
  return { relevance, depth, structure, confidence, conciseness, overall, feedback };
}
