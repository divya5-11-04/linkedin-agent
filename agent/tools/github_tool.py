"""GitHub API wrapper with retry logic."""

import base64
import requests
from typing import Optional, Dict, Any, List
from agent.logger import setup_logger
from agent.config import Config

logger = setup_logger(__name__)


class GitHubTool:
    """Wrapper for GitHub API with retries and validation."""

    def __init__(self, config: Config):
        self.config = config
        self.base_url = "https://api.github.com"
        self.headers = {"Authorization": f"token {config.github_token}"} if config.github_token else {}

    def _call_with_retry(self, method: str, url: str, max_retries: int = 3, **kwargs) -> requests.Response:
        """Call API with exponential backoff retry."""
        import time

        for attempt in range(max_retries):
            try:
                resp = requests.request(
                    method,
                    url,
                    headers=self.headers,
                    timeout=self.config.api_timeout,
                    **kwargs,
                )
                if resp.status_code < 500:
                    return resp
                # 5xx errors: retry
                if attempt < max_retries - 1:
                    delay = self.config.retry_delay_base * (2**attempt)
                    logger.warning(f"GitHub API {resp.status_code}, retrying in {delay}s...")
                    time.sleep(delay)
            except requests.RequestException as e:
                if attempt < max_retries - 1:
                    delay = self.config.retry_delay_base * (2**attempt)
                    logger.warning(f"GitHub API request failed: {e}, retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    logger.error(f"GitHub API failed after {max_retries} retries: {e}")
                    raise
        return resp

    def fetch_repo_metadata(self, repo: str) -> Dict[str, Any]:
        """Fetch repository metadata."""
        logger.info(f"Fetching repo metadata: {repo}")
        resp = self._call_with_retry("GET", f"{self.base_url}/repos/{repo}")
        resp.raise_for_status()
        return resp.json()

    def fetch_readme(self, repo: str) -> str:
        """Fetch README content."""
        logger.info(f"Fetching README: {repo}")
        resp = self._call_with_retry("GET", f"{self.base_url}/repos/{repo}/readme")
        if resp.status_code == 404:
            logger.warning(f"README not found for {repo}")
            return ""
        resp.raise_for_status()
        content = resp.json().get("content", "")
        readme_text = base64.b64decode(content).decode("utf-8", errors="ignore")
        return readme_text[: self.config.readme_max_chars]

    def fetch_recent_commits(self, repo: str, count: int = 10) -> List[str]:
        """Fetch recent commit messages."""
        logger.info(f"Fetching {count} recent commits: {repo}")
        resp = self._call_with_retry("GET", f"{self.base_url}/repos/{repo}/commits", params={"per_page": count})
        if resp.status_code != 200:
            logger.warning(f"Failed to fetch commits for {repo}")
            return []
        commits = resp.json()
        return [c["commit"]["message"].split("\n")[0] for c in commits if "commit" in c]
