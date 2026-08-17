import os
import json
import base64
import requests

repo = os.environ["REPO"]
token = os.environ.get("GH_TOKEN")

headers = {"Authorization": f"token {token}"} if token else {}

# Repo metadata
meta_resp = requests.get(f"https://api.github.com/repos/{repo}", headers=headers)
meta_resp.raise_for_status()
meta = meta_resp.json()

# README
readme_resp = requests.get(f"https://api.github.com/repos/{repo}/readme", headers=headers)
readme_text = ""
if readme_resp.status_code == 200:
    content = readme_resp.json().get("content", "")
    readme_text = base64.b64decode(content).decode("utf-8", errors="ignore")

# Recent commits (last 10) for extra flavor
commits_resp = requests.get(
    f"https://api.github.com/repos/{repo}/commits", headers=headers, params={"per_page": 10}
)
commit_msgs = []
if commits_resp.status_code == 200:
    commit_msgs = [c["commit"]["message"].split("\n")[0] for c in commits_resp.json()]

data = {
    "repo": repo,
    "description": meta.get("description", ""),
    "language": meta.get("language", ""),
    "stars": meta.get("stargazers_count", 0),
    "topics": meta.get("topics", []),
    "url": meta.get("html_url", f"https://github.com/{repo}"),
    "readme": readme_text[:6000],  # cap size
    "recent_commits": commit_msgs,
}

with open("repo_data.json", "w") as f:
    json.dump(data, f, indent=2)

print(f"Fetched data for {repo}: {len(readme_text)} char README, {len(commit_msgs)} commits")
