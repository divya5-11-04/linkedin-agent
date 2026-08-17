import os
import json
import requests

with open("repo_data.json") as f:
    repo_data = json.load(f)

extra_context = os.environ.get("EXTRA_CONTEXT", "")
groq_key = os.environ["GROQ_API_KEY"]

SYSTEM_PROMPT = """You write LinkedIn posts for a software engineer announcing a project they built.

Hard rules:
- Sound like a real person talking to other engineers/recruiters, not a marketing bot.
- NO hashtag spam (max 3, only if genuinely relevant, at the very end).
- NO "Excited to share 🚀" / "Thrilled to announce" / "Game-changer" / generic LinkedIn-influencer phrases.
- Open with something concrete: the problem, a surprising result, or what it does — not "I built a project."
- Include specifics: what it does, what stack/approach, what was hard or interesting about it, and a real outcome or number if available.
- Keep it 100-180 words. Short paragraphs (1-3 sentences), easy to skim on mobile.
- End with a plain, low-key call to action (e.g. "Repo link in comments" or "Curious what you'd have done differently").
- Do not use em dashes.
- Write in first person, past or present tense as natural.

Output ONLY the post text. No preamble, no explanation, no quotes around it.
"""

user_prompt = f"""
Repo: {repo_data['repo']}
Description: {repo_data['description']}
Primary language: {repo_data['language']}
Topics: {', '.join(repo_data['topics'])}
Stars: {repo_data['stars']}
Repo URL: {repo_data['url']}

README (may be truncated):
{repo_data['readme']}

Recent commit messages (for flavor on what was actually worked on):
{chr(10).join('- ' + c for c in repo_data['recent_commits'])}

Extra context from the author (prioritize this if given): {extra_context or '(none provided)'}
"""

resp = requests.post(
    "https://api.groq.com/openai/v1/chat/completions",
    headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
    json={
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.8,
        "max_tokens": 600,
    },
    timeout=60,
)
resp.raise_for_status()
draft = resp.json()["choices"][0]["message"]["content"].strip()

with open("draft_post.txt", "w") as f:
    f.write(draft)

print("--- DRAFT ---")
print(draft)
