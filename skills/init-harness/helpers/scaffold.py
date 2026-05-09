#!/usr/bin/env python3
"""Scaffold a new <topic>.harness repo from the bundled templates.

Reads everything from <skill-dir>/templates/. No external dependencies.
Idempotent-ish: refuses to overwrite a non-empty target unless --force.

Substitutions performed in *.tmpl files (and in the bundled project-level
onboard SKILL.md):
  <<TOPIC>>            → --topic
  <<ZULIP_STREAM>>     → --zulip-stream
  <<ZULIP_SITE>>       → --zulip-site (default https://zulip.hkust-gz.edu.cn)
  <<WORKSPACE>>        → --workspace (default derived from --zulip-site host;
                        Zulip's term for an org/server)
  <<GITHUB_REMOTE>>    → --github-remote (or "<org>/<repo>" placeholder if empty)
  <<TOPIC_BLURB>>      → --topic-blurb (or a TODO marker if empty)

Files copied verbatim (no substitution): AGENTS.md, .gitignore.

The thin project-level `onboard` skill at templates/skills/onboard/SKILL.md
is copied into <target>/.claude/skills/onboard/SKILL.md with substitution.
The plugin's `zlp-onboard`, `zulip-reply`, and `download-ref` skills are
NOT bundled per-repo — they come from the zlp-harness plugin once it's
enabled in the user's ~/.claude/settings.json (the bundled `onboard`
skill does that on first run).
"""
from __future__ import annotations
import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATES = SKILL_DIR / "templates"

# (template-relative path, target-relative path, substitute?)
RENDER_PLAN: list[tuple[str, str, bool]] = [
    ("Makefile.tmpl",         "Makefile",         True),
    ("CLAUDE.md.tmpl",        "CLAUDE.md",        True),
    ("README.md.tmpl",        "README.md",        True),
    ("AGENTS.md",             "AGENTS.md",        False),
    ("gitignore.tmpl",        ".gitignore",       False),
    ("knowledge/INDEX.md",    ".knowledge/INDEX.md", True),
]

# Project-level skills bundled into each new harness. zlp-onboard,
# download-ref, and zulip-reply are NOT here — they live in the
# zlp-harness plugin and are wired up by the bundled onboard skill.
SUBSKILLS: list[str] = ["onboard"]


def derive_workspace(zulip_site: str) -> str:
    """Take the leftmost host label as the workspace name.

    Examples:
      https://zulip.hkust-gz.edu.cn          → hkust-gz
      https://quantum-info.zulipchat.com     → quantum-info
      https://chat.zulip.org                 → chat
    """
    host = urlparse(zulip_site).hostname or ""
    if not host:
        raise SystemExit(f"error: cannot derive workspace from {zulip_site!r}; "
                         "pass --workspace explicitly.")
    parts = host.split(".")
    # If first label is generic ("zulip", "chat"), use the second.
    if parts[0] in {"zulip", "chat"} and len(parts) > 1:
        return parts[1]
    return parts[0]


def substitute(text: str, *, topic: str, zulip_stream: str, zulip_site: str,
               workspace: str, github_remote: str, topic_blurb: str) -> str:
    blurb = topic_blurb.strip() or (
        f"<!-- TODO: one paragraph describing what the {topic} harness is "
        f"about. Replace this placeholder. -->"
    )
    remote = github_remote.strip() or "<org>/<repo>"
    return (text
            .replace("<<TOPIC>>", topic)
            .replace("<<ZULIP_STREAM>>", zulip_stream)
            .replace("<<ZULIP_SITE>>", zulip_site)
            .replace("<<WORKSPACE>>", workspace)
            .replace("<<GITHUB_REMOTE>>", remote)
            .replace("<<TOPIC_BLURB>>", blurb))


def copy_with_substitution(src: Path, dst: Path, *, do_subst: bool, **subs) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    raw = src.read_text(encoding="utf-8")
    out = substitute(raw, **subs) if do_subst else raw
    dst.write_text(out, encoding="utf-8")


def copy_subskill(name: str, target_root: Path, **subs) -> None:
    src_root = TEMPLATES / "skills" / name
    dst_root = target_root / ".claude" / "skills" / name
    if not src_root.is_dir():
        raise SystemExit(f"missing bundled sub-skill: {src_root}")
    for src in src_root.rglob("*"):
        if src.is_dir() or "__pycache__" in src.parts:
            continue
        rel = src.relative_to(src_root)
        dst = dst_root / rel
        if src.suffix == ".md":
            copy_with_substitution(src, dst, do_subst=True, **subs)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)


def is_dir_effectively_empty(p: Path) -> bool:
    if not p.exists():
        return True
    if not p.is_dir():
        return False
    return not any(p.iterdir())


