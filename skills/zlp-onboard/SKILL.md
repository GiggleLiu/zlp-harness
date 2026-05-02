---
name: zlp-onboard
description: Use when a new collaborator on any zlp-harness-based repo needs to bootstrap their machine — checks what's already installed, walks them through getting a Zulip API key for the harness's site (read from `make zulip-config`), creates the local credential directory for `zuliprc`, and verifies the bridge works. Triggers on "I just cloned this", "first time setup", "onboard me", "help me get started", "set up zulip", "/zlp-onboard", or when invoked by a harness's project-level onboard skill via `Skill("zlp-harness:zlp-onboard")`.
---

# zlp-onboard

## When to use

- A collaborator on a harness repo (LLM, qec, attention-solids, etc.) just cloned and is running it for the first time.
- `make zulip-whoami` fails with "zuliprc not found" or "command not found: zlp".
- The harness's project-level `onboard` skill invokes this one after enabling the plugin.

Do NOT use:
- For an *existing* setup hitting a temporary error — that's a bug to debug, not onboarding. Look at the error first.
- Outside a zlp-harness-style repo. The skill assumes the cwd has a `Makefile` exposing the `make zulip-config` target plus the standard `make zulip-*` set.

## Inputs

The skill is interactive — it detects state and asks for what's missing. No required arguments.

## Workflow

### Step 0 — Read harness config

Every site/path/stream value below is read from the harness's Makefile via `make zulip-config`. Run this once at the start of the skill and use the resulting `CFG_*` env vars throughout.

```sh
# Load harness config from the Makefile. Single-quote each value
# so future stream names with whitespace or shell metacharacters parse safely.
eval "$(make zulip-config | sed 's/^\([^=]*\)=\(.*\)$/CFG_\1=\x27\2\x27/')"

# Should now have:
#   $CFG_ZULIP_SITE              e.g. https://quantum-info.zulipchat.com
#   $CFG_ZULIP_STREAM            e.g. LLM项目推进
#   $CFG_ZULIP_CONFIG_DIR_DEFAULT e.g. /Users/<you>/.config/zlp-harness/quantum-info

# Older harnesses may print CFG_ZULIP_WORKSPACE_DEFAULT. Treat it as a private
# credential directory for compatibility, but don't expose that name to users.
CFG_ZULIP_CONFIG_DIR_DEFAULT="${CFG_ZULIP_CONFIG_DIR_DEFAULT:-${CFG_ZULIP_WORKSPACE_DEFAULT:-}}"

echo "site:    $CFG_ZULIP_SITE"
echo "stream:  $CFG_ZULIP_STREAM"
echo "credential dir: $CFG_ZULIP_CONFIG_DIR_DEFAULT"
```

If `make zulip-config` doesn't exist or returns nothing, the harness is on an older Makefile that predates the contract. Tell the user to run the harness's project-level `onboard` skill first (which should add `zulip-config`), or to update the Makefile by hand following the zlp-harness CLAUDE.md.

### Step 1 — Detect what's already done

Before asking anything, check the four prerequisites in parallel:

```sh
echo "=== zlp-cli installed? ==="
command -v zlp && (zlp whoami 2>/dev/null | head -1 || echo "(cli found)") || echo "(missing)"

echo "=== credential directory ==="
CFG_DIR="${ZULIP_CONFIG_DIR:-$CFG_ZULIP_CONFIG_DIR_DEFAULT}"
echo "$CFG_DIR"

echo "=== zuliprc present? ==="
ls -la "$CFG_DIR/zuliprc" 2>&1 || echo "(missing at $CFG_DIR/zuliprc)"

echo "=== pymupdf4llm available to /usr/bin/env python3? ==="
python3 -c "import pymupdf4llm; print('ok', pymupdf4llm.__version__)" 2>&1 || echo "(missing — only needed for download-ref)"
```

Report a short status table to the user before proposing actions, e.g.:

