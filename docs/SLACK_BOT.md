# Slack Bot (Notion + Claude)

Internal Slack bot that answers `@`-mentions using **read-only Notion search** and **Claude**, then replies in the same thread.

## Behavior

1. Slack Events API delivers `app_mention` to `POST /integrations/slack/events`.
2. Signature is verified; the webhook returns `200` immediately.
3. Async worker:
   - Ignores bot messages (loop prevention)
   - Optionally enforces `SLACK_ALLOWED_CHANNEL_IDS`
   - Searches Notion for the question (token scope + optional page/database filters)
   - Asks Claude to answer **only** from that context
   - Posts the reply with `chat.postMessage` in-thread

If Notion returns no useful context, the bot replies that it could not find an answer (no Claude hallucination from empty context).

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/integrations/slack/health` | Config flags (no secrets) |
| `POST` | `/integrations/slack/events` | Slack Events API |

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SLACK_BOT_ENABLED` | yes | `1` / `true` to enable; default off |
| `SLACK_SIGNING_SECRET` | yes (when enabled) | Slack app signing secret |
| `SLACK_BOT_TOKEN` | yes (when enabled) | Bot OAuth token (`xoxb-…`) |
| `NOTION_TOKEN` | yes (for answers) | Notion integration secret |
| `ANTHROPIC_API_KEY` | yes (for answers) | Existing Claude key |
| `SLACK_ALLOWED_CHANNEL_IDS` | no | Comma-separated channel IDs; empty = all |
| `SLACK_BOT_MODEL` | no | Override model; defaults to `CLAUDE_MODEL` |
| `NOTION_ALLOWED_PAGE_IDS` | no | Optional page filter (in addition to Notion connection scope) |
| `NOTION_ALLOWED_DATABASE_IDS` | no | Optional database parent filter |

**Notion scope:** Prefer restricting which pages/databases the integration can access in the Notion UI. Allowlist env vars are optional extra filters, not required.

## Slack app setup (high level)

1. Create a Slack app with Event Subscriptions.
2. Request URL: `https://<host>/integrations/slack/events` (must pass URL verification).
3. Subscribe to bot event: `app_mention`.
4. OAuth scopes typically include `app_mentions:read`, `chat:write`, and whatever your workspace requires for reading mention text in channels.
5. Install the app; set `SLACK_BOT_TOKEN` and `SLACK_SIGNING_SECRET`.
6. Create a Notion integration, share only the intended pages/databases, set `NOTION_TOKEN`.
7. Set `SLACK_BOT_ENABLED=1` and redeploy.

## Safety

- Feature-flagged off by default
- HMAC signature verification (5-minute timestamp window)
- In-memory `event_id` dedupe for Slack retries
- No Notion writes
- Fail closed on channel allowlist when configured
- Never log tokens or signing secrets

## Rollout checklist

1. Confirm health: `GET /integrations/slack/health` shows signing secret, bot token, Notion, and Anthropic configured.
2. Optional: set `SLACK_ALLOWED_CHANNEL_IDS` to a test channel first.
3. Enable `SLACK_BOT_ENABLED=1`.
4. `@`-mention the bot with a question grounded in shared Notion pages.
5. Confirm thread reply and logs (`channel allowed`, `notion search`, `claude answer`, `Slack reply posted`).
6. Expand channel allowlist or leave empty for all channels once trusted.
