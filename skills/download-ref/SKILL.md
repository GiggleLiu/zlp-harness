---
name: download-ref
description: Use when adding one or many new references (arXiv ID or DOI) to this project's `.knowledge/` library — fetches metadata via Semantic Scholar, downloads the arXiv preprint PDF, renders to markdown, and regenerates `INDEX.md`. Manifest is array-based; batches of 50+ refs work fine.
---

# download-ref

## When to use

- A discussion / draft surfaces a paper not yet in `.knowledge/`, and you want it indexed for future search.
- The user says "add this ref to the KB", "download arXiv:XXXX", "pull this DOI".
- Bulk-importing a reading list from issue threads / Zulip discussions / co-author messages — single manifest, single fetch, single render.

Do NOT use:
- For GitHub repos / web pages — those are too varied for a single-shot helper. Hand-clone or hand-curl, then run `render.py` with a manifest.

## Preflight (run once per machine)

The renderer uses **pymupdf4llm** for the highest-fidelity output (preserves figures). The fallback chain (`markitdown` → `pdftotext`) produces text-only markdown — *figures will silently be missing*. Verify before step 4:

```sh
python3 -c "import pymupdf4llm; print('ok', pymupdf4llm.__version__)"
```

If that errors, install for the **same** `python3` the helpers will use (typically `/opt/homebrew/bin/python3` on macOS, **not** Anaconda's):

```sh
# macOS / Homebrew Python
/opt/homebrew/bin/python3 -m pip install --user --break-system-packages pymupdf4llm

# Linux / system Python
python3 -m pip install --user pymupdf4llm
```

`--break-system-packages` is required on Homebrew Python (PEP 668) and is benign here.

Other helpers used: `requests` (almost always present), and optionally `markitdown` / `pdftotext` for fallback.

## Inputs

- **One or more arXiv IDs** (e.g. `1806.08734`, `2006.10739`) — strip the `vN` suffix.
- **One or more DOIs** (e.g. `10.1103/PhysRevLett.130.036401`) — lowercase preferred but renderer normalizes.
- KB path defaults to `<repo-root>/.knowledge`.

## Workflow

### 0. Resolve helper paths

The Python helpers live alongside this SKILL.md in `helpers/`. Resolve `HELPERS` to the absolute path of that directory (the directory containing this SKILL.md, plus `/helpers`). If the helpers are bundled in the project at `$HELPERS/`, use that instead.

```sh
KB=$(pwd)/.knowledge
HELPERS="<path-to-this-skill's-directory>/helpers"
```

### 1. Confirm the refs aren't already present

```sh
for id in 1806.08734 2006.10739; do
  [ -f "$KB/.raw/arxiv/$id.json" ] && echo "$id present" || echo "$id missing"
done
```

POSIX `[ -f … ]` is zsh-safe; `ls "$KB/.raw/arxiv/$id".*` triggers `no matches found` errors in zsh (extended_glob). The helpers themselves are also idempotent — re-running with an already-present id is a no-op — so this check is for human-readable status, not correctness gating.

### 2. Build a one-shot manifest

```sh
TMP=/tmp/download-ref-manifest.json
cat > "$TMP" <<'EOF'
{"arxiv": ["1806.08734", "2006.10739"], "doi": []}
EOF
```

For DOIs, drop them into the `doi` list verbatim. Both lists may be present.

### 3. Fetch metadata + arXiv PDFs

```sh
python3 $HELPERS/fetch_metadata.py \
  --kb "$KB" \
  --manifest "$TMP" \
  --download-arxiv-pdfs
```

This populates `$KB/.raw/{arxiv,doi}/<id>.{json,pdf}` idempotently — re-running won't re-fetch what's already there.

For DOIs whose publisher gates the PDF (APS / Nature / IOP / AAAS / ACS), the helper automatically falls back to the arXiv preprint via `externalIds.ArXiv` when present. If even that fails, you'll see a `miss` line in the output — proceed to step 3b.

### 3b. SciHub fallback for paywalled PDFs

If step 3 reports `miss` for any DOI (no open-access PDF and no arXiv preprint), use the `sci-hub-server` MCP tool to fetch the PDF. This requires the `sci-hub-server` MCP to be configured in Claude's settings (see below).

For each missing DOI:

1. Call the MCP tool `mcp__sci-hub-server__get_paper_link` with the DOI to get a direct PDF URL.
2. Call the MCP tool `mcp__sci-hub-server__download_pdf` with the URL and save to `$KB/.raw/doi/<safe>.pdf` (where `<safe>` = DOI with `/` → `-`).
3. Verify the file exists and is > 1 KB.

If the `sci-hub-server` MCP is not configured, tell the user to add it to their Claude settings:

```json
"mcpServers": {
  "sci-hub-server": {
    "command": "npx",
    "args": ["sci-mcp-server"]
  }
}
```

Skip this step if all PDFs were fetched in step 3.

### 4. Render to markdown

```sh
python3 $HELPERS/render.py \
  --kb "$KB"
```

No manifest is needed for arXiv/DOI — the renderer auto-discovers them from `$KB/.raw/`. Renders new entries, leaves existing ones in place.

PDF backend priority (first one that works wins):
1. **`pymupdf4llm`** (preferred) — produces markdown directly from the PDF and **also extracts embedded images**. Images are written to `$KB/.figures/arxiv__<id>/` (or `doi__<safe>/`); the rendered `<id>_<slug>.md` references them via relative `.figures/...` paths so the figures show up in any markdown viewer rooted at `$KB/`.
2. `markitdown` — text-only fallback for table-heavy PDFs.
3. `pdftotext -layout` — last-resort plain-text fallback.

Install pymupdf4llm with `pip install pymupdf4llm` (pulls in `pymupdf`). If you see `pymupdf4llm not installed; falling back ...` in stderr, the rendered `.md` is still fine but **figures will be missing** — install pymupdf4llm and re-render.

`$KB/.figures/` should stay out of git for the same reason as `.raw/` — add it to `.gitignore` if not already excluded.

### 5. Regenerate INDEX

```sh
python3 $HELPERS/index.py \
  --kb "$KB" \
  --title "<topic> — references" \
  --source-note "Reading list and full-text harness for the <topic> project. arXiv preprints, DOIs (with arXiv-preprint fallbacks where the publisher gates the PDF)."
```

Replace `<topic>` with this harness's slug (see `CLAUDE.md`'s "Repository purpose" section). **Once chosen, keep `--title` and `--source-note` byte-identical across runs** — `INDEX.md` is regenerated wholesale every time, and any drift here causes a noisy diff. The first run sets the canonical strings; copy them verbatim from `INDEX.md`'s top matter on every re-run.

