"""THINK phase: Determine narrative angle and strategy."""

import json
from agent.logger import setup_logger
from agent.models import RepositoryData, LearningMemory
from agent.tools.groq_tool import GroqTool
from agent.config import Config

logger = setup_logger(__name__)


class ThinkPhase:
    """Narrative analysis and strategy determination."""

    def __init__(self, config: Config, groq_tool: GroqTool):
        self.config = config
        self.groq_tool = groq_tool

    def decide_narrative(self, repo_data: RepositoryData, learning: LearningMemory) -> str:
        """Use LLM to decide best narrative angle for this repo."""
        logger.info("THINK: Deciding narrative angle")

        # Format repo data for LLM
        repo_summary = self._format_repo_summary(repo_data)

        # Get LLM analysis
        analysis = self.groq_tool.analyze_repo(repo_summary)
        logger.info(f"Got narrative analysis: {analysis[:100]}...")

        # Inject user preferences from learning
        if learning.preferred_narrative:
            analysis += f"\n\n[NOTE: User prefers '{learning.preferred_narrative}' narrative style based on past choices]"

        return analysis

    def _format_repo_summary(self, repo_data: RepositoryData) -> str:
        """Format repository data for LLM analysis."""
        return f"""
# Repository: {repo_data.repo}
Type: {repo_data.repo_type or 'unknown'}
Description: {repo_data.description or 'No description'}
Language: {repo_data.language or 'Not specified'}
Stars: {repo_data.stars}
Topics: {', '.join(repo_data.topics) if repo_data.topics else 'None'}
URL: {repo_data.url}

## Key Features
{chr(10).join('- ' + f for f in repo_data.key_features) if repo_data.key_features else 'Not identified'}

## README (excerpt)
{repo_data.readme[:2000]}

## Recent Commits
{chr(10).join('- ' + c for c in repo_data.recent_commits[:5]) if repo_data.recent_commits else 'No commits'}
"""
