"""Pydantic models for type-safe data handling."""

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional
from datetime import datetime


class RepositoryData(BaseModel):
    """Repository metadata and analysis."""

    repo: str
    description: Optional[str] = None
    language: Optional[str] = None
    stars: int = 0
    topics: List[str] = []
    url: str
    readme: str
    recent_commits: List[str] = []
    repo_type: Optional[str] = None  # library, tool, app, research
    key_features: List[str] = []

    @validator("repo")
    def validate_repo_format(cls, v):
        if "/" not in v or len(v.split("/")) != 2:
            raise ValueError("Repo must be in format owner/repo")
        return v


class PostVariant(BaseModel):
    """A generated post variant."""

    variant_id: str  # "recruiter", "developer", "community"
    narrative: str  # The angle/narrative
    post_text: str
    word_count: int
    hashtag_count: int

    @validator("post_text")
    def validate_post_text(cls, v):
        if not v or len(v.strip()) < 50:
            raise ValueError("Post text must be at least 50 characters")
        return v


class EvaluationScores(BaseModel):
    """Self-evaluation scores for a post variant."""

    variant_id: str
    authenticity: float = Field(ge=0, le=10)  # matches repo reality
    recruiter_appeal: float = Field(ge=0, le=10)  # hiring manager interest
    originality: float = Field(ge=0, le=10)  # avoids spam phrases
    clarity: float = Field(ge=0, le=10)  # mobile-readable
    cta_quality: float = Field(ge=0, le=10)  # call-to-action quality
    composite_score: float = Field(ge=0, le=10)

    def calculate_composite(self) -> float:
        """Calculate weighted composite score."""
        weights = {
            "authenticity": 0.25,
            "recruiter_appeal": 0.30,  # highest weight
            "originality": 0.20,
            "clarity": 0.15,
            "cta_quality": 0.10,
        }
        return (
            self.authenticity * weights["authenticity"]
            + self.recruiter_appeal * weights["recruiter_appeal"]
            + self.originality * weights["originality"]
            + self.clarity * weights["clarity"]
            + self.cta_quality * weights["cta_quality"]
        )


class UserFeedback(BaseModel):
    """User feedback on a generated post."""

    repo: str
    chosen_variant: str
    user_edits: Optional[str] = None
    feedback_tags: List[str] = []  # e.g. ["technical", "no_emoji", "concise"]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    approval_score: float = 1.0  # 0.0-1.0: how much editing was needed


class AgentState(BaseModel):
    """Current state of the agent for a single run."""

    repo: str
    repo_data: Optional[RepositoryData] = None
    narrative_analysis: Optional[str] = None  # LLM reasoning
    variants: List[PostVariant] = []
    evaluations: List[EvaluationScores] = []
    chosen_variant_id: Optional[str] = None
    final_post_text: Optional[str] = None
    posted_to_linkedin: bool = False
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    def get_ranked_variants(self) -> List[tuple]:
        """Return variants ranked by composite score."""
        variant_scores = [
            (v, next((e.composite_score for e in self.evaluations if e.variant_id == v.variant_id), 0))
            for v in self.variants
        ]
        return sorted(variant_scores, key=lambda x: x[1], reverse=True)


class LearningMemory(BaseModel):
    """Accumulated learning from user feedback."""

    feedback_history: List[UserFeedback] = []
    preferred_narrative: Optional[str] = None  # most chosen narrative
    preferred_tags: Dict[str, int] = {}  # tag frequency
    total_posts: int = 0
    avg_approval_score: float = 1.0

    def update_preferences(self, feedback: UserFeedback) -> None:
        """Update preferences based on new feedback."""
        self.feedback_history.append(feedback)
        self.total_posts += 1

        # Track chosen narrative
        if feedback.chosen_variant:
            if not self.preferred_narrative:
                self.preferred_narrative = feedback.chosen_variant

        # Track tags
        for tag in feedback.feedback_tags:
            self.preferred_tags[tag] = self.preferred_tags.get(tag, 0) + 1

        # Update approval score (moving average)
        self.avg_approval_score = (
            (self.avg_approval_score * (self.total_posts - 1) + feedback.approval_score) / self.total_posts
        )

    def get_preference_boost(self, variant_id: str, tags: List[str]) -> float:
        """Get score boost based on learned preferences."""
        boost = 0.0

        # Boost if matches preferred narrative
        if self.preferred_narrative and variant_id == self.preferred_narrative:
            boost += 0.5

        # Boost for each matching tag
        for tag in tags:
            if tag in self.preferred_tags:
                boost += 0.2 * min(self.preferred_tags[tag] / max(self.total_posts, 1), 1.0)

        return min(boost, 2.0)  # Cap at +2.0