```
zlp-cli              ✓ installed (1.4.0)
credential directory ~/.config/zlp-harness/<label> (will be created)
zuliprc              ✗ missing at <credential-dir>/zuliprc
pymupdf4llm          ✗ missing (optional — only for adding new refs)

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
2. Click their avatar or initials in the Zulip UI, then open **Personal settings**.
3. Go to **Account & privacy**.
4. Find **API key** and click **Show/change your API key**.
5. Click **Download zuliprc**.

Hint for the user: the downloaded file is usually named `zuliprc` and lands in `~/Downloads/`. Some browsers rename it to `zuliprc.txt` or `zuliprc (1)` if a file already exists. If they are not sure where it went, have them look in the browser's downloads list or run:

```sh
ls -lt ~/Downloads/zuliprc* 2>/dev/null | head
```

The file looks like:

```
[api]
email=<their-email>
key=<32-char-key>
site=<$CFG_ZULIP_SITE>
```

**Do NOT** ask the user to paste the contents into chat. Keys are secrets.

### Step 4 — Create the credential directory and place `zuliprc`

There is no pre-existing local Zulip directory on a fresh collaborator machine. Create a private credential directory for this harness and put the downloaded `zuliprc` there. The harness Makefile points `zlp` at that file via `ZULIP_CONFIG_FILE`.

```sh
mkdir -p "$CFG_ZULIP_CONFIG_DIR_DEFAULT"
mv ~/Downloads/zuliprc "$CFG_ZULIP_CONFIG_DIR_DEFAULT/zuliprc"
chmod 600 "$CFG_ZULIP_CONFIG_DIR_DEFAULT/zuliprc"   # contains an API key
```

If the browser used a different filename, replace `~/Downloads/zuliprc` with the actual downloaded path. Do not open or print the file contents.

If the user wants to keep the credentials somewhere else, then set `ZULIP_CONFIG_DIR` for that custom location:

```sh
echo 'export ZULIP_CONFIG_DIR="/path/to/their/zulip-credentials"' >> ~/.zshrc
source ~/.zshrc
```

or pass it inline for a single command:

```sh
make zulip-whoami ZULIP_CONFIG_DIR="/path/to/their/zulip-credentials"
```

Most collaborators should not set any override at all; the Makefile default is enough. The important point is that onboarding creates the directory and installs `zuliprc`; it must not assume anything already exists on disk.

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
- [ ] Credential directory was created by onboarding, or `ZULIP_CONFIG_DIR` intentionally points at a custom one
- [ ] `zuliprc` exists at `<credential-dir>/zuliprc` with mode 600
- [ ] `make zulip-whoami` returns the user's email + display name
- [ ] `make zulip-topics` lists topics in `$CFG_ZULIP_STREAM` (empty list is fine for a brand-new stream)
- [ ] `.zulip/` populated by `make zulip-pull IMPORT_HISTORY=1`
- [ ] (Optional) `pymupdf4llm` importable by `python3`

After this, the user should:
- Read `CLAUDE.md` for repo conventions.
- Browse `.knowledge/INDEX.md` to see the reference library.

## Common mistakes

| Mistake | Fix |
| --- | --- |
| Assuming a local Zulip directory already exists | Wrong model. A fresh collaborator has no such directory; create the credential directory during onboarding. |
| Hardcoding "hkust-gz" or any other site label into the prompts you show the user | All site/path values come from `make zulip-config`. Re-read Step 0; do not paste site URLs from memory. |
| Running this skill from outside a harness directory | `make zulip-config` only exists inside a harness root. cd into the repo first. |
| Pasting the zuliprc contents into chat | Don't. Keys are secrets. Have the user `mv` the downloaded file locally. |
| Installing pymupdf4llm into Anaconda Python when `python3` resolves to `/opt/homebrew/bin/python3` | Run `which python3` first, then install for *that* interpreter. The renderer runs `python3` directly, not `conda run python`. |
| Putting `zuliprc` directly under the repo | Keep secrets out of the checkout. Put it in the credential directory printed by `make zulip-config`. |
| Forgetting `chmod 600 zuliprc` | The key is in plain text. World-readable mode bits leak it to anyone with shell access. |
| Treating `make zulip-pull` `archived=0` as a failure | It just means no new messages since the last pull. Not an error. |
