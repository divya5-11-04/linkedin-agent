import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from validators import (
    validate_word_count,
    find_spam_phrases,
    validate_hashtag_count,
    validate_draft,
)

GOOD_POST = " ".join(["word"] * 120) + " github.com/user/repo"
SHORT_POST = "way too short"
LONG_POST = " ".join(["word"] * 200)


def test_word_count_within_bounds_passes():
    ok, msg = validate_word_count(GOOD_POST, min_words=100, max_words=180)
    assert ok
    assert str(len(GOOD_POST.split())) in msg


def test_word_count_too_short_fails():
    ok, msg = validate_word_count(SHORT_POST, min_words=100, max_words=180)
    assert not ok
    assert "too short" in msg


def test_word_count_too_long_fails():
    ok, msg = validate_word_count(LONG_POST, min_words=100, max_words=180)
    assert not ok
    assert "too long" in msg


def test_find_spam_phrases_detects_known_phrase():
    text = "Excited to share what I built this week."
    found = find_spam_phrases(text)
    assert "excited to share" in found


def test_find_spam_phrases_case_insensitive():
    text = "This was a GAME-CHANGER for my workflow."
    found = find_spam_phrases(text)
    assert any("game-changer" in p for p in found)


def test_find_spam_phrases_clean_text_returns_empty():
    text = "Built a small tool that fetches data and posts it somewhere else."
    assert find_spam_phrases(text) == []


def test_hashtag_count_within_limit_passes():
    ok, count = validate_hashtag_count("Some post #ai #python", max_hashtags=3)
    assert ok
    assert count == 2


def test_hashtag_count_over_limit_fails():
    ok, count = validate_hashtag_count("#a #b #c #d #e", max_hashtags=3)
    assert not ok
    assert count == 5


def test_validate_draft_passes_clean_post():
    is_valid, issues = validate_draft(GOOD_POST, min_words=100, max_words=180)
    assert is_valid
    assert issues == []


def test_validate_draft_reports_multiple_issues():
    bad_post = "Excited to share this #a #b #c #d game-changer project"
    is_valid, issues = validate_draft(bad_post, min_words=100, max_words=180, max_hashtags=3)
    assert not is_valid
    # should catch: too short, spam phrase, too many hashtags
    assert len(issues) == 3
