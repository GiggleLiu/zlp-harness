# zlp-harness

Claude Code plugin providing skills for Zulip-based research harness repos.

## Skills

| Skill | Purpose |
|-------|---------|
| `zlp-onboard` | Bootstrap a collaborator's machine: install `zlp-cli`, help download `zuliprc`, create the global workspace directory, verify the Zulip bridge. Site-agnostic — reads site / workspace path / stream from each harness's `make zulip-config`. Usually invoked from a harness's project-level `onboard` skill via `Skill("zlp-harness:zlp-onboard")`. |
| `download-ref` | Batch-fetch arXiv/DOI papers into `.knowledge/`, render to markdown, regenerate INDEX. Falls back to SciHub MCP for paywalled DOIs. |
| `zulip-reply` | Pull new Zulip messages, build context from the project library, draft + send a reply. |
| `zlp-advisor` | Weekly advisor pass: sync recent Zulip discussion, audit student TODOs, search `CLAUDE.md`-configured reliable current sources, draft a weekly update. |
| `init-harness` | Scaffold a new `<topic>.harness` repo (Makefile, CLAUDE.md, .knowledge/, .gitignore). |

## Architecture

Each harness repo provides:
- `Makefile` with `ZULIP_STREAM`, the standard `make zulip-*` targets, **and a `make zulip-config` target** that prints stable `KEY=VALUE` lines (`ZULIP_SITE=...`, `ZULIP_STREAM=...`, `ZULIP_WORKSPACE=...`, `ZULIP_WORKSPACE_DIR_DEFAULT=...`, `ZULIP_DRAFTS_DIR=...`)
- `CLAUDE.md` with repo-specific conventions
- `.knowledge/` for the reference library
- A thin project-level `.claude/skills/onboard/SKILL.md` that enables this plugin in the user's `~/.claude/settings.json` and then delegates to `Skill("zlp-harness:zlp-onboard")`

The skills are repo-agnostic — they read stream names and workspace conventions from each repo's `make zulip-config` output, not from hardcoded values. Adding fields to `make zulip-config` is additive — older plugin versions ignore unknown lines.

All per-machine personal state — credentials, archived messages, cursor state, and drafts — lives in one global workspace directory at `~/.local/share/zlp-harness/<workspace>/`, where `<workspace>` is the Zulip server slug (`hkust-gz`, `quantum-info`). Multiple harnesses on the same Zulip server share that directory. The repo working tree only holds syncable harness configuration; nothing personal is gitignored inside it.

**Breaking change vs. earlier versions of this plugin:** message archive moved from `<repo>/.zulip/` to `~/.local/share/zlp-harness/<workspace>/`, and credentials moved from `~/.config/zlp-harness/<label>/` to that same workspace dir. To upgrade an existing harness: regenerate its `Makefile` from the new template (or hand-port the `ZULIP_WORKSPACE*` block), then `mv ~/.config/zlp-harness/<label>/zuliprc ~/.local/share/zlp-harness/<workspace>/zuliprc` and `mv <repo>/.zulip/* ~/.local/share/zlp-harness/<workspace>/`.

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
