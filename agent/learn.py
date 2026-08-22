"""LEARN phase: Persist and learn from user feedback."""

import json
import os
from datetime import datetime
from typing import Optional
from agent.logger import setup_logger
from agent.models import UserFeedback, LearningMemory
from agent.config import Config

logger = setup_logger(__name__)


class LearnPhase:
    """User feedback persistence and preference learning."""

    def __init__(self, config: Config):
        self.config = config
        self.feedback_file = config.feedback_file

    def load_memory(self) -> LearningMemory:
        """Load learning memory from disk."""
        if os.path.exists(self.feedback_file):
            try:
                with open(self.feedback_file, "r") as f:
                    data = json.load(f)
                    logger.info(f"Loaded learning memory: {len(data.get('feedback_history', []))} feedback entries")
                    return LearningMemory(**data)
            except Exception as e:
                logger.warning(f"Failed to load learning memory: {e}")
                return LearningMemory()
        return LearningMemory()

    def save_memory(self, memory: LearningMemory) -> None:
        """Save learning memory to disk."""
        try:
            with open(self.feedback_file, "w") as f:
                json.dump(memory.dict(), f, indent=2, default=str)
                logger.info(f"Saved learning memory: {memory.total_posts} posts")
        except Exception as e:
            logger.error(f"Failed to save learning memory: {e}")

    def record_user_choice(
        self,
        repo: str,
        chosen_variant: str,
        user_edits: Optional[str] = None,
        feedback_tags: list = None,
    ) -> LearningMemory:
        """Record user feedback and update learning memory."""
        logger.info(f"Recording feedback: {repo} chose {chosen_variant}")

        # Load existing memory
        memory = self.load_memory()

        # Calculate approval score (0.0 = heavily edited, 1.0 = no changes)
        if user_edits:
            approval_score = 0.6  # User had to edit
        else:
            approval_score = 1.0  # User approved as-is

        # Create feedback record
        feedback = UserFeedback(
            repo=repo,
            chosen_variant=chosen_variant,
            user_edits=user_edits,
            feedback_tags=feedback_tags or [],
            timestamp=datetime.utcnow(),
            approval_score=approval_score,
        )

        # Update memory
        memory.update_preferences(feedback)

        # Save updated memory
        self.save_memory(memory)

        logger.info(f"Memory updated. Total posts: {memory.total_posts}, Avg approval: {memory.avg_approval_score:.2f}")
        return memory
