---
name: zlp-onboard
description: Use when a new collaborator on any zlp-harness-based repo needs to bootstrap their machine — checks what's already installed, walks them through getting a Zulip API key for the harness's site (read from `make zulip-config`), sets up the workspace path, and verifies the bridge works. Triggers on "I just cloned this", "first time setup", "onboard me", "help me get started", "set up zulip", "/zlp-onboard", or when invoked by a harness's project-level onboard skill via `Skill("zlp-harness:zlp-onboard")`.
---

# zlp-onboard

## When to use

- A collaborator on a harness repo (LLM, qec, attention-solids, etc.) just cloned and is running it for the first time.
- `make zulip-whoami` fails with "zuliprc not found", "command not found: zlp", or the per-target `$(error) ZULIP_WORKSPACE is not set` guard.
- The harness's project-level `onboard` skill invokes this one after enabling the plugin.

Do NOT use:
- For an *existing* setup hitting a temporary error — that's a bug to debug, not onboarding. Look at the error first.
- Outside a zlp-harness-style repo. The skill assumes the cwd has a `Makefile` exposing the `make zulip-config` target plus the standard `make zulip-*` set.

## Inputs

The skill is interactive — it detects state and asks for what's missing. No required arguments.

## Workflow

### Step 0 — Read workspace config

Every site/path/stream value below is read from the harness's Makefile via `make zulip-config`. Run this once at the start of the skill and use the resulting `CFG_*` env vars throughout.

```sh
# Load workspace config from the harness's Makefile. Single-quote each value
# so future stream names with whitespace or shell metacharacters parse safely.
eval "$(make zulip-config | sed 's/^\([^=]*\)=\(.*\)$/CFG_\1=\x27\2\x27/')"

# Should now have:
#   $CFG_ZULIP_SITE              e.g. https://quantum-info.zulipchat.com
#   $CFG_ZULIP_STREAM            e.g. LLM项目推进
#   $CFG_ZULIP_WORKSPACE_DEFAULT e.g. /Users/<you>/zulip-workspaces/quantum-info

echo "site:    $CFG_ZULIP_SITE"
echo "stream:  $CFG_ZULIP_STREAM"
echo "default workspace: $CFG_ZULIP_WORKSPACE_DEFAULT"
```

If `make zulip-config` doesn't exist or returns nothing, the harness is on an older Makefile that predates the contract. Tell the user to run the harness's project-level `onboard` skill first (which should add `zulip-config`), or to update the Makefile by hand following the zlp-harness CLAUDE.md.

### Step 1 — Detect what's already done

Before asking anything, check the four prerequisites in parallel:

```sh
echo "=== zlp-cli installed? ==="
command -v zlp && (zlp whoami 2>/dev/null | head -1 || echo "(cli found)") || echo "(missing)"

echo "=== ZULIP_WORKSPACE env var set? ==="
echo "ZULIP_WORKSPACE=${ZULIP_WORKSPACE:-(unset)}"

echo "=== zuliprc present? ==="
WS="${ZULIP_WORKSPACE:-$CFG_ZULIP_WORKSPACE_DEFAULT}"
ls -la "$WS/zuliprc" 2>&1 || echo "(missing at $WS/zuliprc)"

echo "=== pymupdf4llm available to /usr/bin/env python3? ==="
python3 -c "import pymupdf4llm; print('ok', pymupdf4llm.__version__)" 2>&1 || echo "(missing — only needed for download-ref)"
```

Report a short status table to the user before proposing actions, e.g.:

```
zlp-cli            ✓ installed (1.4.0)
ZULIP_WORKSPACE    ✗ unset
zuliprc            ✗ missing at <default workspace>/zuliprc
pymupdf4llm        ✗ missing (optional — only for adding new refs)

I'll walk you through the missing bits. Sound good? (yes / skip-pymupdf / cancel)
```

If everything is ✓ and `make zulip-whoami` returns successfully, the onboarding is already done — skip to Step 4.

### Step 2 — Install `zlp-cli` (if missing)

```sh
pip install zlp-cli
```

If `pip` reports PEP 668 / "externally-managed-environment" errors on macOS Homebrew Python, use:

```sh
pip install --user --break-system-packages zlp-cli
```

Verify: `zlp --version` exits 0.

### Step 3 — Get the Zulip API key

This step is **manual on the user's side** — no script can do it. Walk them through, substituting `$CFG_ZULIP_SITE` for the harness's actual site:

1. Open `$CFG_ZULIP_SITE` in a browser, log in.
2. Click their avatar → **Personal settings** → **Account & privacy**.
3. Find the **API key** row → click **Show/change your API key**.
4. Click **Download zuliprc** — they get a `zuliprc` text file.

The file looks like:

```
[api]
email=<their-email>
key=<32-char-key>
site=<$CFG_ZULIP_SITE>
```

**Do NOT** ask the user to paste the contents into chat. Keys are secrets.

### Step 4 — Place `zuliprc` AND export `ZULIP_WORKSPACE`

The default workspace location is `$CFG_ZULIP_WORKSPACE_DEFAULT`. Create the dir, move the file, set permissions:

