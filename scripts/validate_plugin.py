#!/usr/bin/env python3
"""Validate the zlp-harness plugin skills and scaffolded harness output."""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"

PLACEHOLDERS = (
    "<<TOPIC>>",
    "<<ZULIP_STREAM>>",
    "<<ZULIP_SITE>>",
    "<<CONFIG_LABEL>>",
    "<<WORKSPACE_LABEL>>",
    "<<GITHUB_REMOTE>>",
    "<<TOPIC_BLURB>>",
)

STALE_GENERATED_PATHS = (
    ".claude/skills/download-ref",
    ".claude/skills/zulip-reply",
    ".claude/skills/zlp-advisor",
    ".claude/skills/zlp-onboard",
)


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


FORBIDDEN_TOOL_REFERENCES = (
    "AskUserQuestion",
    "Claude Code",
    "Skill(",
    "available-skills system reminder",
)


def run(cmd: list[str], *, cwd: Path, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, input=input_text, text=True, capture_output=True)


def parse_frontmatter(path: Path, errors: list[str]) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        fail(errors, f"{path}: missing opening frontmatter marker")
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        fail(errors, f"{path}: missing closing frontmatter marker")
        return {}

    data: dict[str, str] = {}
    for lineno, line in enumerate(text[4:end].splitlines(), start=2):
        if not line.strip():
            continue
        if ":" not in line:
            fail(errors, f"{path}:{lineno}: expected KEY: VALUE")
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if key in data:
            fail(errors, f"{path}:{lineno}: duplicate key {key!r}")
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        elif value.startswith("'") and value.endswith("'"):
            value = value[1:-1]
        elif ": " in value:
            fail(errors, f"{path}:{lineno}: quote values containing ': '")
        data[key] = value
    return data


def validate_skill(skill_dir: Path, errors: list[str], *, expected_name: str | None = None) -> None:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        fail(errors, f"{skill_dir}: missing SKILL.md")
        return

    data = parse_frontmatter(skill_md, errors)
    extra = sorted(set(data) - {"name", "description"})
    if extra:
        fail(errors, f"{skill_md}: unsupported frontmatter keys: {', '.join(extra)}")

    name = data.get("name", "")
    description = data.get("description", "")
    want_name = expected_name or skill_dir.name
    if name != want_name:
        fail(errors, f"{skill_md}: name {name!r} does not match {want_name!r}")
    if not re.fullmatch(r"[a-z0-9-]+", name):
        fail(errors, f"{skill_md}: invalid skill name {name!r}")
    if not description:
        fail(errors, f"{skill_md}: missing description")
    if "<" in description or ">" in description:
        fail(errors, f"{skill_md}: description must not contain angle brackets")


def compile_helpers(errors: list[str]) -> None:
    for path in sorted(SKILLS.glob("*/helpers/*.py")):
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
        except SyntaxError as exc:
            fail(errors, f"{path}:{exc.lineno}: {exc.msg}")


def validate_no_tool_references(errors: list[str]) -> None:
    for path in sorted(list(SKILLS.glob("*/SKILL.md")) + list(SKILLS.glob("*/templates/**/*.md"))):
        text = path.read_text(encoding="utf-8")
        for token in FORBIDDEN_TOOL_REFERENCES:
            if token in text:
                fail(errors, f"{path}: contains platform-specific tool reference {token!r}")


