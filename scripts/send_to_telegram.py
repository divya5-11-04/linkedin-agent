import os
import json
import requests

from retry import with_retries

bot_token = os.environ["TELEGRAM_BOT_TOKEN"]
chat_id = os.environ["TELEGRAM_CHAT_ID"]

with open("draft_post.txt") as f:
    draft = f.read()

message = (
    "📝 *New LinkedIn draft ready*\n\n"
    f"{draft}\n\n"
    "---\n"
    "Reply to THIS message with:\n"
    "`/approve` to post as-is\n"
    "`/edit <your revised text>` to post your edited version\n"
    "`/reject` to discard"
)


def _send():
    resp = requests.post(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp


with_retries(
    _send,
    attempts=3,
    base_delay=2.0,
    on_retry=lambda attempt, exc, delay: print(f"Telegram send failed (attempt {attempt}): {exc}. Retrying in {delay:.0f}s..."),
)

# Persist the exact draft text alongside the run so /approve can recover it
# verbatim later, instead of parsing it back out of Telegram's (sometimes
# truncated) reply-preview text.
with open("pending_draft.json", "w") as f:
    json.dump({"draft": draft}, f)

print("Sent draft to Telegram. Waiting for your reply (checked every 10 min by the approval workflow).")
