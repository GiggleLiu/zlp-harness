# zlp-harness

Claude Code plugin providing shared skills for Zulip-based research harness repos. It handles collaborator onboarding, reference downloads into `.knowledge/`, Zulip reply drafting, and scaffolding new `<topic>.harness` repos.

Harness repos stay small: each one provides its own `Makefile`, `CLAUDE.md`, and `.knowledge/` library; this plugin supplies the reusable workflows.

## Getting started

Open [Claude Code](https://claude.com/claude-code) in any directory and paste:

```
install https://github.com/GiggleLiu/zlp-harness as a Claude Code plugin, then invoke the init-harness skill.
```

For the skill list, architecture, and dependencies, see [`CLAUDE.md`](CLAUDE.md).
