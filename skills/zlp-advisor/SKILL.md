---
name: zlp-advisor
description: Use when the user asks for a weekly advisor check, student TODO follow-up, research supervision update, or current external updates for a zlp-harness Zulip stream.
---

# zlp-advisor

## Overview

Run a weekly advisor pass over the harness Zulip stream: read the last week of discussion, audit student TODOs and project goals, find current reliable external updates, and draft a concise Zulip post. This skill is for recurring supervision; do not use it for ordinary one-off replies.

Use exact dates in summaries. Default "last week" to the last 7 calendar days ending today unless the user specifies a different weekly window.

## Workflow

### Step 1 - Sync Zulip

Read `CLAUDE.md` first for project conventions. Then update the local archive through the Makefile, never by calling `zlp` directly:

```sh
find .zulip -name '*.md' -print -quit 2>/dev/null
# Empty result: first run
make zulip-pull IMPORT_HISTORY=1
# Otherwise
make zulip-pull
```

If the pull fails because credentials are missing, stop and invoke `zlp-onboard`. If the stream has no messages in the selected window, say so and still offer to search for current external updates.

### Step 2 - Build the week view

From `.zulip/`, read messages whose YAML `timestamp` falls in the selected date window. Parse at least:

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

### Step 3 - Audit student TODOs

Identify students from project notes, recurring Zulip participants, or explicit user input. If student identity is ambiguous, ask the user once for the roster before posting.

For each active student, extract TODO-like commitments from this week and the previous weekly advisor/TODO thread. Treat these as TODOs:

- explicit `TODO`, `to do`, `next week`, `plan`, `action item`
- "I will...", "I'll...", "we should..." when assigned to a person
- advisor-assigned tasks acknowledged by the student

For every student, classify:

- **Existing TODOs respected**: continued, completed, explicitly revised, or blocked with evidence.
- **At risk**: a prior TODO was ignored, contradicted, or replaced without acknowledgement.
- **Missing next-week TODO**: no explicit next-week TODO exists.

Do not invent completion status. Cite message permalinks as evidence. Do not overwrite a student's TODO with your own plan unless the draft clearly asks them to confirm or edit it.

### Step 4 - Audit goals and advisor guidance

For each active student or student-owned subproject, identify whether there is a clear goal. A useful goal has:

- an outcome or claim the student is trying to establish
- a key metric, target, benchmark, theorem, proof obligation, dataset result, or concrete artifact
- a near-term checkpoint that can be evaluated next week

Examples:

- experimental: "improve <metric> from A to B on <benchmark> while keeping <cost/error> below C"
- theoretical: "prove/disprove <claim> under <assumptions>, with a minimal counterexample if false"
- literature/survey: "resolve whether <method family> can support <project claim>, backed by 3-5 key references"
- engineering: "deliver <artifact> that reproduces <result> and logs <metric>"

Classify each student's goal status:

- **Clear goal**: goal and key metric/checkpoint are explicit.
- **Needs sharpening**: direction exists, but metric, target, or evaluation criterion is missing.
- **Missing goal**: no explicit project goal found this week or in recent context.

When the goal is missing or vague, remind the student to define one. Frame this as constructive guidance, not criticism:

```md
Please write down the project goal for next week in a checkable form: what metric/result/artifact should move, what target counts as progress, and what evidence you will post by the next weekly check.
```

Add advisor guidance:

- **Evidence-based encouragement**: name concrete progress from the week and cite the Zulip permalink or project artifact. Avoid generic praise.
- **Project significance**: explain why the work matters for the project using evidence from discussions, `.knowledge/`, or reliable external updates.
- **Constructive correction**: if TODOs or goals are missing, state the process fix: carry the TODO forward, mark it blocked, revise it explicitly, or define a measurable goal.
- **Confidence calibration**: distinguish what is solid, what is uncertain, and what evidence would change the assessment.

### Step 5 - Search current reliable sources

This step requires browsing because the request is about the latest updates. Before searching, read the `Reliable update sources (zlp-advisor)` section in `CLAUDE.md` if present. Use it as the project-specific source policy.

Search based on:

- project topic from `CLAUDE.md`
- configured source types, keywords, big names, venues, benchmarks, and URLs from `CLAUDE.md`
- technical keywords and paper names from this week's Zulip messages
- missing references or open questions from the TODO audit

Prefer reliable primary or near-primary sources:

- arXiv, DOI publisher pages, conference/workshop official pages
- official project docs, standards, datasets, benchmark pages, or release notes
- Semantic Scholar/OpenAlex/Crossref only as discovery aids; verify important claims at the primary source

