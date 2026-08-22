"""ACT phase: Generate multiple post variants."""

from typing import List
from agent.logger import setup_logger
from agent.models import RepositoryData, PostVariant, LearningMemory
from agent.tools.groq_tool import GroqTool
from agent.config import Config

logger = setup_logger(__name__)


class ActPhase:
    """Multi-variant post generation."""

    VARIANT_TYPES = ["recruiter", "developer", "community"]

    def __init__(self, config: Config, groq_tool: GroqTool):
        self.config = config
        self.groq_tool = groq_tool

    def generate_variants(
        self, repo_data: RepositoryData, narrative_analysis: str, learning: LearningMemory
    ) -> List[PostVariant]:
        """Generate 3 post variants with different angles."""
        logger.info("ACT: Generating 3 post variants")

        variants = []
        for variant_type in self.VARIANT_TYPES:
            logger.info(f"Generating {variant_type} variant")

            # Build user preferences string
            user_prefs = self._build_user_preferences(variant_type, learning)

            # Generate variant
            post_text = self.groq_tool.generate_variant(
                repo_data=self._format_repo_for_generation(repo_data),
                narrative_analysis=narrative_analysis,
                variant_type=variant_type,
                user_preferences=user_prefs,
            )

            # Create variant object
            variant = PostVariant(
                variant_id=variant_type,
                narrative=self._get_narrative_label(variant_type),
                post_text=post_text,
                word_count=len(post_text.split()),
                hashtag_count=len([w for w in post_text.split() if w.startswith("#")]),
            )
            variants.append(variant)
            logger.info(f"Generated {variant_type} variant: {variant.word_count} words")

        return variants

    def _build_user_preferences(self, variant_type: str, learning: LearningMemory) -> str:
        """Build user preference hints for LLM."""
        if not learning.preferred_tags:
            return ""

        prefs = []
        for tag, count in sorted(learning.preferred_tags.items(), key=lambda x: x[1], reverse=True)[:3]:
            prefs.append(f"- User prefers: {tag}")

        return "\n".join(prefs)

    def _format_repo_for_generation(self, repo_data: RepositoryData) -> str:
        """Format repo data for post generation."""
        return f"""
Repo: {repo_data.repo}
Type: {repo_data.repo_type}
Description: {repo_data.description}
Language: {repo_data.language}
Stars: {repo_data.stars}
URL: {repo_data.url}

Key Features:
{chr(10).join('- ' + f for f in repo_data.key_features) if repo_data.key_features else 'N/A'}

README:
{repo_data.readme[:1500]}
"""

    def _get_narrative_label(self, variant_type: str) -> str:
        """Get human-readable label for variant."""
        labels = {
            "recruiter": "🎯 Recruiter Appeal",
            "developer": "💻 Developer Focused",
            "community": "🤝 Community Driven",
        }
        return labels.get(variant_type, variant_type)
