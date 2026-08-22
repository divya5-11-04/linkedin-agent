"""Validators for post quality and safety."""

from typing import List, Tuple
from agent.logger import setup_logger
from agent.models import PostVariant

logger = setup_logger(__name__)

# Spam phrases to avoid
SPAM_PHRASES = {
    "excited to share",
    "thrilled to announce",
    "game-changer",
    "revolutionary",
    "state-of-the-art",
    "industry-leading",
    "best-in-class",
    "cutting-edge technology",
    "groundbreaking innovation",
    "game-changing solution",
    "disruptive technology",
    "next-generation",
    "paradigm shift",
}


def validate_post_length(post_text: str, min_words: int = 50, max_words: int = 180) -> Tuple[bool, str]:
    """Validate post word count."""
    word_count = len(post_text.split())
    if word_count < min_words:
        return False, f"Post too short: {word_count} words (min {min_words})"
    if word_count > max_words:
        return False, f"Post too long: {word_count} words (max {max_words})"
    return True, f"Word count OK: {word_count} words"


def validate_no_spam_phrases(post_text: str) -> Tuple[bool, List[str]]:
    """Check for spam phrases."""
    lower_text = post_text.lower()
    found_phrases = [phrase for phrase in SPAM_PHRASES if phrase in lower_text]
    if found_phrases:
        return False, found_phrases
    return True, []


def validate_hashtags(post_text: str, max_hashtags: int = 3) -> Tuple[bool, int]:
    """Validate hashtag count."""
    hashtags = [word for word in post_text.split() if word.startswith("#")]
    if len(hashtags) > max_hashtags:
        return False, len(hashtags)
    return True, len(hashtags)


def validate_repo_link(post_text: str, repo_url: str) -> Tuple[bool, str]:
    """Check if repo link is mentioned."""
    # Accept variations: full URL, github.com, or repo mention
    if repo_url in post_text or "github.com" in post_text:
        return True, "Repo link found"
    return False, "Missing repo link or GitHub reference"


def validate_variant(variant: PostVariant, repo_url: str, config) -> Tuple[bool, List[str]]:
    """Run full validation on variant."""
    issues = []

    # Word count
    valid, msg = validate_post_length(variant.post_text, config.post_min_words, config.post_max_words)
    if not valid:
        issues.append(msg)

    # Spam phrases
    valid, phrases = validate_no_spam_phrases(variant.post_text)
    if not valid:
        issues.append(f"Contains spam phrases: {', '.join(phrases)}")

    # Hashtags
    valid, count = validate_hashtags(variant.post_text, config.post_max_hashtags)
    if not valid:
        issues.append(f"Too many hashtags: {count} (max {config.post_max_hashtags})")

    # Repo link
    valid, msg = validate_repo_link(variant.post_text, repo_url)
    if not valid:
        issues.append(msg)

    if issues:
        logger.warning(f"Variant validation issues: {issues}")
        return False, issues

    logger.info(f"Variant {variant.variant_id} passed all validations")
    return True, []
