---
name: onboard
description: Use when a new collaborator on this harness repo needs to bootstrap their machine — checks what's already installed, walks them through getting an hkust-gz Zulip API key, sets up the workspace path, and verifies the bridge works. Triggers on "I just cloned this", "first time setup", "onboard me", "help me get started", "set up zulip", "/onboard".
---

# onboard

## When to use

- The user just cloned this harness repo and is running it for the first time.
- `make zulip-whoami` fails with "zuliprc not found" or "command not found: zlp".
- The user explicitly asks for setup help: "onboard me", "help me get started", "set up zulip", etc.

Do NOT use:
- For an *existing* setup that's hit a temporary error — that's a bug to debug, not onboarding. Look at the error first.
- For onboarding to an unrelated project on a different Zulip workspace — this skill assumes the hkust-gz workspace + the stream named in this repo's `Makefile`.

## Inputs

The skill is interactive — it detects state and asks for what's missing. No required arguments.

## Workflow

### Step 0 — Detect what's already done

Before asking anything, check the four prerequisites in parallel:

```sh
echo "=== zlp-cli installed? ==="
command -v zlp && echo "installed ($(zlp whoami 2>/dev/null | head -1 || echo 'cli found'))" || echo "(missing)"

echo "=== zuliprc present? ==="
ls -la "${ZULIP_WORKSPACE:-$HOME/zulip-workspaces/hkust-gz}/zuliprc" 2>&1 || echo "(missing)"

echo "=== ZULIP_WORKSPACE override set? ==="
echo "ZULIP_WORKSPACE=${ZULIP_WORKSPACE:-(unset, defaulting to \$HOME/zulip-workspaces/hkust-gz)}"

echo "=== pymupdf4llm available to /usr/bin/env python3? ==="
python3 -c "import pymupdf4llm; print('ok', pymupdf4llm.__version__)" 2>&1 || echo "(missing — only needed for download-ref)"
```

Report a short status table to the user before proposing actions, e.g.:

```
zlp-cli       ✓ installed (1.4.0)
zuliprc       ✗ missing at ~/zulip-workspaces/hkust-gz/zuliprc
ZULIP_WORKSPACE  using default
pymupdf4llm   ✗ missing (optional — only for adding new refs)

I'll walk you through the missing bits. Sound good? (yes / skip-pymupdf / cancel)
```

If everything is ✓ and `make zulip-whoami` returns successfully, the onboarding is already done — skip to Step 4.

### Step 1 — Install `zlp-cli` (if missing)

```sh
pip install zlp-cli
```

If `pip` reports PEP 668 / "externally-managed-environment" errors on macOS Homebrew Python, use:

```sh
pip install --user --break-system-packages zlp-cli
```

Verify: `zlp --version` exits 0.

### Step 2 — Get the hkust-gz Zulip API key

This step is **manual on the user's side** — no script can do it. Walk them through:

1. Open <https://zulip.hkust-gz.edu.cn> in a browser, log in.
2. Click their avatar → **Personal settings** → **Account & privacy**.
3. Find the **API key** row → click **Show/change your API key**.
4. Click **Download zuliprc** — they get a `zuliprc` text file.

The file looks like:

```
[api]
email=<their-email>@zulip.hkust-gz.edu.cn
key=<32-char-key>
site=https://zulip.hkust-gz.edu.cn
```

**Do NOT** ask the user to paste the contents into chat. Keys are secrets.

### Step 3 — Place `zuliprc` at the workspace path

Default location is `~/zulip-workspaces/hkust-gz/zuliprc`. Create the dir and move the downloaded file:

```sh
mkdir -p ~/zulip-workspaces/hkust-gz
mv ~/Downloads/zuliprc ~/zulip-workspaces/hkust-gz/zuliprc
chmod 600 ~/zulip-workspaces/hkust-gz/zuliprc   # contains an API key
```

If the user prefers a different directory, have them set `ZULIP_WORKSPACE` in their shell rc:

```sh
echo 'export ZULIP_WORKSPACE=/path/to/their/dir' >> ~/.zshrc   # or ~/.bashrc
```

### Step 4 — Verify the bridge

From the repo root:

```sh
make zulip-whoami
```

Expected output (their email and display name will differ):

```
zlp whoami
https://zulip.hkust-gz.edu.cn <their-email> <Display Name>
```

Then a quick sanity check that the stream is reachable:

```sh
make zulip-topics
```

Should list whatever topics the harness's Zulip stream contains. If the stream has no topics yet, the listing is empty — that's not an error, just means no one has posted.

### Step 5 — (Optional) `pymupdf4llm` for adding references

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

### Step 6 — Backfill the local Zulip archive (recommended)

```sh
make zulip-pull IMPORT_HISTORY=1
```

This pulls every message in the harness's Zulip stream (the `ZULIP_STREAM` value in the repo's `Makefile`) into `.zulip/` (gitignored). After this runs once, daily catch-up is just `make zulip-pull`.

## Done checklist

- [ ] `zlp` is on `$PATH`
- [ ] `zuliprc` exists at `$ZULIP_WORKSPACE/zuliprc` (default `~/zulip-workspaces/hkust-gz/zuliprc`) with mode 600
- [ ] `make zulip-whoami` returns the user's email + display name
- [ ] `make zulip-topics` returns without error (empty list is fine for a brand-new stream)
- [ ] `.zulip/` populated by `make zulip-pull IMPORT_HISTORY=1`
- [ ] (Optional) `pymupdf4llm` importable by `python3`

After this, the user should:
- Read `CLAUDE.md` for repo conventions.
- Read `.knowledge/PROJECT_NOTES.md` for the current research context.
- Browse `.knowledge/INDEX.md` to see the reference library.

## Common mistakes

| Mistake | Fix |
| --- | --- |
| Pasting the zuliprc contents into chat | Don't. Keys are secrets. Have the user `mv` the downloaded file locally. |
| Installing pymupdf4llm into Anaconda Python when `python3` resolves to `/opt/homebrew/bin/python3` | Run `which python3` first, then install for *that* interpreter. The renderer runs `python3` directly, not `conda run python`. |
| Setting `ZULIP_WORKSPACE` only for the current shell | Append to `~/.zshrc` / `~/.bashrc`, not just `export` in one terminal. |
| Putting `zuliprc` at `~/zulip-workspaces/zuliprc` (no `hkust-gz/`) | The Makefile expects a workspace *directory*, not a flat file. The path is `<workspace>/zuliprc`. |
| Forgetting `chmod 600 zuliprc` | The key is in plain text. World-readable mode bits leak it to anyone with shell access. |
| Treating `make zulip-pull` `archived=0` as a failure | It just means no new messages since the last pull. Not an error. |
