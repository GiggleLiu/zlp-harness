# zlp-harness

Agent plugin providing shared skills for Zulip-based research harness repos. It handles collaborator onboarding, reference downloads into `.knowledge/`, Zulip reply drafting, scaffolding new `<topic>.harness` repos, and creating scheduled weekly advisor Cryochamber chambers.

Harness repos stay small: each one provides its own `Makefile`, `CLAUDE.md`, and `.knowledge/` library; this plugin supplies the reusable workflows.

## Getting started

Open a supported agent client in any directory and paste:

```
install https://github.com/GiggleLiu/zlp-harness as a plugin, then invoke the init-harness skill.
```

For the skill list, architecture, and dependencies, see [`CLAUDE.md`](CLAUDE.md).
