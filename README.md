# github-notifi-bot

## Description

Telegram bot that delivers real-time notifications about your GitHub repositories
(commits, pull requests, issues, releases, CI runs, stars, forks and more) to
group chats — through GitHub webhooks. Written in Python on top of aiogram 3,
FastAPI and Tortoise-ORM.

## Screenshots

![Screenshot](.github/images/actions.png)

Action messages example

---

![Screenshot](.github/images/list.png)

List of repositories integrated with the bot in chat

## Features

- 🔔 **Real-time notifications** for 18 GitHub event types (see the table
  below) delivered as Telegram-HTML messages.
- 🧰 **Per-chat event toggles** via `/events` — enable/disable each event type
  independently.
- 🔄 **`/reinstall`** — re-syncs the GitHub-side webhook subscription list
  with the bot's current capabilities (run this after the bot adds new event
  types). Stale events are flagged in the `/events` keyboard with ⚠️ and
  blocked from being enabled until you reinstall.
- 🧵 **Forum topic delivery** — `/set_topic` records the active forum topic
  and notifications are routed there. Falls back to General if the topic is
  closed or deleted.
- 👥 **Admin-gated commands** — only chat administrators can integrate, delete,
  set topic, change events or reinstall.
- 🛡 **Structured GitHub error handling** — distinct user-friendly messages
  for invalid/expired token, missing scopes, no admin access, repo not found,
  hook already exists, etc. (no more raw stack traces in the chat).
- 🌟 **Star anti-flood** — per-chat configurable cooldown so a viral repo
  doesn't spam the chat.
- 📦 **Pluggable event architecture** — each event type lives in
  [`app/events/`](app/events) as a single file with a Pydantic schema and a
  formatter, and self-registers on import. Adding a new event is one new file.
- 🔌 **Async webhook delivery** — Telegram calls go through `aiohttp`; the
  webhook auto-retries without `message_thread_id` if the topic is gone, and
  classifies 403 (kicked) separately in logs.

## Supported events

| Event | What triggers it | Notes |
|-------|------------------|-------|
| `ping` | Webhook installation | Auto-fired by GitHub once on hook creation |
| `push` | Commits pushed to a branch | Per-commit file diff stats fetched via the user's token |
| `issues` | Issue lifecycle | Filtered to `opened`, `closed`, `reopened`, `assigned` |
| `issue_comment` | Comments on issues *and* PRs | Filtered to `created`; PR comments are labelled accordingly |
| `pull_request` | PR lifecycle | Filtered to `opened`, `closed`, `reopened`, `ready_for_review`; "merged" rendered with 🟣 |
| `pull_request_review` | Review submitted on a PR | Filtered to `submitted`; icon by review state (✅/🔴/💬/⚪) |
| `pull_request_review_comment` | Inline comment on a PR diff | Filtered to `created`; shows file path |
| `commit_comment` | Comment on a specific commit | Filtered to `created` |
| `star` | Repo starred / unstarred | Anti-flood applies per chat |
| `fork` | Repo forked | Shows total forks count |
| `create` | Branch or tag created | |
| `delete` | Branch or tag deleted | |
| `release` | Release created/published | Filtered to `published`; drafts skipped; prerelease label shown |
| `workflow_run` | GitHub Actions run finished | Filtered to `completed`; icon by conclusion |
| `discussion` | GitHub Discussions lifecycle | Filtered to `created`, `closed`, `reopened`, `answered` |
| `discussion_comment` | Comment on a discussion | Filtered to `created` |
| `deployment_status` | Deployment status transitions | All states; icon by state |
| `member` | Collaborator added | Filtered to `added` |
| `public` | Repo turned public | |

## Project layout

```
app/
├── __main__.py            # entry point (bot + webhook server)
├── commands.py            # Telegram command menu
├── config.py              # TOML config parsing
├── db/
│   ├── models.py          # Tortoise models + EventType enum
│   └── functions.py       # query helpers / domain methods
├── events/                # one file per event: schema + formatter
│   ├── _base.py           # shared nested schemas (User, Repo, Issue, …)
│   ├── _context.py        # EventCtx dataclass
│   ├── _formatting.py     # HTML helpers (truncate, links, escape)
│   ├── _registry.py       # event registry + build_message()
│   ├── push.py            # — per-event modules —
│   ├── pull_request.py
│   ├── workflow_run.py
│   └── …  (19 event files)
├── handlers/
│   ├── admin/             # /error, /mailing, owner-only commands
│   └── user/              # /start, /token, /integrate, /events, /reinstall, …
├── middlewares/
│   └── throttling.py
├── utils/
│   └── hooks.py           # GitHub API: create_webhook, update_webhook, validate, …
└── webhook/
    ├── api.py             # FastAPI endpoint receiving GitHub events
    └── main.py            # uvicorn entry point
```

## TODO

- [ ] **Auth via GitHub App** instead of (or alongside) Personal Access Tokens.
      Use installation tokens with auto-refresh and granular per-repo permissions
      so the user doesn't have to grant a broad PAT.
- [ ] **Filters** — per-chat ignore rules: author (e.g. `dependabot`), branch, label, event subtype
- [ ] **AI summary for large PRs / commits** — client provides API key, model name and provider
      (Anthropic / OpenAI / OpenRouter / etc.); diff + commit titles are sent to the model and the
      generated TL;DR is appended to the notification
- [ ] `/test <repo>` command — send a synthetic webhook payload to verify delivery without pushing
- [ ] `/status` command — per-integration health: `last_event_at`, `events_24h`, healthy/unhealthy
- [ ] **Custom message templates** (Jinja-style) — each chat can override the message format per event
- [ ] **Localization** (en / ru, extensible)
- [ ] **Webhook secret + HMAC verification** (`X-Hub-Signature-256`) — reject forged events
- [ ] **Encrypt GitHub tokens at rest** in the database (Fernet/AES, key from env)
- [ ] **Org mode** — `/integrate myorg/*` to subscribe to all repositories of an organization at once
- [ ] **Stats** — `/stats <period>`: top authors, top repos by activity, ASCII activity graph
- [ ] **Auto-pin important releases** — by label (e.g. `major`) or by semver major bump
- [ ] `/whoami` (DM) — show all repositories and chats the user is subscribed to
- [ ] `/mute <duration>` — temporarily silence notifications in a chat (e.g. `/mute 2h`)
- [ ] **Emoji reactions** on bot messages map to GitHub actions (👍 → approve PR,
      👎 → request changes, 🔁 → re-run failed CI, etc.)
- [ ] **Render GitHub Markdown** in PR / issue bodies as Telegram HTML (headings, lists, links,
      code blocks) instead of raw escaped text
