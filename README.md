# LinkedIn Post Agent (100% free stack)

Manually trigger a workflow with a repo name → get a human-sounding LinkedIn
draft in Telegram → reply `/approve`, `/edit <text>`, or `/reject` → approved
posts go live on LinkedIn automatically. No servers, no paid APIs.

## How it works

1. **`generate-post.yml`** — you trigger this manually (Actions tab → Run
   workflow) with a repo name. It fetches the README/commits, generates a
   draft via Groq (free), and DMs it to you on Telegram.
2. **`check-approval.yml`** — runs every 10 minutes automatically. Checks if
   you replied `/approve`, `/edit ...`, or `/reject` on Telegram, and if
   approved, posts to LinkedIn.

## One-time setup

### 1. Groq API key
- Sign up at [console.groq.com](https://console.groq.com), create an API key.

### 2. Telegram bot
- Message [@BotFather](https://t.me/BotFather) → `/newbot` → save the token.
- Send your new bot any message, then visit:
  `https://api.telegram.org/bot<8925785320:AAEu6Nx8A89Q_p9ysnjMLX1TJsJ9537Cpy4>/getUpdates`
  and copy your `chat.id` from the JSON response.

### 3. LinkedIn access token
- Create an app at [linkedin.com/developers/apps](https://www.linkedin.com/developers/apps)
- Request the **"Share on LinkedIn"** and **"Sign In with LinkedIn using OpenID
  Connect"** products (self-serve, usually instant).
- Add redirect URL `http://localhost:8000/callback` under Auth settings.
- Run locally:
  ```
  pip install requests
  CLIENT_ID=xxx CLIENT_SECRET=yyy python scripts/get_linkedin_token.py
  ```
  This prints your access token + person URN.
- ⚠️ Token expires every ~60 days — re-run the script to refresh and update
  the GitHub secret when it does. (There's no free way around this; LinkedIn
  doesn't offer long-lived tokens for personal apps.)

### 4. Add GitHub repo secrets
Repo → Settings → Secrets and variables → Actions → New repository secret:

| Secret | Value |
|---|---|
| `GROQ_API_KEY` | from step 1 |
| `TELEGRAM_BOT_TOKEN` | from step 2 |
| `TELEGRAM_CHAT_ID` | from step 2 |
| `LINKEDIN_ACCESS_TOKEN` | from step 3 |
| `LINKEDIN_PERSON_URN` | from step 3 |

### 5. Enable Actions write permissions
Settings → Actions → General → Workflow permissions → **"Read and write
permissions"** (needed so the approval-checker can commit its offset file).

## Usage

1. Go to the **Actions** tab → **Generate LinkedIn Post** → **Run workflow**.
2. Enter the repo full name (e.g. `yourname/cool-project`) and optional
   context (e.g. "emphasize the performance optimization, casual tone").
3. Check Telegram within a minute or two for the draft.
4. Reply to that message with `/approve`, `/edit <your version>`, or `/reject`.
5. Within 10 minutes, it's posted (or check Actions tab → "Check Approval &
   Post" → Run workflow to force an immediate check instead of waiting).

## Notes / limitations

- **10-minute polling delay**: GitHub Actions' minimum cron interval is 5
  min but it's not guaranteed to run exactly on time — expect up to ~15 min
  latency between approving and the post going live. Run the check workflow
  manually if you want it instant.
- **Free repo minutes**: public repos get unlimited Action minutes; private
  repos get 2,000 free min/month, which is plenty for this (each run is
  seconds).
- **Groq quality**: good but a notch below GPT-4/Claude-class for nuanced
  tone. If a draft feels off, just use `/edit` with your own rewrite — the
  approval step is doing exactly what it's there for.
- **Voice matching**: for posts to sound more like you specifically, paste
  2-3 of your past LinkedIn posts into `scripts/generate_post.py`'s
  `SYSTEM_PROMPT` as style examples.
