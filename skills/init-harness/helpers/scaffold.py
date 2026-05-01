#!/usr/bin/env python3
"""Scaffold a new <topic>.harness repo from the bundled templates.

Reads everything from <skill-dir>/templates/. No external dependencies.
Idempotent-ish: refuses to overwrite a non-empty target unless --force.

Substitutions performed in *.tmpl files (and in the bundled sub-skill
SKILL.md / Makefile.tmpl):
  <<TOPIC>>          → --topic
  <<ZULIP_STREAM>>   → --zulip-stream
  <<GITHUB_REMOTE>>  → --github-remote (or "<org>/<repo>" placeholder if empty)
  <<TOPIC_BLURB>>    → --topic-blurb (or a TODO marker if empty)

Files copied verbatim (no substitution): AGENTS.md, .gitignore,
all skills/download-ref/helpers/*.py.
"""
from __future__ import annotations
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

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

# Sub-skills are provided by the zlp-harness plugin (not bundled per-repo).
SUBSKILLS: list[str] = []


def substitute(text: str, *, topic: str, zulip_stream: str,
               github_remote: str, topic_blurb: str) -> str:
    blurb = topic_blurb.strip() or (
        f"<!-- TODO: one paragraph describing what the {topic} harness is "
        f"about. Replace this placeholder. -->"
    )
    remote = github_remote.strip() or "<org>/<repo>"
    return (text
            .replace("<<TOPIC>>", topic)
            .replace("<<ZULIP_STREAM>>", zulip_stream)
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
                    help="hkust-gz stream name (default: project-<topic>)")
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
    print(f"  topic         = {topic}")
    print(f"  zulip-stream  = {zulip_stream}")
    print(f"  github-remote = {args.github_remote or '(none — leave placeholder)'}")
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
    print( "  4. Open in Claude Code and run /onboard to set up the Zulip bridge.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
