---
name: zlp-onboard
description: Use when a new collaborator on any zlp-harness-based repo needs to bootstrap their machine — checks what's already installed, walks them through getting a Zulip API key for the harness's site, creates the global zlp-harness workspace directory, places `zuliprc` there, and verifies the bridge works. Triggers on "I just cloned this", "first time setup", "onboard me", "help me get started", "set up zulip", "/zlp-onboard", or when invoked by a harness's project-level onboard skill.
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

Every site/path/stream value below is read from the harness's Makefile via `make zulip-config`. Resolve `HELPERS` to this skill's bundled `helpers/` directory, then run the parser once at the start of the skill and use the resulting `CFG_*` env vars throughout.

```sh
HELPERS="<path-to-this-skill's-directory>/helpers"

# Load harness config from the Makefile. The helper parses the KEY=VALUE
# contract strictly and emits shell-safe CFG_* assignments.
eval "$(python3 "$HELPERS/read_zulip_config.py" --format shell)"

# Should now have:
#   $CFG_ZULIP_SITE                  e.g. https://quantum-info.zulipchat.com
#   $CFG_ZULIP_STREAM                e.g. LLM项目推进
#   $CFG_ZULIP_WORKSPACE             e.g. quantum-info
#   $CFG_ZULIP_WORKSPACE_DIR_DEFAULT e.g. <workspace-dir>
#   $CFG_ZULIP_DRAFTS_DIR            e.g. <workspace-dir>/.drafts

echo "site:          $CFG_ZULIP_SITE"
echo "stream:        $CFG_ZULIP_STREAM"
echo "workspace:     $CFG_ZULIP_WORKSPACE"
echo "workspace dir: $CFG_ZULIP_WORKSPACE_DIR_DEFAULT"
```

If `make zulip-config` doesn't exist or returns nothing, the harness is on an older Makefile that predates the contract. Tell the user to update the Makefile by hand following the zlp-harness CLAUDE.md.

### Step 1 — Detect what's already done

Before asking anything, check the four prerequisites in parallel:

```sh
echo "=== zlp-cli installed? ==="
command -v zlp && (zlp whoami 2>/dev/null | head -1 || echo "(cli found)") || echo "(missing)"

echo "=== workspace directory ==="
WS_DIR="${ZULIP_WORKSPACE_DIR:-$CFG_ZULIP_WORKSPACE_DIR_DEFAULT}"
echo "$WS_DIR"

echo "=== zuliprc present? ==="
ls -la "$WS_DIR/zuliprc" 2>&1 || echo "(missing at $WS_DIR/zuliprc)"

echo "=== pymupdf4llm available to python3? ==="
python3 -c "import pymupdf4llm; print('ok', pymupdf4llm.__version__)" 2>&1 || echo "(missing — only needed for download-ref)"
```

Report a short status table to the user before proposing actions, e.g.:

```
zlp-cli              ✓ installed (1.4.0)
workspace directory  <workspace-dir> (will be created)
zuliprc              ✗ missing at <workspace-dir>/zuliprc
pymupdf4llm          ✗ missing (optional — only for adding new refs)

I'll walk you through the missing bits. Sound good? (yes / skip-pymupdf / cancel)
```

If everything is ✓ and `make zulip-whoami` returns successfully, the onboarding is already done — skip to Step 4.

### Step 2 — Install `zlp-cli` (if missing)

```sh
pip install zlp-cli
```

If `pip` reports a PEP 668 / "externally-managed-environment" error, use:

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

Hint for the user: the downloaded file is usually named `zuliprc`. Some browsers rename it to `zuliprc.txt` or `zuliprc (1)` if a file already exists. If they are not sure where it went, have them look in the browser's downloads list.

The file looks like:

```
[api]
email=<their-email>
key=<32-char-key>
site=<$CFG_ZULIP_SITE>
```

**Do NOT** ask the user to paste the contents into chat. Keys are secrets.

### Step 4 — Create the workspace directory and place `zuliprc`

