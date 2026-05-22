---
name: zlp-advisor
description: Use when the user asks for a weekly advisor check, student TODO follow-up, research supervision update, or current external updates for a zlp-harness Zulip stream.
---

# zlp-advisor

## Overview

Run a weekly advisor pass over the harness Zulip stream: read the last week of discussion, audit student TODOs, find current reliable external updates from the last month, and draft a concise Zulip post. This skill is for recurring supervision; do not use it for ordinary one-off replies.

Use exact dates in summaries. Default "last week" to the last 7 calendar days ending today unless the user specifies a different weekly window.

## Workflow

### Step 1 - Sync Zulip

Read `CLAUDE.md` first for project conventions. Resolve the workspace path from `make zulip-config`, then update the archive through the Makefile, never by calling `zlp` directly:

```sh
eval "$(make zulip-config | sed 's/^\([^=]*\)=\(.*\)$/CFG_\1=\x27\2\x27/')"
WS_DIR="${ZULIP_WORKSPACE_DIR:-$CFG_ZULIP_WORKSPACE_DIR_DEFAULT}"
find "$WS_DIR" -path '*/.*' -prune -o -name '*.md' -print -quit 2>/dev/null
# Empty result: first run
make zulip-pull IMPORT_HISTORY=1
# Otherwise
make zulip-pull
```

If the pull fails because credentials are missing, stop and invoke `zlp-onboard`. If the stream has no messages in the selected window, say so and still offer to search for current external updates.

### Step 2 - Build the week view

From `$WS_DIR`, read messages whose YAML `timestamp` falls in the selected date window. Parse at least:

- `sender_full_name`
- `timestamp`
- `subject`
- `permalink`
- `_archive.attachments`
- body text after the closing frontmatter marker

Open attachments referenced by `_archive.attachments`. Read 3-5 neighboring messages in the same topic when a TODO or technical claim needs context.

Produce a private working summary grouped by topic:

```md
- <date> [<topic>] <sender>: <gist> (<permalink>)
```

### Step 3 - Audit the overall TODO list

Identify students from project notes, recurring Zulip participants, or explicit user input. If a roster is ambiguous, ask the user once before posting.

Build **one consolidated TODO table** across the whole team — not a separate audit per student. Pull TODO-like commitments from this week and the previous weekly advisor/TODO thread. Treat these as TODOs:

- explicit `TODO`, `to do`, `next week`, `plan`, `action item`
- "I will...", "I'll...", "we should..." when assigned to a person
- advisor-assigned tasks acknowledged by the student

For every TODO, record: a one-line description, the owner, and a status. Statuses:

- **Done** — explicitly completed this week.
- **In progress** — work continued or was explicitly revised/blocked.
- **At risk** — a prior TODO was ignored, contradicted, or replaced without acknowledgement.
- **New** — newly proposed for next week.

Do not invent completion status; rely on what Zulip actually shows. Do not overwrite a TODO with your own plan unless the draft clearly asks the owner to confirm or edit it.

### Step 4 - Search current reliable sources (last 30 days only)

Browse for **updates published within the last 30 days** (calendar days, ending today). Anything older is out of scope for this section. Before searching, read the `Reliable update sources (zlp-advisor)` section in `CLAUDE.md` if present and use it as the source policy.

Search based on:

- project topic from `CLAUDE.md`
- configured source types, keywords, big names, venues, benchmarks, and URLs from `CLAUDE.md`
- technical keywords and paper names from this week's Zulip messages
- missing references or open questions from the TODO audit

Prefer reliable primary or near-primary sources:

- arXiv, DOI publisher pages, conference/workshop official pages
- official project docs, standards, datasets, benchmark pages, or release notes
- Semantic Scholar / OpenAlex / Crossref only as discovery aids; verify important claims at the primary source

Avoid unsourced social posts, SEO blogs, and generic news summaries unless the project domain specifically depends on them. If search results are weak, say so and post fewer (or zero) external updates rather than padding.

If `CLAUDE.md` has no reliable-source section, pause and ask the user to choose source types, keywords, and important names/venues to watch.

**Deduplicate before recommending.** For every candidate update, check:

