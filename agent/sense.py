"""SENSE phase: Analyze repository to extract meaningful insights."""

import json
from typing import Optional
from agent.logger import setup_logger
from agent.models import RepositoryData
from agent.tools.github_tool import GitHubTool
from agent.config import Config

logger = setup_logger(__name__)


class SensePhase:
    """Repository analysis and insight extraction."""

    def __init__(self, config: Config, github_tool: GitHubTool):
        self.config = config
        self.github_tool = github_tool

    def analyze_repo(self, repo: str) -> RepositoryData:
        """Analyze repository and extract insights."""
        logger.info(f"SENSE: Analyzing repository {repo}")

        # Fetch metadata
        metadata = self.github_tool.fetch_repo_metadata(repo)
        logger.info(f"Fetched metadata: {metadata.get('name')}")

        # Fetch README
        readme = self.github_tool.fetch_readme(repo)
        logger.info(f"Fetched README: {len(readme)} characters")

        # Fetch commits
        commits = self.github_tool.fetch_recent_commits(repo, count=10)
        logger.info(f"Fetched {len(commits)} recent commits")

        # Determine repo type based on README and metadata
        repo_type = self._classify_repo_type(readme, metadata)
        logger.info(f"Classified as: {repo_type}")

        # Extract key features from README
        key_features = self._extract_key_features(readme)
        logger.info(f"Extracted {len(key_features)} key features")

        return RepositoryData(
            repo=repo,
            description=metadata.get("description", ""),
            language=metadata.get("language", ""),
            stars=metadata.get("stargazers_count", 0),
            topics=metadata.get("topics", []),
            url=metadata.get("html_url", f"https://github.com/{repo}"),
            readme=readme,
            recent_commits=commits,
            repo_type=repo_type,
            key_features=key_features,
        )

    def _classify_repo_type(self, readme: str, metadata: dict) -> str:
        """Classify repository type based on content and metadata."""
        readme_lower = readme.lower()
        topics = [t.lower() for t in metadata.get("topics", [])]

        # Library/package
        if any(word in readme_lower for word in ["install", "pip install", "npm install", "library", "package"]):
            return "library"

        # Tool/CLI
        if any(word in readme_lower for word in ["cli", "command-line", "tool", "binary"]):
            return "tool"

        # Framework
        if any(word in readme_lower for word in ["framework", "web", "django", "fastapi", "express"]):
            return "framework"

        # Learning/educational
        if any(word in readme_lower for word in ["tutorial", "learn", "educational", "example", "course"]):
            return "learning"

        # Research/paper
        if any(word in readme_lower for word in ["paper", "research", "implementation", "reproduced"]):
            return "research"

        # Application
        if any(word in readme_lower for word in ["app", "application", "server", "api"]):
            return "app"

        return "project"

    def _extract_key_features(self, readme: str) -> list:
        """Extract key features from README."""
        features = []

        # Look for common feature markers
        markers = ["features", "capabilities", "highlights", "advantages", "benefits"]
        lines = readme.split("\n")

        in_features = False
        for line in lines:
            line_lower = line.lower()

            # Start of features section
            if any(marker in line_lower for marker in markers):
                in_features = True
                continue

            # Feature line (bullet point)
            if in_features and line.strip().startswith(("- ", "* ", "• ")):
                feature = line.strip()[2:].strip()
                if feature and len(feature) < 100:
                    features.append(feature)

            # End of features section (next heading)
            if in_features and line.strip().startswith("#") and "feature" not in line_lower:
                in_features = False

        return features[:5]  # Top 5 features