There is no pre-existing workspace directory on a fresh collaborator machine. Create the global workspace dir for this Zulip server and put the downloaded `zuliprc` there. The harness Makefile points `zlp` at that file via `ZULIP_CONFIG_FILE` and at the same dir for the message archive via `ZLP_ARCHIVE_ROOT`.

```sh
mkdir -p "$CFG_ZULIP_WORKSPACE_DIR_DEFAULT"
ZULIPRC_SOURCE="<path-to-downloaded-zuliprc>"
mv "$ZULIPRC_SOURCE" "$CFG_ZULIP_WORKSPACE_DIR_DEFAULT/zuliprc"
chmod 600 "$CFG_ZULIP_WORKSPACE_DIR_DEFAULT/zuliprc"   # contains an API key
```

Replace `<path-to-downloaded-zuliprc>` with the actual downloaded path. Do not open or print the file contents. If `chmod` is unavailable on the user's platform, use the platform's normal file-permission tool to restrict the file to the current user.

If the user wants to keep the workspace somewhere else, set `ZULIP_WORKSPACE_DIR` for that custom location:

```sh
# Add this export to the user's shell startup file, then open a fresh shell:
export ZULIP_WORKSPACE_DIR="/path/to/their/zulip-workspace"
```

or pass it inline for a single command:

```sh
make zulip-whoami ZULIP_WORKSPACE_DIR="/path/to/their/zulip-workspace"
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
# Print the python3 interpreter the renderer will use:
python3 -c "import sys; print(sys.executable)"

# Install for that interpreter:
python3 -m pip install --user pymupdf4llm
# If pip reports an externally-managed-environment / PEP 668 error:
python3 -m pip install --user --break-system-packages pymupdf4llm

# Verify:
python3 -c "import pymupdf4llm; print(pymupdf4llm.__version__)"
```

The `download-ref` skill's Preflight section has the same check; this step just front-loads it.

### Step 7 — Sync the workspace archive

```sh
make zulip-pull IMPORT_HISTORY=1
find "$CFG_ZULIP_WORKSPACE_DIR_DEFAULT" -path '*/.*' -prune -o -name '*.md' -print -quit 2>/dev/null
```

This pulls the available history in `$CFG_ZULIP_STREAM` into the workspace dir (`$CFG_ZULIP_WORKSPACE_DIR_DEFAULT`). Do not treat onboarding as complete until `make zulip-pull IMPORT_HISTORY=1` exits successfully.

If `find` prints a path, the archive has local message files. If it prints nothing, check the command output: a brand-new or empty stream can sync successfully with no message files. In that case, tell the user the stream is reachable but currently has no archived messages. After this first sync, daily catch-up is just `make zulip-pull`.

### Step 8 — Recommend key reference downloads

Before ending onboarding, recommend that the user populate `.knowledge/` with the project’s key references:

```
Zulip is synced. Next, it is worth downloading the project’s core arXiv/DOI references into `.knowledge/` with the `download-ref` skill, so future Zulip replies and research questions are grounded in the local library. Send me the key arXiv IDs/DOIs, or ask me to identify likely key refs from the synced Zulip discussion and existing project notes.
```

If the user provides arXiv IDs or DOIs, invoke `download-ref` next. If they want help identifying key references, inspect `.zulip/`, `CLAUDE.md`, and `.knowledge/INDEX.md` first, then propose a short candidate list before downloading.

### Step 9 — Configure reliable update sources for `zlp-advisor`

Before ending onboarding, help the user define where weekly "latest update" searches should look. This belongs in the harness's `CLAUDE.md`, so future `zlp-advisor` runs use project-specific sources instead of guessing.

First inspect local context:

```sh
rg -n "Repository purpose|Reliable update sources|Knowledge base|Weekly advisor|Zulip channel" CLAUDE.md
test -f .knowledge/INDEX.md && sed -n '1,120p' .knowledge/INDEX.md
find "$CFG_ZULIP_WORKSPACE_DIR_DEFAULT" -path '*/.*' -prune -o -name '*.md' -print -quit 2>/dev/null
```

Then propose a compact pick-list. Include:

