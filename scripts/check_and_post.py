import os
import json
import requests

STATE_FILE = "telegram_offset.json"

bot_token = os.environ["TELEGRAM_BOT_TOKEN"]
chat_id = str(os.environ["TELEGRAM_CHAT_ID"])
li_token = os.environ["LINKEDIN_ACCESS_TOKEN"]
li_urn = os.environ["LINKEDIN_PERSON_URN"]  # e.g. "urn:li:person:XXXXXXX"

# Load last processed update_id so we never double-post
offset = 0
if os.path.exists(STATE_FILE):
    with open(STATE_FILE) as f:
        offset = json.load(f).get("last_update_id", 0)

resp = requests.get(
    f"https://api.telegram.org/bot{bot_token}/getUpdates",
    params={"offset": offset + 1, "timeout": 0},
)
resp.raise_for_status()
updates = resp.json().get("result", [])

if not updates:
    print("No new Telegram messages.")
    exit(0)

post_text = None
new_offset = offset

for u in updates:
    new_offset = max(new_offset, u["update_id"])
    msg = u.get("message", {})
    if str(msg.get("chat", {}).get("id")) != chat_id:
        continue
    text = msg.get("text", "").strip()

    if text.startswith("/approve"):
        # find the draft this is replying to
        replied = msg.get("reply_to_message", {}).get("text", "")
        # strip our own formatting to get raw draft back out
        if replied:
            body = replied.split("📝 *New LinkedIn draft ready*")[-1]
            body = body.split("---")[0].strip()
            post_text = body
    elif text.startswith("/edit"):
        post_text = text[len("/edit"):].strip()
    elif text.startswith("/reject"):
        print("Draft rejected by user. Nothing posted.")

# Save new offset regardless of outcome
with open(STATE_FILE, "w") as f:
    json.dump({"last_update_id": new_offset}, f)

if not post_text:
    print("No approval/edit command found in new messages.")
    exit(0)

# Post to LinkedIn (UGC Posts API)
li_resp = requests.post(
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
)

if li_resp.status_code in (200, 201):
    print("✅ Posted to LinkedIn successfully.")
else:
    print(f"❌ LinkedIn post failed: {li_resp.status_code} {li_resp.text}")
    exit(1)

# Notify back on Telegram
requests.post(
    f"https://api.telegram.org/bot{bot_token}/sendMessage",
    json={"chat_id": chat_id, "text": "✅ Posted to LinkedIn!"},
)
