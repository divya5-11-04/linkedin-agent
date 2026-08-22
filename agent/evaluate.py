"""EVALUATE phase: Self-score variants using LLM rubric."""

import json
from typing import List
from agent.logger import setup_logger
from agent.models import PostVariant, EvaluationScores, LearningMemory
from agent.tools.groq_tool import GroqTool
from agent.config import Config

logger = setup_logger(__name__)


class EvaluatePhase:
    """Self-evaluation of generated variants."""

    def __init__(self, config: Config, groq_tool: GroqTool):
        self.config = config
        self.groq_tool = groq_tool

    def evaluate_variants(
        self, variants: List[PostVariant], repo_url: str, learning: LearningMemory
    ) -> List[EvaluationScores]:
        """Evaluate all variants and return ranked scores."""
        logger.info("EVALUATE: Self-scoring variants")

        # Format variants for LLM evaluation
        variants_text = self._format_variants_for_evaluation(variants)
        user_prefs_text = self._format_user_preferences(learning)

        # Get LLM evaluation
        evaluation_json = self.groq_tool.evaluate_variants(
            repo_data=f"URL: {repo_url}",
            variants=variants_text,
            user_preferences=user_prefs_text,
        )

        # Parse LLM response
        scores = self._parse_evaluation_response(evaluation_json, variants)

        # Apply learning boost
        scores = self._apply_learning_boost(scores, learning)

        logger.info(f"Evaluation complete. Top score: {scores[0].composite_score:.1f}/10")
        return scores

    def _format_variants_for_evaluation(self, variants: List[PostVariant]) -> str:
        """Format variants for LLM evaluation."""
        lines = []
        for v in variants:
            lines.append(f"\n## {v.variant_id.upper()} ({v.narrative})")
            lines.append(f"```\n{v.post_text}\n```")
            lines.append(f"Stats: {v.word_count} words, {v.hashtag_count} hashtags")
        return "\n".join(lines)

    def _format_user_preferences(self, learning: LearningMemory) -> str:
        """Format user preferences for context."""
        if not learning.preferred_tags:
            return "No user preference history"

        lines = [f"User approval score trend: {learning.avg_approval_score:.2f}/1.0"]
        for tag, count in sorted(learning.preferred_tags.items(), key=lambda x: x[1], reverse=True)[:5]:
            lines.append(f"- {tag}: {count} times")
        return "\n".join(lines)

    def _parse_evaluation_response(self, response: str, variants: List[PostVariant]) -> List[EvaluationScores]:
        """Parse LLM evaluation response into structured scores."""
        try:
            # Extract JSON from response
            if "{" in response:
                json_start = response.index("{")
                json_str = response[json_start:]
                eval_data = json.loads(json_str)
            else:
                logger.warning("No JSON found in evaluation response")
                return self._default_scores(variants)

            scores = []
            for variant_eval in eval_data.get("variants", []):
                variant_id = variant_eval.get("id", "")
                score = EvaluationScores(
                    variant_id=variant_id,
                    authenticity=float(variant_eval.get("authenticity", 7)),
                    recruiter_appeal=float(variant_eval.get("recruiter_appeal", 7)),
                    originality=float(variant_eval.get("originality", 7)),
                    clarity=float(variant_eval.get("clarity", 7)),
                    cta_quality=float(variant_eval.get("cta_quality", 7)),
                    composite_score=float(variant_eval.get("composite_score", 7)),
                )
                scores.append(score)

            # Sort by composite score
            scores.sort(key=lambda x: x.composite_score, reverse=True)
            return scores
        except Exception as e:
            logger.error(f"Failed to parse evaluation: {e}")
            return self._default_scores(variants)

    def _default_scores(self, variants: List[PostVariant]) -> List[EvaluationScores]:
        """Return default scores if parsing fails."""
        scores = []
        for i, v in enumerate(variants):
            score = EvaluationScores(
                variant_id=v.variant_id,
                authenticity=7 + i * 0.5,
                recruiter_appeal=8 + i * 0.3,
                originality=7 + i * 0.7,
                clarity=8,
                cta_quality=7,
                composite_score=7.5,
            )
            scores.append(score)
        return scores

    def _apply_learning_boost(self, scores: List[EvaluationScores], learning: LearningMemory) -> List[EvaluationScores]:
        """Apply learning-based score adjustments."""
        for score in scores:
            # Boost recruiter appeal if that's what user prefers
            if learning.preferred_narrative == score.variant_id:
                score.recruiter_appeal = min(10, score.recruiter_appeal + 0.5)
                score.composite_score = score.calculate_composite()
                logger.info(f"Applied learning boost to {score.variant_id}")

        # Re-sort after boosting
        scores.sort(key=lambda x: x.composite_score, reverse=True)
        return scores