- **Source types**: `arXiv`, `web search`, and `other reliable sources`.
- **Keywords**: 6-10 project-specific phrases from `CLAUDE.md`, `.knowledge/INDEX.md`, and recent Zulip discussions in the workspace archive.
- **Big names to watch**: 3-8 prominent authors, labs, venues, benchmarks, datasets, or methods. Prefer names already evidenced in `.knowledge/` or Zulip. If evidence is thin, label them as provisional suggestions and ask the user to correct them.
- **Other reliable sources**: official conference/workshop pages, benchmark/dataset leaderboards, standards/docs, project release notes, publisher pages, or lab pages relevant to this project.

Ask the user to choose and edit. Example prompt:

```md
For weekly advisor updates, which reliable sources should I track?

Source types:
- arXiv search
- web search over reliable/official sources
- other reliable sources you name

Candidate keywords:
- <keyword 1>
- <keyword 2>
- <keyword 3>

Candidate big names / venues / benchmarks:
- <name 1> — why it appears relevant
- <name 2> — why it appears relevant

Other reliable sources to include:
- <official site, benchmark, conference, lab page, docs, or release page>
```

After the user chooses, add or update this section in `CLAUDE.md`:

```md
## Reliable update sources (`zlp-advisor`)

Use these sources when looking for current external updates during weekly advisor checks.

- Source types: arXiv, web search, other reliable sources
- arXiv queries / categories:
  - <query or category>
- Web-search keywords:
  - <keyword>
- People / groups / venues / benchmarks to watch:
  - <name> — <why relevant>
- Other reliable sources:
  - <URL or source name> — <why reliable/relevant>
- Avoid:
  - unsourced social posts, SEO blogs, and generic news summaries unless the user explicitly asks
```

Do not invent authority. If the user does not know yet, write a short provisional section with TODO markers and tell them `zlp-advisor` will ask again before relying on weak sources.

## Done checklist

- [ ] `zlp` is on `$PATH`
- [ ] Workspace directory was created by onboarding, or `ZULIP_WORKSPACE_DIR` intentionally points at a custom one
- [ ] `zuliprc` exists at `<workspace-dir>/zuliprc` with mode 600
- [ ] `make zulip-whoami` returns the user's email + display name
- [ ] `make zulip-topics` lists topics in `$CFG_ZULIP_STREAM` (empty list is fine for a brand-new stream)
- [ ] `make zulip-pull IMPORT_HISTORY=1` completed; the workspace dir has messages, or the user was told the stream currently has none
- [ ] User was advised to download key project references with `download-ref`
- [ ] `CLAUDE.md` has a `Reliable update sources (zlp-advisor)` section, or the user intentionally deferred it
- [ ] (Optional) `pymupdf4llm` importable by `python3`

After this, the user should:
- Read `CLAUDE.md` for repo conventions.
- Browse `.knowledge/INDEX.md` to see the reference library.

## Common mistakes

| Mistake | Fix |
| --- | --- |
| Assuming a workspace directory already exists | Wrong model. A fresh collaborator has no such directory; create the workspace directory during onboarding. |
| Hardcoding "hkust-gz" or any other site label into the prompts you show the user | All site/path values come from `make zulip-config`. Re-read Step 0; do not paste site URLs from memory. |
| Running this skill from outside a harness directory | `make zulip-config` only exists inside a harness root. cd into the repo first. |
| Pasting the zuliprc contents into chat | Don't. Keys are secrets. Have the user `mv` the downloaded file locally. |
| Installing pymupdf4llm into a different Python environment than `python3` uses | Run `python3 -c "import sys; print(sys.executable)"` first, then install for *that* interpreter. The renderer runs `python3` directly. |
| Putting `zuliprc` directly under the repo | Keep secrets out of the checkout. Put it in the workspace directory printed by `make zulip-config`. |
| Forgetting `chmod 600 zuliprc` | The key is in plain text. World-readable mode bits leak it to anyone with shell access. |
| Treating `make zulip-pull` `archived=0` as a failure | It just means no new messages since the last pull. Not an error. |
| Looking for messages under `<repo>/.zulip/` | That layout is gone. Messages live at `$CFG_ZULIP_WORKSPACE_DIR_DEFAULT/<channel-slug>/...`. |
