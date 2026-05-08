# Global workspace store — design

Resolves issue #1 ("Refactor: store message globally - setup locally").

## Problem

A `zlp-harness` repo today contains both **harness configuration** (Makefile, `CLAUDE.md`, `.knowledge/` — committed) and **personal Zulip state** (downloaded messages, cursor state, drafts in `.zulip/` — gitignored). Credentials live elsewhere again at `~/.config/zlp-harness/<config-label>/zuliprc`. Three consequences:

1. Each harness clutters its working tree with a hidden `.zulip/` directory that has no business being co-located with version-controlled files.
2. A user with multiple harnesses on the same Zulip server has the *same* messages mirrored under each repo's `.zulip/` instead of in one place.
3. Credentials and messages live in different roots with different naming conventions, so "where is my Zulip stuff for site X?" has no single answer.

## Goal

The repo holds only static, syncable harness *configuration*. All per-machine personal data — credentials, archived messages, cursor state, drafts — lives under a single global root organized by Zulip workspace, then by channel.

## New layout

```
~/.local/share/zlp-harness/<workspace>/
  zuliprc                            # credential — one per workspace
  <channel-slug>/                    # populated by `zlp` per Zulip stream
    <topic-slug>/*.md                # messages, organized by topic
    _files/                          # attachments
  .run/                              # zlp cursor state (workspace-wide)
  .drafts/                           # in-progress draft messages
```

- `<workspace>` is the Zulip server label (`hkust-gz`, `quantum-info`, `chat`). Zulip's own term for a server is "workspace", so the codebase adopts that name everywhere it currently says `config-label` / `site label` / `credential directory`.
- `<channel-slug>` is the Zulip stream, slugified by `zlp` itself. The Makefile points `zlp` at the workspace root and lets `zlp` create channel subdirs the way it already does today.
- Credentials live at the workspace root rather than `~/.config/...` so a user has *one* directory per Zulip workspace. This is a deliberate departure from strict XDG: discoverability ("here is everything for hkust-gz") matters more than convention purity for this tool.
- Multiple harnesses on the same workspace share `zuliprc` and `.run/` and have their own `<channel-slug>/` subtree (one channel per harness, by convention).

The repo no longer contains a `.zulip/` directory. Per-repo gitignored state is gone; nothing personal lives in the working tree anymore.

**Breaking change.** Existing harnesses keep working with their old Makefile until that Makefile is regenerated from the new template; the upgrade path is `mv ~/.config/zlp-harness/<label>/zuliprc` + `mv <repo>/.zulip/*` into the new workspace dir. Per the issue scope, this PR does not ship migration tooling.

## Naming: `<<CONFIG_LABEL>>` → `<<WORKSPACE>>`

The placeholder used by `init-harness` templates becomes `<<WORKSPACE>>`. The Makefile variable `ZULIP_CONFIG_DIR` becomes `ZULIP_WORKSPACE_DIR`. The exported env vars `zlp` reads (`ZULIP_CONFIG_FILE`, `ZLP_ARCHIVE_ROOT`, `ZLP_RUN_ROOT`) are unchanged — those are the contract with `zlp-cli` and shouldn't churn. The `make zulip-config` contract replaces `ZULIP_CONFIG_DIR_DEFAULT` with `ZULIP_WORKSPACE` + `ZULIP_WORKSPACE_DIR_DEFAULT` + `ZULIP_DRAFTS_DIR`.

## Files that change

### A. Templates (new harnesses)

- **`skills/init-harness/templates/Makefile.tmpl`** — set `ZULIP_WORKSPACE`, `ZULIP_WORKSPACE_DIR_DEFAULT := $(HOME)/.local/share/zlp-harness/<<WORKSPACE>>`, `ZULIP_CONFIG_FILE := $(ZULIP_WORKSPACE_DIR)/zuliprc`, `ZLP_ARCHIVE_ROOT := $(ZULIP_WORKSPACE_DIR)`, `ZLP_RUN_ROOT := $(ZULIP_WORKSPACE_DIR)/.run`. Add `ZULIP_DRAFTS_DIR := $(ZULIP_WORKSPACE_DIR)/.drafts` for skills that stage drafts. Update `make zulip-config` to print the new keys.
- **`skills/init-harness/templates/gitignore.tmpl`** — drop the `.zulip/` line.
- **`skills/init-harness/templates/CLAUDE.md.tmpl`** + **`README.md.tmpl`** — replace `~/.config/zlp-harness/<<CONFIG_LABEL>>/` and `.zulip/` references with the new workspace path.
- **`skills/init-harness/helpers/scaffold.py`** — rename `--config-label` → `--workspace`; substitute `<<WORKSPACE>>`; drop the legacy `<<WORKSPACE_LABEL>>` / `<<CONFIG_LABEL>>` aliases.

### B. Plugin skills

- **`skills/zlp-onboard/SKILL.md`** — Step 0 reads `CFG_ZULIP_WORKSPACE_DIR_DEFAULT`; Steps 4–7 reference the workspace dir and override env var (`ZULIP_WORKSPACE_DIR`).
- **`skills/zulip-reply/SKILL.md`** — initialization detection and draft staging both use `$CFG_ZULIP_WORKSPACE_DIR_DEFAULT` / `$CFG_ZULIP_DRAFTS_DIR`.
- **`skills/zlp-advisor/SKILL.md`** — same archive + drafts path replacements.
- **`skills/init-harness/templates/skills/onboard/SKILL.md`** — prose-only update to reference the workspace dir.

### C. Plugin docs

- **`CLAUDE.md`** (plugin root) — architecture description updated; 1-2 sentence breaking-change note added with the migration command.

## What does *not* change

- `zlp-cli` itself. The plugin only changes which paths it points `zlp` at via env vars.
- The harness scaffold's *committed* layout (Makefile, CLAUDE.md, `.knowledge/`, `.claude/skills/onboard/SKILL.md`).
- The `<topic>` slug. It still names the harness repo and the default stream.