Avoid unsourced social posts, SEO blogs, and generic news summaries unless the project domain specifically depends on them. If search results are weak, say that no high-confidence update was worth posting.

If `CLAUDE.md` has no reliable-source section, pause before relying on broad search. Ask the user to choose source types (`arXiv`, web search, other reliable sources), keywords, and important names/venues to watch. Recommend candidates from `.knowledge/INDEX.md`, recent Zulip messages, and the project purpose, but mark unsupported suggestions as provisional.

Select the 1-4 most important updates. For each update, record:

- source title and link
- date or version, when available
- one-line factual summary
- why it matters for this project
- which Zulip discussion/TODO it relates to

### Step 6 - Draft the advisor post

Use a stable topic unless the project says otherwise: `weekly advisor`. Verify or intentionally create it:

```sh
make zulip-topics | grep -F "weekly advisor"
```

Draft in `.zulip/.drafts/weekly-advisor-YYYY-MM-DD.md`. The posted message should read like a natural advisor note: warm, specific, and constructive. Do not make it look like a compliance report. Use light structure only when it improves readability; prefer short paragraphs and a few bullets over many headings.

```md
Hi all, I looked through the discussion from YYYY-MM-DD to YYYY-MM-DD.

<Warm, evidence-backed opening: what moved forward this week and why it matters for the project. Cite or link the most relevant discussion/artifact.>

For next week, I would like each of you to keep the TODOs explicit and checkable:

- <Student>, <natural-language feedback on current TODOs and goal status>. <If needed: please define the key metric/result/artifact that would count as progress.>
- <Student>, <natural-language feedback...>

I also found a few recent updates that look relevant:

- [<Title>](<url>) (<date>): <summary in plain language>. This matters for us because <relation to project/TODO/discussion>.
```

Internal coverage rules before showing the draft:

- Include every active student in the TODO audit.
- Include each active student's goal status.
- Respect existing TODOs before adding new advice.
- If a clear goal/key metric is missing, explicitly ask the student to define it.
- Include evidence-based encouragement and constructive feedback, tied to project significance.
- Include 1-4 external updates, not more.
- For each update, explicitly state how it relates to or helps the project.
- Keep the final message human and warm; avoid labels like "TODO status: clear/missing" unless the user asks for a strict report.
- No AI signature. The account name is the attribution.

### Step 7 - Review and send

Show the draft to the user first. Do not send until the user explicitly approves.

Before sending, verify the topic:

```sh
make zulip-topics | grep -F "weekly advisor"
```

If the topic does not exist, ask whether to create it or use another topic. Then send:

```sh
make zulip-send TOPIC="weekly advisor" MSG_FILE=".zulip/.drafts/weekly-advisor-YYYY-MM-DD.md"
make zulip-pull
```

After sending, confirm that the post was mirrored back into `.zulip/`; retry `make zulip-pull` once if needed.

## Done Checklist

- [ ] Zulip archive synced before analysis.
- [ ] Exact date window stated.
- [ ] `CLAUDE.md` reliable-source preferences were used, or the user was asked to choose them.
- [ ] Every active student has a TODO status.
- [ ] Every active student or student-owned subproject has a goal/key-metric status.
- [ ] Prior TODOs are respected, carried forward, or explicitly flagged.
- [ ] Missing or vague goals trigger a request to define a measurable/checkable goal.
- [ ] Encouragement or constructive feedback is specific and evidence-backed.
- [ ] Project significance is explained with evidence.
- [ ] Latest external updates were checked with browsing.
- [ ] 1-4 reliable-source updates included, each with relation to the project.
- [ ] Draft shown to the user before posting.
- [ ] Sent message mirrored back into `.zulip/`.

## Common Mistakes

| Mistake | Fix |
| --- | --- |
| Treating this as a normal reply | This is a weekly supervision pass: TODO audit plus external updates. |
| Assigning new work while ignoring existing TODOs | Audit existing TODOs first, then add requests only when they do not conflict. |
| Letting students work without a clear target | Ask for a goal with a metric, benchmark, proof obligation, or concrete artifact. |
| Generic encouragement | Tie encouragement to specific evidence and the project's significance. |
| Guessing student status | Use Zulip evidence; mark unknown or blocked when evidence is absent. |
| Posting stale "latest" updates | Browse current reliable sources during the run. |
| Listing papers without relevance | Each update must say how it helps this project. |
| Sending without approval | Always show the draft and wait for explicit approval. |
