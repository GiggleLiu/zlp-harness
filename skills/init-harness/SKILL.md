---
name: init-harness
description: Use when the user wants to scaffold a new research-discussion harness — a private GitHub repo wired to a Zulip stream on zulip.hkust-gz.edu.cn, with `.knowledge/` for papers and a Makefile for the bridge. Triggers on "create a new harness", "scaffold a harness", "init harness for <topic>", "/init-harness", "set up a harness like qec.harness for X". Self-contained: bundles the canonical Makefile, CLAUDE.md template, and three sub-skills (onboard, download-ref, zulip-reply); does not depend on any source repo.
---

# init-harness

## When to use

- The user wants a brand-new `<topic>.harness` repo modelled on the proven layout: Makefile + CLAUDE.md + .knowledge/ + Zulip bridge + the three sub-skills (`onboard`, `download-ref`, `zulip-reply`).
- Trigger phrases: "create a new harness for <X>", "scaffold a harness", "init harness", "/init-harness", "set up a harness like qec.harness for <X>", "bootstrap the <X>.harness repo".

Do NOT use when:
- The user already has a harness and just needs **their machine** wired up — that's the bundled `onboard` skill, which this skill chains into as Phase 3.
- The user only needs a Zulip stream and no repo — `zlp send` directly is enough.
- The user wants to add a **paper draft** (LaTeX) to an existing harness — different workflow; the `.gitignore` already has the LaTeX entries set up but no scaffolding for `main.tex` exists yet.

## What gets scaffolded

```
<topic>.harness/
  Makefile                       # zulip-* targets, ZULIP_STREAM substituted
  CLAUDE.md                      # repo conventions for future Claude sessions
  README.md                      # single-prompt onboarding instruction
  AGENTS.md                      # @CLAUDE.md
  .gitignore                     # LaTeX + .zulip/ + .knowledge/.raw + .claude/settings.local
  .knowledge/
    INDEX.md                     # placeholder, overwritten on first download-ref run
```

The `onboard`, `download-ref`, and `zulip-reply` skills are **not** bundled per-repo — they are provided by the `zlp-harness` plugin. Collaborators install the plugin once; it works across all harness repos.

All scaffold templates are bundled inside this skill at `templates/`. The skill does **not** read from any other repo — it is a closed unit.

## Inputs (collect once, up front)

Bundle the questions into one `AskUserQuestion` exchange — don't ping per-field.

| Input | Default | Notes |
| --- | --- | --- |
| `topic` | (required) | lowercase, hyphenated slug. Examples: `qec`, `attention-solids`, `llm`. Used in repo / stream / file paths. |
| `target-dir` | (required) | absolute path or expression like `~/code/<topic>.harness`. Must be empty or non-existent (the helper refuses non-empty unless `--force`). |
| `zulip-stream` | `project-<topic>` | the hkust-gz stream the bridge will target. Must already exist on Zulip — created via the web UI by an admin. |
| `github-remote` | (optional) | `<org>/<repo>` for the README clone link, e.g. `CodingThrust/<topic>.harness`. Empty leaves a `<org>/<repo>` placeholder for the user to fix later. |
| `topic-blurb` | (optional) | one paragraph for "Repository purpose". Empty leaves a TODO marker; user can edit `CLAUDE.md` afterwards. |
| `git-init` | yes / no | run `git init` + a single seed commit. Default yes. |

## Workflow

```dot
digraph init_harness {
    "Collect inputs" [shape=doublecircle];
    "Run scaffold.py" [shape=box];
    "Verify (Done checklist)" [shape=box];
    "github-remote provided?" [shape=diamond];
    "User wants gh repo create now?" [shape=diamond];
    "gh repo create + push" [shape=box];
    "cd into target & invoke onboard skill" [shape=box];
    "Hand off to user" [shape=doublecircle];

    "Collect inputs" -> "Run scaffold.py" -> "Verify (Done checklist)";
    "Verify (Done checklist)" -> "github-remote provided?";
    "github-remote provided?" -> "User wants gh repo create now?" [label="yes"];
    "github-remote provided?" -> "cd into target & invoke onboard skill" [label="no"];
    "User wants gh repo create now?" -> "gh repo create + push" [label="yes"];
    "User wants gh repo create now?" -> "cd into target & invoke onboard skill" [label="no"];
    "gh repo create + push" -> "cd into target & invoke onboard skill";
    "cd into target & invoke onboard skill" -> "Hand off to user";
}
```

