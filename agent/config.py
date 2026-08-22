"""Centralized configuration for LinkedIn Agent."""

import os
from dataclasses import dataclass


@dataclass
class Config:
    """Agent configuration."""

    # API Keys
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    github_token: str = os.getenv("GH_TOKEN", "")
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "")
    linkedin_access_token: str = os.getenv("LINKEDIN_ACCESS_TOKEN", "")
    linkedin_person_urn: str = os.getenv("LINKEDIN_PERSON_URN", "")

    # LLM Configuration
    groq_model: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    analysis_temperature: float = float(os.getenv("ANALYSIS_TEMPERATURE", "0.3"))  # Low for reasoning
    generation_temperature: float = float(os.getenv("GENERATION_TEMPERATURE", "0.7"))  # Medium for creativity
    max_tokens_analysis: int = int(os.getenv("MAX_TOKENS_ANALYSIS", "500"))
    max_tokens_generation: int = int(os.getenv("MAX_TOKENS_GENERATION", "300"))
    max_tokens_evaluation: int = int(os.getenv("MAX_TOKENS_EVALUATION", "400"))

    # Content Constraints
    readme_max_chars: int = int(os.getenv("README_MAX_CHARS", "6000"))
    post_min_words: int = int(os.getenv("POST_MIN_WORDS", "50"))
    post_max_words: int = int(os.getenv("POST_MAX_WORDS", "180"))
    post_max_hashtags: int = int(os.getenv("POST_MAX_HASHTAGS", "3"))

    # Retry Configuration
    max_retries: int = int(os.getenv("MAX_RETRIES", "3"))
    retry_delay_base: int = int(os.getenv("RETRY_DELAY_BASE", "1"))  # seconds

    # Validation
    extra_context_max_length: int = int(os.getenv("EXTRA_CONTEXT_MAX_LENGTH", "500"))

    # API Timeouts
    api_timeout: int = int(os.getenv("API_TIMEOUT", "30"))  # seconds

    # State Files
    telegram_offset_file: str = os.getenv("TELEGRAM_OFFSET_FILE", "telegram_offset.json")
    feedback_file: str = os.getenv("FEEDBACK_FILE", "feedback.json")
    agent_state_file: str = os.getenv("AGENT_STATE_FILE", "agent_state.json")

    def validate(self) -> None:
        """Validate that all required secrets are present."""
        required = [
            ("GROQ_API_KEY", self.groq_api_key),
            ("TELEGRAM_BOT_TOKEN", self.telegram_bot_token),
            ("TELEGRAM_CHAT_ID", self.telegram_chat_id),
            ("LINKEDIN_ACCESS_TOKEN", self.linkedin_access_token),
            ("LINKEDIN_PERSON_URN", self.linkedin_person_urn),
        ]
        missing = [name for name, value in required if not value]
        if missing:
            raise RuntimeError(f"Missing required secrets: {', '.join(missing)}")


def get_config() -> Config:
    """Get and validate config."""
    config = Config()
    config.validate()
    return config
