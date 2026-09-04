"""Pure validation functions for generated LinkedIn post drafts.

Kept dependency-free and side-effect-free so they're trivial to unit test.
"""

from typing import List, Tuple

SPAM_PHRASES = [
    "excited to share",
    "thrilled to announce",
    "game-changer",
    "game-changing",
    "revolutionary",
    "state-of-the-art",
    "industry-leading",
    "best-in-class",
    "cutting-edge",
    "groundbreaking",
    "disruptive technology",
    "next-generation",
    "paradigm shift",
]


def validate_word_count(post_text: str, min_words: int = 100, max_words: int = 180) -> Tuple[bool, str]:
    """Check the post falls within the intended word-count band."""
    word_count = len(post_text.split())
    if word_count < min_words:
        return False, f"too short: {word_count} words (min {min_words})"
    if word_count > max_words:
        return False, f"too long: {word_count} words (max {max_words})"
    return True, f"word count OK: {word_count}"


def find_spam_phrases(post_text: str) -> List[str]:
    """Return any banned LinkedIn-influencer phrases found in the post (case-insensitive)."""
    lower_text = post_text.lower()
    return [phrase for phrase in SPAM_PHRASES if phrase in lower_text]


def validate_hashtag_count(post_text: str, max_hashtags: int = 3) -> Tuple[bool, int]:
    """Check the post doesn't exceed the hashtag budget."""
    hashtags = [w for w in post_text.split() if w.startswith("#")]
    return len(hashtags) <= max_hashtags, len(hashtags)


def validate_draft(post_text: str, min_words: int = 100, max_words: int = 180, max_hashtags: int = 3) -> Tuple[bool, List[str]]:
    """Run all checks on a draft. Returns (is_valid, list_of_issues)."""
    issues = []

    ok, msg = validate_word_count(post_text, min_words, max_words)
    if not ok:
        issues.append(msg)

    spam_found = find_spam_phrases(post_text)
    if spam_found:
        issues.append(f"contains spam phrases: {', '.join(spam_found)}")

    ok, count = validate_hashtag_count(post_text, max_hashtags)
    if not ok:
        issues.append(f"too many hashtags: {count} (max {max_hashtags})")

    return (len(issues) == 0), issues
