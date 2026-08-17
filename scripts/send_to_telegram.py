import os
import requests

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

resp = requests.post(
    f"https://api.telegram.org/bot{bot_token}/sendMessage",
    json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"},
)
resp.raise_for_status()
print("Sent draft to Telegram. Waiting for your reply (checked every 5 min by the approval workflow).")