### Phase 1 — Scaffold

Run the bundled helper. The `SKILL_DIR` must point to wherever this skill is installed — if loaded from the `zlp-harness` plugin, use the plugin cache path; if loaded from `~/.claude/skills/init-harness`, use that. Claude: resolve this by finding `scaffold.py` via the skill's own directory (the directory containing this `SKILL.md`).

```sh
# Resolve SKILL_DIR to this skill's directory (where SKILL.md lives).
# If invoked from a plugin, that's the plugin cache path.
# If invoked from ~/.claude/skills/init-harness, that's the global path.
SKILL_DIR="<path-to-this-skill's-directory>"

python3 "$SKILL_DIR/helpers/scaffold.py" \
  --topic           "<topic>" \
  --target-dir      "<target-dir>" \
  --zulip-stream    "project-<topic>" \
  --github-remote   "CodingThrust/<topic>.harness" \
  --topic-blurb     "<one paragraph, or empty>" \
  --git-init                                      # omit to skip git init
```

The helper:
1. Validates `--topic` is lowercase + hyphenated.
2. Refuses to scaffold into a **non-empty** target unless `--force` is passed (don't pass `--force` without explicit user permission — the destination might be in-progress work).
3. Verifies all required template files exist inside `templates/` before writing anything.
4. Renders `Makefile`, `CLAUDE.md`, `README.md`, `.knowledge/INDEX.md` from `*.tmpl` with `<<TOPIC>>`, `<<ZULIP_STREAM>>`, `<<GITHUB_REMOTE>>`, `<<TOPIC_BLURB>>` substituted.
5. Copies `AGENTS.md` and `.gitignore` verbatim (no substitution needed — already generic).
6. Recursively copies `.claude/skills/{onboard,download-ref,zulip-reply}/`. SKILL.md inside each gets the same substitution pass; `.py` helper files in `download-ref/helpers/` are copied byte-for-byte.
7. If `--git-init`: `git init`, `git add .`, single commit `scaffold <topic>.harness from init-harness skill`.
8. Prints the file tree it wrote and a `next steps` block.

### Phase 2 — (Optional) create the GitHub repo

If `--github-remote` was provided AND `gh` is on `$PATH` AND the user agrees, run from inside `<target-dir>`:

```sh
cd "<target-dir>"
gh repo create "<github-remote>" --private --source=. --push \
  --description "Reference / discussion harness for <topic>."
```

Confirm with the user before running — `gh repo create` is observable to the org and pushes the seed commit. Don't bundle this into Phase 1 silently.

If the user wants to invite a collaborator afterwards (the original `qec.harness` invited `nzy1997`):

```sh
gh repo edit "<github-remote>" --add-collaborator <github-handle>
```

Skip this whole phase if `github-remote` is empty.

### Phase 3 — Onboard the user to the new harness

`onboard` is bundled inside the new harness at `.claude/skills/onboard/`. It reads from the harness's `Makefile`, so it must be invoked **with the new harness as cwd**:

```sh
cd "<target-dir>"
# Then read and follow .claude/skills/onboard/SKILL.md directly.
# `onboard` is a project-local skill — it is NOT in the global Skill tool
# registry, so Skill(onboard) will fail unless the user launched Claude Code
# from inside the new harness directory.
```

Notes:
- The Zulip *workspace* (hkust-gz.edu.cn) is shared across all harnesses on this machine. If the user has already onboarded a previous harness, `onboard`'s preflight reports everything green and finishes in one step. That's expected.
- If the `<zulip-stream>` doesn't yet exist on Zulip, `make zulip-topics` returns nothing (or an error). The bridge **cannot** auto-create the stream — an admin must create it via the Zulip web UI first. Tell the user; don't try to work around it.
- `onboard`'s `description` field references "this harness repo" generically — the bundled copy is already topic-agnostic, no per-harness patching needed.

### Phase 4 — Hand off

Print a tight summary so the user knows what they own next:

```
Harness scaffolded at <target-dir>.

Next steps for the user:
  1. cd <target-dir>
  2. Edit CLAUDE.md — fill in "Repository purpose" and any linked external repos
     (group code, scratchpad issue trackers).
  3. Add the first references via the `download-ref` skill.
  4. (If you skipped Phase 2) push to GitHub manually and invite collaborators.
  5. Tell collaborators to clone and run /onboard.
```

## Common mistakes

| Mistake | Fix |
| --- | --- |
| Picking a `topic` with uppercase / spaces (e.g. `Attention Solids`) | Use lowercase, hyphenated (`attention-solids`). The slug appears in repo names, stream names, file paths — none of those should need shell quoting. The helper refuses uppercase / whitespace and exits 2. |
| Pointing `--target-dir` at a populated directory | The helper refuses unless `--force` is passed. Don't pass `--force` without explicit user OK — you might clobber in-progress work. Pick a fresh directory instead. |
| Reading from `.../qec/.claude/skills/...` while running this skill | Don't. This skill is **standalone**: every template lives under this skill's `templates/` directory. If you find yourself hand-copying from another repo, you've taken a wrong turn — re-run the helper. |
| Skipping the GitHub-remote question because it's "optional" | Ask anyway. Without it the README contains a `<org>/<repo>` placeholder that breaks the one-line onboarding paste in `README.md`. Easier to set it now than retrofit. |
| Pointing `ZULIP_STREAM` at a stream that doesn't exist on Zulip yet | The bridge can't create streams. Have the user (or workspace admin) make the stream on the web UI first; only then will `make zulip-topics` succeed. |
| Running Phase 3 (`onboard`) without `cd`-ing into the new repo | `onboard` runs `make zulip-whoami`, which reads the **current** repo's `Makefile`. Wrong cwd ⇒ wrong stream / wrong workspace. Always switch directories before invoking. |
| Editing the templates without testing the next scaffold | `templates/` is the source of truth for every future harness; a typo here propagates. After editing any `*.tmpl`, run the helper into `/tmp/scratch-harness` to verify the rendered output is what you expected. |
| Bundling `__pycache__/` from the local machine into `templates/` | The helper's `rglob` skips `__pycache__` parts explicitly, but if you ever update the bundled `download-ref/helpers/`, do a `find templates -name __pycache__ -exec rm -rf {} +` first. |

## Done checklist

After the helper finishes, verify (the user might do this themselves; if they don't, you do):

- [ ] `<target-dir>/Makefile` exists; `grep ZULIP_STREAM <target-dir>/Makefile` shows the new stream name (not `<<ZULIP_STREAM>>` and not `project-qec`).
- [ ] `grep -r '<<TOPIC>>\|<<ZULIP_STREAM>>\|<<GITHUB_REMOTE>>\|<<TOPIC_BLURB>>' <target-dir>` returns nothing (all placeholders substituted).
- [ ] The `zlp-harness` plugin is enabled in the user's Claude settings (provides `onboard`, `download-ref`, `zulip-reply` skills).
- [ ] `<target-dir>/.knowledge/INDEX.md` exists with the topic name in its title line.
- [ ] If `--git-init`: `<target-dir>/.git/` exists and `git -C <target-dir> log --oneline` shows the seed commit.
- [ ] If Phase 2 ran: `gh repo view <github-remote>` succeeds.
- [ ] If Phase 3 ran: `make -C <target-dir> zulip-whoami` returns the user's account (assuming the Zulip stream exists on the server).
- [ ] User has been told to edit `CLAUDE.md`'s "Repository purpose" placeholder.
