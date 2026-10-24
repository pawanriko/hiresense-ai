# Criteria extraction v1 (Groq, llama-3.3-70b-versatile)
Input: raw job description text.
Output: JSON object {"criteria": [{"name", "category" ("skill"|"tool"|"language"|"education"|"soft"), "weight" (suggested, sum ~100), "required" (bool)}]}.
Rules: required skills > preferred skills > education/soft. 5-12 criteria, short names.
The result is a DRAFT: the candidate reviews and edits criteria and weights before any scoring runs.
