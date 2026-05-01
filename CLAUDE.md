# zlp-harness

Claude Code plugin providing skills for Zulip-based research harness repos.

## Skills

| Skill | Purpose |
|-------|---------|
| `onboard` | Bootstrap a collaborator's machine: install `zlp-cli`, place `zuliprc`, verify the Zulip bridge. |
| `download-ref` | Batch-fetch arXiv/DOI papers into `.knowledge/`, render to markdown, regenerate INDEX. Falls back to SciHub MCP for paywalled DOIs. |
| `zulip-reply` | Pull new Zulip messages, build context from the project library, draft + send a reply. |
| `init-harness` | Scaffold a new `<topic>.harness` repo (Makefile, CLAUDE.md, .knowledge/, .gitignore). |

## Architecture

Each harness repo provides:
- `Makefile` with `ZULIP_STREAM` and `make zulip-*` targets
- `CLAUDE.md` with repo-specific conventions
- `.knowledge/` for the reference library

The skills are repo-agnostic — they read stream names and conventions from each repo's `Makefile` and `CLAUDE.md`.

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

Each harness repo should ship an in-tree `onboard` skill at `.claude/skills/onboard/SKILL.md` that performs this edit automatically for collaborators on first clone.