```sh
mkdir -p "$CFG_ZULIP_WORKSPACE_DEFAULT"
mv ~/Downloads/zuliprc "$CFG_ZULIP_WORKSPACE_DEFAULT/zuliprc"
chmod 600 "$CFG_ZULIP_WORKSPACE_DEFAULT/zuliprc"   # contains an API key
```

Then **persist `ZULIP_WORKSPACE` in the user's shell rc** — most harness Makefiles enforce that the var is set:

```sh
echo "export ZULIP_WORKSPACE=\"$CFG_ZULIP_WORKSPACE_DEFAULT\"" >> ~/.zshrc
# or ~/.bashrc, depending on their shell
source ~/.zshrc
```

If they prefer to pass it inline each time:

```sh
make zulip-whoami ZULIP_WORKSPACE="$CFG_ZULIP_WORKSPACE_DEFAULT"
```

Inline works but is annoying — the rc-file export is the right answer.

If the user already had a `ZULIP_WORKSPACE` for a *different* harness (e.g. another Zulip workspace on a different site), they'll need either separate workspace dirs (`~/zulip-workspaces/hkust-gz/`, `~/zulip-workspaces/quantum-info/`, etc.) and switch `ZULIP_WORKSPACE` per-shell, or symlink the right one in. The Makefile is opinionated — one workspace per shell environment.

### Step 5 — Verify the bridge

From the repo root:

```sh
make zulip-whoami
```

Expected output (their email and display name will differ):

```
zlp whoami
<$CFG_ZULIP_SITE> <their-email> <Display Name>
```

If you see `*** ZULIP_WORKSPACE is not set ...`, the env var didn't propagate — they probably ran `export` in a different shell. Have them open a fresh terminal or `source ~/.zshrc`.

Then a quick sanity check that the stream is reachable:

```sh
make zulip-topics
```

Should list topics in `$CFG_ZULIP_STREAM`. If the stream has no topics yet, the listing is empty — that's not an error.

### Step 6 — (Optional) `pymupdf4llm` for adding references

Only needed if they'll use the `download-ref` skill to add new arXiv/DOI papers to `.knowledge/`. Reading the existing library doesn't need it.

```sh
# Check which python3 the renderer will use:
which python3

# Install for that interpreter (macOS Homebrew needs the break flag):
python3 -m pip install --user --break-system-packages pymupdf4llm
# Linux / system python:
python3 -m pip install --user pymupdf4llm

# Verify:
python3 -c "import pymupdf4llm; print(pymupdf4llm.__version__)"
```

The `download-ref` skill's Preflight section has the same check; this step just front-loads it.

### Step 7 — Backfill the local Zulip archive (recommended)

```sh
make zulip-pull IMPORT_HISTORY=1
```

This pulls every message in `$CFG_ZULIP_STREAM` into `.zulip/` (gitignored). After this runs once, daily catch-up is just `make zulip-pull`.

## Done checklist

- [ ] `zlp` is on `$PATH`
- [ ] `ZULIP_WORKSPACE` exported in the user's shell rc (not just the current terminal)
- [ ] `zuliprc` exists at `$ZULIP_WORKSPACE/zuliprc` with mode 600
- [ ] `make zulip-whoami` returns the user's email + display name without an env-var error
- [ ] `make zulip-topics` lists topics in `$CFG_ZULIP_STREAM` (empty list is fine for a brand-new stream)
- [ ] `.zulip/` populated by `make zulip-pull IMPORT_HISTORY=1`
- [ ] (Optional) `pymupdf4llm` importable by `python3`

After this, the user should:
- Read `CLAUDE.md` for repo conventions.
- Browse `.knowledge/INDEX.md` to see the reference library.

## Common mistakes

| Mistake | Fix |
| --- | --- |
| Hardcoding "hkust-gz" or any other workspace into the prompts you show the user | All site/path values come from `make zulip-config`. Re-read Step 0; do not paste site URLs from memory. |
| Running this skill from outside a harness directory | `make zulip-config` only exists inside a harness root. cd into the repo first. |
| `make` says `ZULIP_WORKSPACE is not set` even though they `export`ed it | They exported in a different shell. Append to `~/.zshrc` and `source` it (or open a fresh terminal). |
| Pasting the zuliprc contents into chat | Don't. Keys are secrets. Have the user `mv` the downloaded file locally. |
| Installing pymupdf4llm into Anaconda Python when `python3` resolves to `/opt/homebrew/bin/python3` | Run `which python3` first, then install for *that* interpreter. The renderer runs `python3` directly, not `conda run python`. |
| Putting `zuliprc` at `~/zulip-workspaces/zuliprc` (no workspace-label subdir) | The Makefile expects a workspace *directory*, not a flat file. The path is `<workspace>/zuliprc`. |
| Forgetting `chmod 600 zuliprc` | The key is in plain text. World-readable mode bits leak it to anyone with shell access. |
| Treating `make zulip-pull` `archived=0` as a failure | It just means no new messages since the last pull. Not an error. |
