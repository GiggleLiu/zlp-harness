# zlp-harness

Claude Code plugin providing skills for Zulip-based research harness repos.

## Skills

| Skill | Purpose |
|-------|---------|
| `zlp-onboard` | Bootstrap a collaborator's machine: install `zlp-cli`, place `zuliprc`, verify the Zulip bridge. Workspace-agnostic — reads site / default path / stream from each harness's `make zulip-config`. Usually invoked from a harness's project-level `onboard` skill via `Skill("zlp-harness:zlp-onboard")`. |
| `download-ref` | Batch-fetch arXiv/DOI papers into `.knowledge/`, render to markdown, regenerate INDEX. Falls back to SciHub MCP for paywalled DOIs. |
| `zulip-reply` | Pull new Zulip messages, build context from the project library, draft + send a reply. |
| `init-harness` | Scaffold a new `<topic>.harness` repo (Makefile, CLAUDE.md, .knowledge/, .gitignore). |

## Architecture

Each harness repo provides:
- `Makefile` with `ZULIP_STREAM`, the standard `make zulip-*` targets, **and a `make zulip-config` target** that prints stable `KEY=VALUE` lines (`ZULIP_SITE=...`, `ZULIP_STREAM=...`, `ZULIP_WORKSPACE_DEFAULT=...`)
- `CLAUDE.md` with repo-specific conventions
- `.knowledge/` for the reference library
- A thin project-level `.claude/skills/onboard/SKILL.md` that enables this plugin in the user's `~/.claude/settings.json` and then delegates to `Skill("zlp-harness:zlp-onboard")`

The skills are repo-agnostic — they read stream names and workspace conventions from each repo's `make zulip-config` output, not from hardcoded values. Adding fields to `make zulip-config` is additive — older plugin versions ignore unknown lines.

## Dependencies

- `zlp-cli` (pip) — Zulip bridge CLI
- `pymupdf4llm` (pip) — PDF-to-markdown renderer
- `sci-hub-server` MCP (npx) — optional, for paywalled DOI fallback

## Installation

Add to `~/.claude/settings.json`:

```jsonc
"extraKnownMarketplaces": {
  "zlp-harness": {
    "source": { "source": "github", "repo": "GiggleLiu/zlp-harness" }
  }
},
"enabledPlugins": {
  "zlp-harness@zlp-harness": true
}
```

For local development, swap the source for `{ "source": "directory", "path": "/path/to/zlp-harness" }`.

Each harness repo should ship an in-tree `onboard` skill at `.claude/skills/onboard/SKILL.md` that performs this edit automatically for collaborators on first clone, then delegates to `Skill("zlp-harness:zlp-onboard")` once the plugin is loaded. The project-level skill keeps the natural `/onboard` trigger; the namespaced `zlp-harness:zlp-onboard` is only invoked internally.
