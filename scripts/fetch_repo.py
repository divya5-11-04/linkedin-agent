import os
import json
import base64
import requests

from retry import with_retries

repo = os.environ["REPO"]
token = os.environ.get("GH_TOKEN")

headers = {"Authorization": f"token {token}"} if token else {}


def _get(url, **kwargs):
    def _do():
        resp = requests.get(url, headers=headers, timeout=30, **kwargs)
        resp.raise_for_status()
        return resp

    return with_retries(
        _do,
        attempts=3,
        base_delay=2.0,
        on_retry=lambda attempt, exc, delay: print(f"GET {url} failed (attempt {attempt}): {exc}. Retrying in {delay:.0f}s..."),
    )


# Repo metadata
meta_resp = _get(f"https://api.github.com/repos/{repo}")
meta = meta_resp.json()

# README (missing README is a valid 404, not a failure -- don't retry that)
readme_text = ""
try:
    readme_resp = _get(f"https://api.github.com/repos/{repo}/readme")
    content = readme_resp.json().get("content", "")
    readme_text = base64.b64decode(content).decode("utf-8", errors="ignore")
except requests.HTTPError as e:
    if e.response is not None and e.response.status_code == 404:
        print("No README found for this repo.")
    else:
        raise

# Recent commits (last 10) for extra flavor
commit_msgs = []
try:
    commits_resp = _get(f"https://api.github.com/repos/{repo}/commits", params={"per_page": 10})
    commit_msgs = [c["commit"]["message"].split("\n")[0] for c in commits_resp.json()]
except requests.HTTPError as e:
    if e.response is not None and e.response.status_code == 409:
        print("Repo has no commits yet.")
    else:
        raise

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
