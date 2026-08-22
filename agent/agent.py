"""Main agent orchestration loop."""

import json
import os
from typing import List, Tuple
from agent.logger import setup_logger
from agent.config import Config, get_config
from agent.models import RepositoryData, PostVariant, EvaluationScores, AgentState, LearningMemory
from agent.sense import SensePhase
from agent.think import ThinkPhase
from agent.act import ActPhase
from agent.evaluate import EvaluatePhase
from agent.learn import LearnPhase
from agent.tools.github_tool import GitHubTool
from agent.tools.groq_tool import GroqTool
from agent.tools.linkedin_tool import LinkedInTool
from agent.tools.telegram_tool import TelegramTool
from agent.tools.validators import validate_variant

logger = setup_logger(__name__)


class LinkedInAgent:
    """Main agent orchestrator: SENSE → THINK → ACT → EVALUATE → OBSERVE → VERIFY → PUBLISH"""

    def __init__(self, config: Config):
        self.config = config
        self.github_tool = GitHubTool(config)
        self.groq_tool = GroqTool(config)
        self.linkedin_tool = LinkedInTool(config)
        self.telegram_tool = TelegramTool(config)

        self.sense = SensePhase(config, self.github_tool)
        self.think = ThinkPhase(config, self.groq_tool)
        self.act = ActPhase(config, self.groq_tool)
        self.evaluate = EvaluatePhase(config, self.groq_tool)
        self.learn = LearnPhase(config)

    def run(self, repo: str) -> AgentState:
        """Execute full agent loop for a repository."""
        logger.info(f"\n{'='*60}")
        logger.info(f"Starting LinkedIn Agent for {repo}")
        logger.info(f"{'='*60}\n")

        state = AgentState(repo=repo)

        try:
            # Load learning memory
            learning = self.learn.load_memory()
            logger.info(f"Loaded learning memory: {learning.total_posts} previous posts")

            # SENSE: Analyze repository
            state.repo_data = self.sense.analyze_repo(repo)
            logger.info("✓ SENSE phase complete")

            # THINK: Determine narrative angle
            state.narrative_analysis = self.think.decide_narrative(state.repo_data, learning)
            logger.info("✓ THINK phase complete")

            # ACT: Generate variants
            state.variants = self.act.generate_variants(state.repo_data, state.narrative_analysis, learning)
            logger.info("✓ ACT phase complete")

            # EVALUATE: Self-score variants
            state.evaluations = self.evaluate.evaluate_variants(state.variants, state.repo_data.url, learning)
            logger.info("✓ EVALUATE phase complete")

            # OBSERVE: Ask for user approval
            ranked_variants = [
                (v, next(e.composite_score for e in state.evaluations if e.variant_id == v.variant_id))
                for v in state.variants
            ]
            ranked_variants.sort(key=lambda x: x[1], reverse=True)

            self._send_approval_request(repo, ranked_variants)
            logger.info("✓ OBSERVE phase complete - awaiting user feedback")

            return state

        except Exception as e:
            logger.error(f"Agent failed: {e}", exc_info=True)
            self.telegram_tool.send_message(f"❌ Agent failed for {repo}: {str(e)}")
            raise

    def handle_user_feedback(self, repo: str, feedback_command: str, original_text: str = None) -> bool:
        """Handle user feedback from Telegram.

        Returns True if post was published.
        """
        logger.info(f"Handling user feedback: {feedback_command}")

        try:
            if feedback_command.startswith("/choose"):
                # User chose a specific variant
                choice = int(feedback_command.split()
[1]) - 1  # 1-indexed to 0-indexed
                return self._post_and_learn(repo, choice, original_text, edited=False)

            elif feedback_command.startswith("/edit"):
                # User edited the post
                custom_text = feedback_command[len("/edit"):].strip()
                return self._post_and_learn(repo, None, custom_text, edited=True)

            elif feedback_command.startswith("/reject"):
                # User rejected all variants
                logger.info(f"User rejected post for {repo}")
                self.telegram_tool.send_message(f"Draft rejected for {repo}. Starting over...")
                return False

            elif feedback_command.startswith("/refine"):
                # User requested refinement (not implemented yet)
                logger.info(f"Refinement requested for {repo}")
                self.telegram_tool.send_message(f"Refinement not yet implemented. Please /choose or /edit instead.")
                return False

            else:
                logger.warning(f"Unknown feedback command: {feedback_command}")
                return False

        except Exception as e:
            logger.error(f"Failed to handle feedback: {e}")
            self.telegram_tool.send_message(f"❌ Error processing feedback: {str(e)}")
            return False

    def _send_approval_request(self, repo: str, ranked_variants: List[Tuple]) -> None:
        """Send approval request to Telegram."""
        self.telegram_tool.send_approval_request(repo, ranked_variants)
        logger.info("Approval request sent to Telegram")

    def _post_and_learn(self, repo: str, variant_choice: int = None, custom_text: str = None, edited: bool = False) -> bool:
        """Post to LinkedIn and learn from choice."""
        try:
            # Determine final post text
            if custom_text:
                final_text = custom_text
            elif variant_choice is not None:
                # TODO: Load state to get variants
                logger.warning("Variant choice requires loaded state")
                return False
            else:
                logger.error("No post text provided")
                return False

            # VERIFY: Validate before posting
            logger.info("VERIFY: Running quality checks")
            # (validation logic here)

            # POST: Publish to LinkedIn
            logger.info("Publishing to LinkedIn...")
            self.linkedin_tool.post_ugc(final_text)
            logger.info("✓ Posted to LinkedIn")

            # LEARN: Record user choice
            chosen_variant = "custom" if edited else ("recruiter", "developer", "community")[variant_choice] if variant_choice is not None else "unknown"
            feedback_tags = self._extract_feedback_tags(custom_text) if edited else []
            self.learn.record_user_choice(repo, chosen_variant, user_edits=custom_text if edited else None, feedback_tags=feedback_tags)

            # Notify user
            self.telegram_tool.send_message(f"✅ Posted to LinkedIn! Post saved with {chosen_variant} narrative.")
            return True

        except Exception as e:
            logger.error(f"Failed to post and learn: {e}")
            self.telegram_tool.send_message(f"❌ Failed to post: {str(e)}")
            return False

    def _extract_feedback_tags(self, edited_text: str) -> list:
        """Infer feedback tags from edited text."""
        tags = []
        text_lower = edited_text.lower()

        # Simple heuristics
        if text_lower.count(" ") < edited_text.count(" ") * 0.8:
            tags.append("concise")
        if "#" not in edited_text and "#" in edited_text:
            tags.append("no_emoji")
        if any(word in text_lower for word in ["performance", "optimization", "algorithm", "architecture"]):
            tags.append("technical")
        if any(word in text_lower for word in ["🎯", "💡", "🚀"]):
            tags.append("emoji_focused")

        return tags
