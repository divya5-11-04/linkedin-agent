# LinkedIn Post Agent (100% free stack)

Manually trigger a workflow with a repo name → get a human-sounding LinkedIn
draft in Telegram → reply `/approve`, `/edit <text>`, or `/reject` → approved
posts go live on LinkedIn automatically. No servers, no paid APIs.

## How it works

1. **`generate-post.yml`** — you trigger this manually (Actions tab → Run
   workflow) with a repo name. It fetches the README/commits, generates a
   draft via Groq (free), validates the draft against a set of rules
   (word count, banned phrases, hashtag limit — see `scripts/validators.py`),
   asks Groq for one revision if it fails those checks, and DMs the result to
   you on Telegram.
2. **`check-approval.yml`** — runs every 10 minutes automatically. Checks if
   you replied `/approve`, `/edit ...`, or `/reject` on Telegram, and if
   approved, posts to LinkedIn.

All network calls (GitHub, Groq, Telegram, LinkedIn) retry up to 3 times with
linear backoff before failing (`scripts/retry.py`) — a single transient 500
doesn't kill a run.

## Design decisions

**Telegram as the approval UI, not a web dashboard.** A dashboard means a
server, a login, and something to keep running. Telegram is already on my
phone, push notifications are free, and replying to a message is a natural
approve/edit/reject interaction — no UI to build or host.

**Polling every 10 minutes instead of a webhook.** GitHub Actions has no way
to hold a persistent listener, and Telegram webhooks need a publicly
reachable HTTPS endpoint, which would mean paying for or self-hosting a
server — the thing this project is explicitly trying to avoid. A 5-10 minute
poll on the free tier costs nothing and the latency is fine for something
that isn't time-critical.

**One LLM call per draft, not a multi-variant "agent."** An earlier version
of this repo (see git history) built a full SENSE→THINK→ACT→EVALUATE→LEARN
pipeline: three post variants per run, an LLM scoring its own outputs on a
quality rubric, and a memory file meant to learn from my edit history over
time. I cut all of it, for two reasons. First, it was never actually wired
into the deployed workflows — a nice-looking package that didn't run.
Second, and more importantly, the "evaluation" in it wasn't real evaluation:
an LLM grading its own output against a rubric it also has access to isn't a
meaningful quality signal without a human-labeled baseline to check it
against. Rather than ship that, I replaced it with something smaller but
honest: rule-based validation in actual code (not just prompt instructions)
for the things that matter — word count, hashtag spam, banned phrases — plus
one automatic revision pass if the model doesn't follow its own rules. If I
revisit multi-variant generation later, it'll be with a real evaluation set
of posts I've personally rated, not a self-graded rubric.

**Persisting state (`telegram_offset.json`, `pending_draft.json`) by
committing it back to the repo.** GitHub Actions runners are ephemeral —
nothing survives between runs unless it's written somewhere durable. Rather
than stand up a database for two small JSON files, each workflow commits its
own state back to the repo with `[skip ci]` so it doesn't trigger itself.
`pending_draft.json` specifically exists so `/approve` can recover the exact
draft text that was sent, instead of re-parsing it out of Telegram's
reply-preview text (which Telegram truncates for long messages) — an earlier
version did the latter and it was fragile.

## One-time setup

### 1. Groq API key
- Sign up at [console.groq.com](https://console.groq.com), create an API key.

### 2. Telegram bot
- Message [@BotFather](https://t.me/BotFather) → `/newbot` → save the token.
- Send your new bot any message, then visit:
  `https://api.telegram.org/bot<[Your_Token_ID]>/getUpdates`
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
permissions"** (needed so the workflows can commit their state files —
`telegram_offset.json` and `pending_draft.json` — back to the repo).

## Usage

1. Go to the **Actions** tab → **Generate LinkedIn Post** → **Run workflow**.
2. Enter the repo full name (e.g. `yourname/cool-project`) and optional
   context (e.g. "emphasize the performance optimization, casual tone").
3. Check Telegram within a minute or two for the draft.
4. Reply to that message with `/approve`, `/edit <your version>`, or `/reject`.
5. Within 10 minutes, it's posted (or check Actions tab → "Check Approval &
   Post" → Run workflow to force an immediate check instead of waiting).

## Testing

The pure logic (draft validation, retry-with-backoff) is unit tested and has
no external dependencies at test time — no live API calls needed to run
these.

```
pip install -r requirements-dev.txt
python -m pytest tests/ -v
```

Everything that touches a real network call (GitHub, Groq, Telegram,
LinkedIn) is exercised by actually running the workflows, not by tests —
mocking four different third-party APIs wasn't worth it for a
single-user personal tool. The parts worth unit testing are the parts with
real logic: rule checking and retry behavior.

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
- **Validation is rule-based, not semantic**: it catches word count, banned
  phrases, and hashtag spam, but can't tell you a draft is boring or
  factually off — that's still on the human reviewing it in Telegram.
- **Voice matching**: for posts to sound more like you specifically, paste
  2-3 of your past LinkedIn posts into `scripts/generate_post.py`'s
  `SYSTEM_PROMPT` as style examples.
