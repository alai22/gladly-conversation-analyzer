# Product Bot (Notion + Claude)

Isolated Slack bot for a **Product** Notion corpus. Separate Slack app, signing secret, bot token, Notion token, and allowlists from the Operations bot (`docs/SLACK_BOT.md`).

## Behavior

1. Slack Events API delivers `app_mention` to `POST /integrations/slack/product/events`.
2. Signature is verified with `PRODUCT_SLACK_SIGNING_SECRET`; webhook returns `200` immediately.
3. Async worker:
   - Ignores bot messages (loop prevention)
   - Optionally enforces `PRODUCT_SLACK_ALLOWED_CHANNEL_IDS`
   - Classifies the question (broad overview vs narrow factual)
   - Searches Notion with `PRODUCT_NOTION_TOKEN` using an extracted topic phrase
   - Ranks hits by title/hub relevance (not Notion recency alone)
   - Loads fuller page content for the top ranked docs, then asks Claude to answer **only** from that context
   - Posts the reply with `chat.postMessage` in-thread using `PRODUCT_SLACK_BOT_TOKEN`

**Notion scope:** Prefer restricting which pages/databases the integration can access in the Notion UI. `PRODUCT_NOTION_ALLOWED_*` env vars are optional extra filters.

### Broad vs narrow retrieval

| | Broad overview | Narrow factual |
|--|----------------|----------------|
| Examples | "tell me about X", "what is X", "overview of X" | Specific how/when/what-length questions |
| Search candidates | ~12 | ~5 |
| Pages loaded | top 3–5 after title/hub ranking | top ~3 |
| Page depth | nested blocks (up to 2 levels) | top-level blocks |
| Synthesis | structured overview; cite page titles; prefer synthesis over abstaining | concise grounded answer |

Ops Slack bot retrieval defaults are unchanged.

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/integrations/slack/product/health` | Config flags (no secrets) |
| `POST` | `/integrations/slack/product/events` | Slack Events API |

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `PRODUCT_BOT_ENABLED` | yes | `1` / `true` to enable; default off |
| `PRODUCT_SLACK_SIGNING_SECRET` | yes (when enabled) | Product Slack app signing secret |
| `PRODUCT_SLACK_BOT_TOKEN` | yes (when enabled) | Product bot OAuth token (`xoxb-…`) |
| `PRODUCT_NOTION_TOKEN` | yes (for answers) | Product Notion integration secret |
| `ANTHROPIC_API_KEY` | yes (for answers) | Shared Claude key |
| `PRODUCT_NOTION_ALLOWED_PAGE_IDS` | no | Optional page filter (in addition to Notion connection scope) |
| `PRODUCT_NOTION_ALLOWED_DATABASE_IDS` | no | Optional database parent filter |
| `PRODUCT_NOTION_PRIORITY_PAGE_IDS` | no | Optional canonical hub page IDs — **ranking boost only** (not required) |
| `PRODUCT_SLACK_ALLOWED_CHANNEL_IDS` | no | Comma-separated channel IDs; empty = all |

**Do not** reuse Operations bot env vars (`SLACK_*`, `NOTION_TOKEN`, etc.) for Product Bot.

## Slack app setup (high level)

1. Create a **separate** Slack app (distinct from Operations).
2. Request URL: `https://<host>/integrations/slack/product/events`.
3. Subscribe to bot event: `app_mention`.
4. Install; set `PRODUCT_SLACK_BOT_TOKEN` and `PRODUCT_SLACK_SIGNING_SECRET`.
5. Create a Product Notion integration; share only the intended pages/databases; set `PRODUCT_NOTION_TOKEN`.
6. Optionally set `PRODUCT_NOTION_ALLOWED_*` for extra filtering.
7. Optionally set `PRODUCT_NOTION_PRIORITY_PAGE_IDS` to boost known hub/strategy pages in ranking.
8. Set `PRODUCT_BOT_ENABLED=1` and redeploy.

## Safety

- Feature-flagged off by default
- HMAC signature verification (5-minute timestamp window)
- Separate in-memory `event_id` dedupe from Operations bot
- No Notion writes
- Scope primarily via Notion connection UI (optional env allowlists)
- Never log tokens or signing secrets

## Rollout checklist

1. Confirm `GET /integrations/slack/product/health` shows Product credentials configured.
2. Optional: set `PRODUCT_SLACK_ALLOWED_CHANNEL_IDS` to a test channel first.
3. Enable `PRODUCT_BOT_ENABLED=1`.
4. `@`-mention the Product bot with a question grounded in shared Notion pages.
5. Confirm Operations bot at `/integrations/slack/events` is unchanged and still uses its own credentials.
