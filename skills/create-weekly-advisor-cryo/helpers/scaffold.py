#!/usr/bin/env python3
"""Scaffold a benchmark-style weekly advisor Cryochamber chamber."""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"

PLACEHOLDER_RE = re.compile(r"<<([A-Z0-9_]+)>>")
SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(value: str) -> str:
    slug = SLUG_RE.sub("-", value.lower()).strip("-")
    return slug or "weekly-advisor"


def fail(message: str, code: int = 2) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(code)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-dir", required=True, help="Fresh or empty chamber directory to create")
    parser.add_argument("--project-name", required=True, help="Human-readable project name")
    parser.add_argument("--operator", required=True, help="Operator or PI name")
    parser.add_argument("--zulip-site", required=True, help="Messenger/Zulip site value, such as problem-reductions or https://example.zulipchat.com")
    parser.add_argument("--zulip-stream", required=True, help="Zulip stream for weekly posts")
    parser.add_argument("--zulip-topic", default="weekly advisor", help="Zulip topic for weekly posts")
    parser.add_argument("--weekly-day", default="Monday", help="Weekly check day")
    parser.add_argument("--weekly-time", default="09:00", help="Local check time, HH:MM")
    parser.add_argument("--agent", default="claude", help="Agent command for cryo.toml")
    parser.add_argument("--force", action="store_true", help="Allow writing into a non-empty target")
    parser.add_argument("--skip-cryo-init", action="store_true", help="Skip cryo init; intended for repository validation tests")
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if not re.fullmatch(r"[A-Za-z]+", args.weekly_day):
        fail("--weekly-day should be a day name such as Monday")
    if not re.fullmatch(r"[0-2][0-9]:[0-5][0-9]", args.weekly_time):
        fail("--weekly-time must be HH:MM")
    hour = int(args.weekly_time.split(":", 1)[0])
    if hour > 23:
        fail("--weekly-time hour must be between 00 and 23")
    if not re.fullmatch(r"[A-Za-z0-9._/-]+", args.agent):
        fail("--agent should be an executable name or simple path")


def ensure_templates() -> None:
    required = (
        "AGENTS.md",
        "CLAUDE.md.tmpl",
        "README.md.tmpl",
        "gitignore",
        "plan.md.tmpl",
        "NOTES.md",
        "cryo.toml.tmpl",
        "mailbox/README.md",
        "skills/mailbox-send/SKILL.md",
    )
    missing = [rel for rel in required if not (TEMPLATES / rel).exists()]
    if missing:
        fail(f"missing bundled template(s): {', '.join(missing)}")


def render_template(path: Path, values: dict[str, str]) -> str:
    text = path.read_text(encoding="utf-8")

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in values:
            fail(f"{path.relative_to(TEMPLATES)} references unknown placeholder <<{key}>>")
        return values[key]

    return PLACEHOLDER_RE.sub(replace, text)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def copy_static(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)


def run_cryo_init(target: Path, agent: str) -> str:
    if not shutil.which("cryo"):
        fail("cryo CLI not found on PATH. Install it with: cargo install --path ~/rcode/cryochamber")
    result = subprocess.run(
        ["cryo", "init", "--agent", agent],
        cwd=target,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        fail(f"cryo init failed:\n{result.stderr or result.stdout}", code=result.returncode)
    return result.stdout.strip()


def main() -> int:
    args = parse_args()
    validate_args(args)
    ensure_templates()

    target = Path(args.target_dir).expanduser().resolve()
    if target.exists() and any(target.iterdir()) and not args.force:
        fail(f"{target} is not empty; pass --force only with explicit user approval")
    target.mkdir(parents=True, exist_ok=True)

    project_slug = slugify(args.project_name)
    values = {
        "PROJECT_NAME": args.project_name,
        "PROJECT_SLUG": project_slug,
        "OPERATOR": args.operator,
        "ZULIP_SITE": args.zulip_site,
        "ZULIP_STREAM": args.zulip_stream,
        "ZULIP_TOPIC": args.zulip_topic,
        "WEEKLY_DAY": args.weekly_day,
        "WEEKLY_TIME": args.weekly_time,
        "AGENT": args.agent,
    }

    cryo_init_output = ""
    if not args.skip_cryo_init:
        cryo_init_output = run_cryo_init(target, args.agent)

    render_map = {
        "AGENTS.md": TEMPLATES / "AGENTS.md",
        "CLAUDE.md": TEMPLATES / "CLAUDE.md.tmpl",
        "README.md": TEMPLATES / "README.md.tmpl",
        "plan.md": TEMPLATES / "plan.md.tmpl",
        "cryo.toml": TEMPLATES / "cryo.toml.tmpl",
    }
    for rel, src in render_map.items():
        write_text(target / rel, render_template(src, values))

    copy_static(TEMPLATES / "NOTES.md", target / "NOTES.md")
    copy_static(TEMPLATES / "gitignore", target / ".gitignore")
    copy_static(TEMPLATES / "mailbox" / "README.md", target / "mailbox" / "README.md")
    copy_static(TEMPLATES / "skills" / "mailbox-send" / "SKILL.md", target / ".claude" / "skills" / "mailbox-send" / "SKILL.md")

    for rel in (
        "messages/inbox",
        "messages/outbox",
        "mailbox/inbox",
        "mailbox/outbox",
    ):
        (target / rel).mkdir(parents=True, exist_ok=True)

    written = [
        "AGENTS.md",
        "CLAUDE.md",
        "README.md",
        ".gitignore",
        "plan.md",
        "NOTES.md",
        "cryo.toml",
        "mailbox/README.md",
        ".claude/skills/mailbox-send/SKILL.md",
    ]

    print(f"weekly advisor cryo scaffolded at {target}")
    if cryo_init_output:
        print("\ncryo init output:")
        print(cryo_init_output)
    print("\nwritten files:")
    for rel in written:
        print(f"  {rel}")
    print("\nnext steps:")
    print(f"  1. Review {target / 'plan.md'}")
    print("  2. Configure the messenger/mailbox bridge before team-channel posts")
    print(f"  3. When ready, run: cd {target} && cryo start")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