- `.knowledge/INDEX.md` and `.knowledge/` filenames — skip if the arXiv ID, DOI, or title already appears.
- Recent Zulip messages (at least the last 8 weeks) — skip if the same paper/release was already linked or discussed.
- Earlier `weekly advisor` posts in `$WS_DIR` — skip if already recommended.

Match on arXiv ID, DOI, or normalized title (lowercased, punctuation stripped). When in doubt, do not recommend; note it as a near-duplicate in your working notes instead.

Select **0-3** updates that survive both the recency and dedup filters. For each, record:

- title and link
- publication date (must be within the last 30 days)
- one-line factual summary
- why it matters for this project (tied to a TODO, discussion, or `.knowledge/` reference)

### Step 5 - Draft the advisor post

Use the topic `weekly advisor` unless the project says otherwise. Verify it:

```sh
make zulip-topics | grep -F "weekly advisor"
```

Draft in `$CFG_ZULIP_DRAFTS_DIR/weekly-advisor-YYYY-MM-DD.md` (the workspace's `.drafts/` subdir, never inside the repo). Keep it short and human — a brief advisor note, not a report. Prefer short paragraphs and a few bullets.

```md
Hi all, quick check-in for YYYY-MM-DD to YYYY-MM-DD.

<One short paragraph: the most important thing that moved this week, with a link.>

TODOs:

| TODO | Owner | Status |
| --- | --- | --- |
| <one-line task> | @<owner> | Done / In progress / At risk / New |
| <one-line task> | @<owner> | ... |

Recent reads (last 30 days):

- [<Title>](<url>) (<date>) — <one line on why it matters here>
```

Rules before showing the draft:

- Use a single TODO table; do not split per student. Every open TODO (across the team) should appear as a row with the owner flagged.
- Respect existing TODOs before adding new ones. Carried-over items keep their original wording where possible.
- External updates section: 0-3 entries, every entry within the last 30 days, none duplicating `.knowledge/`, prior Zulip messages, or earlier weekly-advisor posts. Drop the section entirely if nothing qualifies.
- No AI signature. The account name is the attribution.

### Step 6 - Review and send

Show the draft to the user first. Do not send until the user explicitly approves.

Before sending, verify the topic exists:

```sh
make zulip-topics | grep -F "weekly advisor"
```

If the topic does not exist, ask whether to create it or use another topic. Then send:

```sh
make zulip-send TOPIC="weekly advisor" MSG_FILE="$CFG_ZULIP_DRAFTS_DIR/weekly-advisor-YYYY-MM-DD.md"
make zulip-pull
```

After sending, confirm that the post was mirrored back into the workspace archive; retry `make zulip-pull` once if needed.

## Done Checklist

- [ ] Zulip archive synced before analysis.
- [ ] Exact date window stated.
- [ ] Single consolidated TODO table, one row per open TODO, owner flagged on every row.
- [ ] Every row has a status: Done / In progress / At risk / New.
- [ ] Prior TODOs are respected, carried forward as rows, or explicitly flagged At risk.
- [ ] External updates (if any) are all dated within the last 30 days.
- [ ] External updates checked against `.knowledge/`, recent Zulip, and prior weekly-advisor posts — no duplicates.
- [ ] Each external update states how it matters for this project.
- [ ] Draft shown to the user before posting.
- [ ] Sent message mirrored back into the workspace archive.

## Common Mistakes

| Mistake | Fix |
| --- | --- |
| Treating this as a normal reply | This is a weekly supervision pass: TODO audit plus current external updates. |
| Splitting TODOs into per-student sections | One consolidated table; flag the owner in the row. |
| Assigning new work while ignoring existing TODOs | Carry prior TODOs forward as rows first, then add new rows only when they do not conflict. |
| Inventing completion status | Use what Zulip actually shows; mark At risk when there is no acknowledgement. |
| Generic encouragement | Tie feedback to a specific TODO row. |
| Guessing student status | Use Zulip evidence; mark unknown or blocked when evidence is absent. |
| Posting stale "latest" updates | Only include sources published within the last 30 days. |
| Recommending a paper already in the library | Check `.knowledge/INDEX.md`, recent Zulip, and prior weekly-advisor posts before listing. |
| Listing papers without relevance | Each update must say how it helps this project. |
| Padding the updates section | 0-3 entries; drop the section if nothing qualifies. |
| Sending without approval | Always show the draft and wait for explicit approval. |
