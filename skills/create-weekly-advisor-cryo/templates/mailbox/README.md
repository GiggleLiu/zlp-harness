# Messenger Mailbox

This directory is the per-machine mailbox that messenger reads from and writes to for this destination. It is gitignored by convention.

## Layout

- `inbox/<id>/message.md` - frontmatter plus body of an incoming message.
- `inbox/<id>/attachments/<filename>` - binary attachments, if any.
- `inbox/<id>/meta.json` - routing metadata.
- `outbox/<id>.json` - outbound replies or proactive posts. Messenger drains these on the next tick.

Treat `inbox/` as read-only.

## Outbox Envelope

```json
{
  "channel": "zulip",
  "target": {"site": "example", "stream": "project", "topic": "weekly advisor"},
  "body_markdown": "Reply body in markdown.",
  "reply_to": "optional-inbound-message-id",
  "attachments": [],
  "needs_human_review": false
}
```

For weekly advisor posts, `reply_to` is usually absent because the post is proactive.

## Fields

| Field | Required | Notes |
| --- | --- | --- |
| `channel` | yes | Mirror inbound channel for replies; use `zulip` for weekly posts. |
| `target` | yes | Zulip target: `site`, `stream`, and `topic`. |
| `body_markdown` | yes | Message body in plain markdown. |
| `reply_to` | optional | Include for threaded replies to an inbound message. |
| `attachments` | optional | File paths for attachments. |
| `needs_human_review` | optional | If true, messenger should stage instead of sending. |

## Lifecycle

1. The agent writes `outbox/<id>.json`.
2. Messenger drains it.
3. Success moves to `outbox/sent/<id>.json`.
4. Failure moves to `outbox/failed/<id>.json`.
5. Human review moves to `outbox/pending/<id>.json`.

Do not write `.md` files to `outbox/`; the drain expects JSON.
