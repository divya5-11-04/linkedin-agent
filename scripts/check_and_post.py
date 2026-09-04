import os
import json
import requests

from retry import with_retries

STATE_FILE = "telegram_offset.json"
PENDING_FILE = "pending_draft.json"

bot_token = os.environ["TELEGRAM_BOT_TOKEN"]
chat_id = str(os.environ["TELEGRAM_CHAT_ID"])
li_token = os.environ["LINKEDIN_ACCESS_TOKEN"]
li_urn = os.environ["LINKEDIN_PERSON_URN"]  # e.g. "urn:li:person:XXXXXXX"

# Load last processed update_id so we never double-post
offset = 0
if os.path.exists(STATE_FILE):
    with open(STATE_FILE) as f:
        offset = json.load(f).get("last_update_id", 0)

# Load the draft we actually sent, rather than re-parsing it out of
# Telegram's (sometimes truncated) reply-preview text.
pending_draft = None
if os.path.exists(PENDING_FILE):
    with open(PENDING_FILE) as f:
        pending_draft = json.load(f).get("draft")


def _get_updates():
    resp = requests.get(
        f"https://api.telegram.org/bot{bot_token}/getUpdates",
        params={"offset": offset + 1, "timeout": 0},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("result", [])


updates = with_retries(
    _get_updates,
    attempts=3,
    base_delay=2.0,
    on_retry=lambda attempt, exc, delay: print(f"getUpdates failed (attempt {attempt}): {exc}. Retrying in {delay:.0f}s..."),
)

if not updates:
    print("No new Telegram messages.")
    with open(STATE_FILE, "w") as f:
        json.dump({"last_update_id": offset}, f)
    exit(0)

post_text = None
new_offset = offset
draft_consumed = False

for u in updates:
    new_offset = max(new_offset, u["update_id"])
    msg = u.get("message", {})
    if str(msg.get("chat", {}).get("id")) != chat_id:
        continue
    text = msg.get("text", "").strip()

    if text.startswith("/approve"):
        if pending_draft:
            post_text = pending_draft
            draft_consumed = True
        else:
            print("WARNING: /approve received but no pending_draft.json found; skipping.")
    elif text.startswith("/edit"):
        post_text = text[len("/edit"):].strip()
        draft_consumed = True
    elif text.startswith("/reject"):
        print("Draft rejected by user. Nothing posted.")
        draft_consumed = True

# Save new offset regardless of outcome
with open(STATE_FILE, "w") as f:
    json.dump({"last_update_id": new_offset}, f)

# Clear the pending draft once it's been acted on, so a stray future message
# can't accidentally re-trigger an old post.
if draft_consumed and os.path.exists(PENDING_FILE):
    os.remove(PENDING_FILE)

if not post_text:
    print("No approval/edit command found in new messages.")
    exit(0)


def _post_to_linkedin():
    resp = requests.post(
        "https://api.linkedin.com/v2/ugcPosts",
        headers={
            "Authorization": f"Bearer {li_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        },
        json={
            "author": li_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": post_text},
                    "shareMediaCategory": "NONE",
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        },
        timeout=30,
    )
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"LinkedIn post failed: {resp.status_code} {resp.text}")
    return resp


try:
    with_retries(
        _post_to_linkedin,
        attempts=3,
        base_delay=3.0,
        on_retry=lambda attempt, exc, delay: print(f"LinkedIn post failed (attempt {attempt}): {exc}. Retrying in {delay:.0f}s..."),
    )
    print("✅ Posted to LinkedIn successfully.")
except Exception as e:
    print(f"❌ LinkedIn post failed after retries: {e}")
    requests.post(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        json={"chat_id": chat_id, "text": f"❌ Failed to post to LinkedIn: {e}"},
        timeout=30,
    )
    exit(1)

# Notify back on Telegram
requests.post(
    f"https://api.telegram.org/bot{bot_token}/sendMessage",
    json={"chat_id": chat_id, "text": "✅ Posted to LinkedIn!"},
    timeout=30,
)