def validate_zulip_config_helper(errors: list[str]) -> None:
    helper = SKILLS / "zlp-onboard" / "helpers" / "read_zulip_config.py"
    if not helper.exists():
        fail(errors, f"{helper}: missing safer zulip-config parser helper")
        return

    stream = "LLM 项目's phase"
    cfg_dir = "/tmp/zlp harness/quote's"
    sample = (
        "ZULIP_SITE=https://quantum-info.zulipchat.com\n"
        f"ZULIP_STREAM={stream}\n"
        f"ZULIP_WORKSPACE_DIR_DEFAULT={cfg_dir}\n"
    )
    parsed = run(
        [sys.executable, str(helper), "--from-stdin", "--format", "shell"],
        cwd=ROOT,
        input_text=sample,
    )
    if parsed.returncode != 0:
        fail(errors, f"{helper}: shell output failed:\n{parsed.stderr or parsed.stdout}")
        return

    probe = subprocess.run(
        [
            "/bin/sh",
            "-c",
            (
                'eval "$1"; '
                'test "$CFG_ZULIP_SITE" = "https://quantum-info.zulipchat.com" && '
                'test "$CFG_ZULIP_STREAM" = "$2" && '
                'test "$CFG_ZULIP_WORKSPACE_DIR_DEFAULT" = "$3"'
            ),
            "sh",
            parsed.stdout,
            stream,
            cfg_dir,
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    if probe.returncode != 0:
        fail(errors, f"{helper}: shell assignments did not round-trip quoted values")

    compat = run(
        [sys.executable, str(helper), "--from-stdin", "--format", "json"],
        cwd=ROOT,
        input_text=(
            "ZULIP_SITE=https://example.zulipchat.com\n"
            "ZULIP_STREAM=project-test\n"
            "ZULIP_WORKSPACE_DEFAULT=/tmp/legacy\n"
        ),
    )
    if compat.returncode != 0 or '"ZULIP_WORKSPACE_DIR_DEFAULT": "/tmp/legacy"' not in compat.stdout:
        fail(errors, f"{helper}: did not map legacy ZULIP_WORKSPACE_DEFAULT to ZULIP_WORKSPACE_DIR_DEFAULT")


def validate_scaffold(errors: list[str]) -> None:
    scaffold = SKILLS / "init-harness" / "helpers" / "scaffold.py"
    with tempfile.TemporaryDirectory(prefix="zlp-harness-validate-") as tmp:
        target = Path(tmp) / "validate-probe.harness"
        result = run(
            [
                sys.executable,
                str(scaffold),
                "--topic",
                "validate-probe",
                "--target-dir",
                str(target),
                "--zulip-stream",
                "project-validate-probe",
                "--zulip-site",
                "https://quantum-info.zulipchat.com",
                "--github-remote",
                "Test/validate-probe.harness",
            ],
            cwd=ROOT,
        )
        if result.returncode != 0:
            fail(errors, f"scaffold failed:\n{result.stderr or result.stdout}")
            return

        cfg = run(["make", "-C", str(target), "zulip-config"], cwd=ROOT)
        if cfg.returncode != 0:
            fail(errors, f"generated make zulip-config failed:\n{cfg.stderr or cfg.stdout}")
        for key in ("ZULIP_SITE=", "ZULIP_STREAM=", "ZULIP_WORKSPACE_DIR_DEFAULT="):
            if key not in cfg.stdout:
                fail(errors, f"generated zulip-config missing {key}")

        cfg_helper = SKILLS / "zlp-onboard" / "helpers" / "read_zulip_config.py"
        helper_result = run([sys.executable, str(cfg_helper), "--format", "json"], cwd=target)
        if helper_result.returncode != 0:
            fail(errors, f"zulip-config helper failed against scaffold:\n{helper_result.stderr or helper_result.stdout}")
        for expected in (
            '"ZULIP_SITE": "https://quantum-info.zulipchat.com"',
            '"ZULIP_STREAM": "project-validate-probe"',
            '"ZULIP_WORKSPACE_DIR_DEFAULT":',
        ):
            if expected not in helper_result.stdout:
                fail(errors, f"zulip-config helper output missing {expected}")

        validate_skill(target / ".claude" / "skills" / "onboard", errors, expected_name="onboard")

        for path in sorted(p for p in target.rglob("*") if p.is_file()):
            text = path.read_text(encoding="utf-8", errors="ignore")
            for placeholder in PLACEHOLDERS:
                if placeholder in text:
                    fail(errors, f"{path.relative_to(target)} still contains {placeholder}")
            for stale in STALE_GENERATED_PATHS:
                if stale in text:
                    fail(errors, f"{path.relative_to(target)} references stale plugin path {stale}")


def validate_weekly_advisor_cryo_helper(errors: list[str]) -> None:
    helper = SKILLS / "create-weekly-advisor-cryo" / "helpers" / "scaffold.py"
    if not helper.exists():
        fail(errors, f"{helper}: missing weekly advisor cryo scaffold helper")
        return

    with tempfile.TemporaryDirectory(prefix="weekly-advisor-cryo-validate-") as tmp:
        target = Path(tmp) / "qtest-advisor.harness"
        result = run(
            [
                sys.executable,
                str(helper),
                "--target-dir",
                str(target),
                "--project-name",
                "Quantum Test",
                "--operator",
                "Dr. Q",
                "--zulip-site",
                "https://example.zulipchat.com",
                "--zulip-stream",
                "project-qtest",
                "--zulip-topic",
                "weekly advisor",
                "--weekly-day",
                "Tuesday",
                "--weekly-time",
                "10:30",
                "--agent",
                "codex",
                "--skip-cryo-init",
            ],
            cwd=ROOT,
        )
        if result.returncode != 0:
            fail(errors, f"weekly advisor cryo scaffold failed:\n{result.stderr or result.stdout}")
            return

        expected_files = (
            "AGENTS.md",
            "CLAUDE.md",
            "README.md",
            ".gitignore",
            "plan.md",
            "NOTES.md",
            "cryo.toml",
            "mailbox/README.md",
            ".claude/skills/mailbox-send/SKILL.md",
        )
        for rel in expected_files:
            if not (target / rel).exists():
                fail(errors, f"weekly advisor cryo scaffold missing {rel}")

        plan = (target / "plan.md").read_text(encoding="utf-8")
        for expected in ("Quantum Test", "Dr. Q", "project-qtest", "weekly advisor", "Tuesday around 10:30"):
            if expected not in plan:
                fail(errors, f"weekly advisor cryo plan missing {expected!r}")

        config = (target / "cryo.toml").read_text(encoding="utf-8")
        if 'agent = "codex"' not in config:
            fail(errors, "weekly advisor cryo config did not set requested agent")
        if 'watch_dirs = ["messages/inbox", "mailbox/inbox"]' not in config:
            fail(errors, "weekly advisor cryo config did not watch mailbox inbox")

        for path in sorted(p for p in target.rglob("*") if p.is_file()):
            text = path.read_text(encoding="utf-8", errors="ignore")
            if re.search(r"<<[A-Z0-9_]+>>", text):
                fail(errors, f"{path.relative_to(target)} still contains a placeholder")

        if shutil.which("cryo"):
            cryo_target = Path(tmp) / "qtest-advisor-cryo-init.harness"
            cryo_result = run(
                [
                    sys.executable,
                    str(helper),
                    "--target-dir",
                    str(cryo_target),
                    "--project-name",
                    "Quantum Test",
                    "--operator",
                    "Dr. Q",
                    "--zulip-site",
                    "https://example.zulipchat.com",
                    "--zulip-stream",
                    "project-qtest",
                    "--zulip-topic",
                    "weekly advisor",
                    "--agent",
                    "codex",
                ],
                cwd=ROOT,
            )
            if cryo_result.returncode != 0:
                fail(errors, f"weekly advisor cryo scaffold failed with cryo init:\n{cryo_result.stderr or cryo_result.stdout}")


def main() -> int:
    errors: list[str] = []

    for skill_md in sorted(SKILLS.glob("*/SKILL.md")):
        validate_skill(skill_md.parent, errors)

    compile_helpers(errors)
    validate_no_tool_references(errors)
    validate_zulip_config_helper(errors)
    validate_scaffold(errors)
    validate_weekly_advisor_cryo_helper(errors)

    if errors:
        print("validation failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print("plugin validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