def preflight_templates() -> list[str]:
    """Return list of missing required template files (empty = OK)."""
    required = [t for (t, _, _) in RENDER_PLAN]
    required += [f"skills/{s}/SKILL.md" for s in SUBSKILLS]
    return [r for r in required if not (TEMPLATES / r).exists()]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--topic", required=True,
                    help="lowercase, hyphenated slug (e.g. 'qec', 'attention-solids')")
    ap.add_argument("--target-dir", required=True,
                    help="where to scaffold the new harness; must be empty or non-existent")
    ap.add_argument("--zulip-stream", default=None,
                    help="stream name on the Zulip server (default: project-<topic>)")
    ap.add_argument("--zulip-site", default="https://zulip.hkust-gz.edu.cn",
                    help="Zulip server URL (default: https://zulip.hkust-gz.edu.cn). "
                         "Examples: https://quantum-info.zulipchat.com, https://chat.zulip.org")
    ap.add_argument("--workspace", default=None,
                    help="Zulip workspace slug — names the global workspace directory at "
                         "~/.local/share/zlp-harness/<workspace>/ that holds zuliprc, archived "
                         "messages, cursor state, and drafts. Default: derived from --zulip-site "
                         "host (e.g. 'hkust-gz', 'quantum-info').")
    ap.add_argument("--github-remote", default="",
                    help="<org>/<repo> for the README clone link (e.g. CodingThrust/qec.harness); "
                         "empty leaves a placeholder")
    ap.add_argument("--topic-blurb", default="",
                    help="one paragraph describing the harness purpose; empty leaves a TODO")
    ap.add_argument("--git-init", action="store_true",
                    help="run `git init` and a single seed commit in the target")
    ap.add_argument("--force", action="store_true",
                    help="allow scaffolding into a non-empty directory (DANGEROUS)")
    args = ap.parse_args()

    topic = args.topic.strip()
    if not topic or any(c.isupper() or c.isspace() for c in topic):
        print(f"error: --topic must be lowercase, hyphenated, no spaces (got {topic!r})",
              file=sys.stderr)
        return 2

    zulip_stream = args.zulip_stream or f"project-{topic}"
    zulip_site = args.zulip_site.rstrip("/")
    workspace = args.workspace or derive_workspace(zulip_site)
    target = Path(args.target_dir).expanduser().resolve()

    missing = preflight_templates()
    if missing:
        print("error: skill is incomplete — missing template files:", file=sys.stderr)
        for m in missing:
            print(f"  - {TEMPLATES / m}", file=sys.stderr)
        return 3

    if not args.force and not is_dir_effectively_empty(target):
        print(f"error: {target} exists and is not empty. "
              "Pass --force to scaffold into it anyway (this can clobber files).",
              file=sys.stderr)
        return 4

    target.mkdir(parents=True, exist_ok=True)

    subs = dict(
        topic=topic,
        zulip_stream=zulip_stream,
        zulip_site=zulip_site,
        workspace=workspace,
        github_remote=args.github_remote.strip(),
        topic_blurb=args.topic_blurb,
    )

    written: list[Path] = []
    for src_rel, dst_rel, do_subst in RENDER_PLAN:
        src, dst = TEMPLATES / src_rel, target / dst_rel
        copy_with_substitution(src, dst, do_subst=do_subst, **subs)
        written.append(dst)

    for s in SUBSKILLS:
        copy_subskill(s, target, **subs)
        written.append(target / ".claude" / "skills" / s)

    print(f"scaffolded {target}")
    print(f"  topic            = {topic}")
    print(f"  zulip-stream     = {zulip_stream}")
    print(f"  zulip-site       = {zulip_site}")
    print(f"  workspace        = {workspace}")
    print(f"  github-remote    = {args.github_remote or '(none — leave placeholder)'}")
    print("  files written:")
    for w in written:
        print(f"    {w.relative_to(target)}")

    if args.git_init:
        try:
            subprocess.run(["git", "init", "--quiet"], cwd=target, check=True)
            subprocess.run(["git", "add", "."], cwd=target, check=True)
            subprocess.run(
                ["git", "commit", "--quiet", "-m",
                 f"scaffold {topic}.harness from init-harness skill"],
                cwd=target, check=True,
            )
            print("git: initialized + seed commit")
        except subprocess.CalledProcessError as e:
            print(f"warning: git step failed: {e}", file=sys.stderr)

    print()
    print("next steps for the user:")
    print(f"  1. cd {target}")
    print( "  2. Edit CLAUDE.md — fill in 'Repository purpose' and any linked external repos.")
    if args.github_remote:
        print(f"  3. (optional) gh repo create {args.github_remote} --private --source=. --push")
    print( "  4. Open in Claude Code and run /onboard to enable the zlp-harness plugin and set up Zulip.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