### 6. Verify and report

```sh
# New md files appear at top level
ls -t "$KB"/*.md | head
# Frontmatter present
for f in "$KB"/*.md; do
  [ "$(basename "$f")" = INDEX.md ] && continue
  head -1 "$f" | grep -q '^---$' || echo "MISSING FRONTMATTER: $f"
done
# Raw blobs gitignored
git -C "$(dirname "$KB")" check-ignore .knowledge/.raw/ || echo "WARN: .raw/ not gitignored"
# INDEX picked up the new ids
for id in 1806.08734 2006.10739; do
  grep -q "$id" "$KB/INDEX.md" || echo "WARN: $id missing from INDEX.md"
done
```

Tell the user the new file names + the canonical IDs, and whether `full_text` came through (`yes`/`no`).

### 7. Append to `ref.bib` (interactive cite-key confirmation)

`ref.bib` lives at the repo root and is shared by `main.tex`, `report/*.tex`, `survey/*.tex`. After fetching, **propose** a cite key, **confirm with the user** via `AskUserQuestion`, then **append**.

#### 7a. Propose

For each new ref, run:

```sh
python3 $HELPERS/append_bibtex.py propose \
  --kb "$KB" --id 1806.08734 --type arxiv
```

Output is JSON with `proposed_key` (form `lastname_year_firstkeyword`, e.g. `rahaman_2018_spectral`) and `bibtex_with_proposed_key`. Show the user the proposed key together with the title and ask via `AskUserQuestion`:
- Accept the proposed key
- Use a custom key (offer a free-text alternative)
- Skip this entry (don't touch `ref.bib`)

#### 7b. Append

Once the user confirms a key:

```sh
python3 $HELPERS/append_bibtex.py append \
  --kb "$KB" --id 1806.08734 --type arxiv \
  --key rahaman_2018_spectral \
  --bib "$(dirname "$KB")/ref.bib"
```

The helper:
- Rewrites the BibTeX cite key to the confirmed value.
- Refuses to duplicate (greps for `@\w+\{<key>,` first; prints "skip: already present" if so).
- Appends the rewritten entry to `ref.bib` with one blank-line separator.

If the cite key already exists with different content, the helper still skips — investigate manually rather than letting it silently divert. Run the propose step again with a different proposed key, or fix the existing entry.

## Common mistakes

| Mistake | Fix |
| --- | --- |
| Running the helpers from the wrong CWD | They use `--kb` absolute paths, so CWD shouldn't matter — but always pass an **absolute** `$KB`. |
| Forgetting `--download-arxiv-pdfs` | Without it you get only metadata; the rendered `.md` will have `full_text: no`. |
| Re-running with a stale manifest | Helpers are idempotent — they skip entries whose `.raw/` already exists. Safe to re-run. |
| Editing the rendered `.md` by hand and losing it on re-render | The renderer overwrites without warning. Edit the `.raw/` source or the renderer logic if you need persistent changes. |
| Using `arXiv:XXXX` with the prefix or `vN` suffix | Strip both — manifest takes bare ids: `1806.08734`. |

## Done checklist

- [ ] `.raw/{arxiv,doi}/<id>.json` exists for every requested id
- [ ] `.raw/{arxiv,doi}/<id>.pdf` exists where the source allows (else recorded as paywalled)
- [ ] One new `<id>_<slug>.md` per ref at `$KB/` root, with frontmatter
- [ ] `$KB/INDEX.md` regenerated, lists the new entry under arXiv or DOI section
- [ ] User told the file names + whether `full_text` came through
