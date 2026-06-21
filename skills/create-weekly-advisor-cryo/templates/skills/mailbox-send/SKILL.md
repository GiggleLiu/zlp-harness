---
name: mailbox-send
description: Use when a Cryochamber agent needs to send a message through the local mailbox outbox, including replies to mailbox inbox messages or proactive weekly Zulip advisor posts.
---

# mailbox-send

## Overview

Write a valid JSON envelope to `mailbox/outbox/` so the external messenger drain can deliver it. Use this for both replies to `mailbox/inbox/<id>/` and proactive weekly Zulip posts.

## Locate The Mailbox

Default to `$PWD/mailbox` when invoked from a chamber root.

```sh
test -d mailbox/inbox -a -d mailbox/outbox || { echo "no mailbox here"; exit 1; }
```

Do not edit `mailbox/inbox/<id>/`; inbound messages are source-of-truth records.

## Reply To An Inbound Message

Read:

- `mailbox/inbox/<id>/message.md`
- `mailbox/inbox/<id>/meta.json`

Mirror the inbound `channel` and route back to the same thread when possible.

Channel-specific targets:

| Channel | Target keys |
| --- | --- |
| `mail` | `to`, optional `account` |
| `zulip` | `site`, `stream`, `topic` |
| `feishu` | `chat` or `chat_id`, optional `thread`, optional `format` |

Use `reply_to` for the inbound Message-ID or chat message id.

## Proactive Weekly Zulip Post

For a scheduled weekly advisor post there may be no inbound message. In that case write an envelope directly:

```json
{
  "channel": "zulip",
  "target": {
    "site": "<site>",
    "stream": "<stream>",
    "topic": "<topic>"
  },
  "body_markdown": "<weekly advisor note>",
  "attachments": [],
  "needs_human_review": false
}
```

Filename convention: use a stable traceable stem such as `weekly-advisor-YYYY-MM-DD.json`.

Use `needs_human_review: true` for draft-only behavior.

## Write And Verify

```python
import json
from pathlib import Path

envelope = {
    "channel": "zulip",
    "target": {"site": "<site>", "stream": "<stream>", "topic": "<topic>"},
    "body_markdown": "<message body>",
    "attachments": [],
    "needs_human_review": False,
}

out = Path("mailbox/outbox") / "weekly-advisor-YYYY-MM-DD.json"
out.write_text(json.dumps(envelope, indent=2), encoding="utf-8")
```

Then verify:

```sh
python3 -m json.tool mailbox/outbox/<stem>.json >/dev/null
test ! -e mailbox/outbox/sent/<stem>.json
test ! -e mailbox/outbox/failed/<stem>.json
```

If a `sent/` or `failed/` file already exists with the same stem, choose a new stem to avoid accidental resend.

## Report

Tell the operator:

- the outbox path,
- the `channel` and `target`,
- whether `needs_human_review` is set,
- that messenger will move the file to `sent/`, `failed/`, or `pending/`.

## Common Pitfalls

| Pitfall | Fix |
| --- | --- |
| Writing markdown files to `outbox/` | Write JSON envelopes only. |
| Cross-channel replies | Reply through the same channel as the inbound message. |
| Missing `reply_to` for replies | Include it when replying to a specific inbound. |
| Using `reply_to` for weekly posts | Omit it for proactive weekly summaries. |
| Resending with the same stem | Check `sent/` and `failed/` before writing. |
