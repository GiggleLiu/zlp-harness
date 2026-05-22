#!/usr/bin/env python3
"""Read a harness Makefile's zulip-config contract safely.

By default this runs `make zulip-config` in the current directory, parses
KEY=VALUE lines, applies the legacy ZULIP_WORKSPACE_DEFAULT compatibility
mapping, and prints either JSON or shell-safe CFG_* assignments.
"""
from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys


KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")
REQUIRED_KEYS = ("ZULIP_SITE", "ZULIP_STREAM", "ZULIP_CONFIG_DIR_DEFAULT")


def parse_config(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        if "=" not in line:
            raise ValueError(f"line {lineno}: expected KEY=VALUE, got {raw!r}")
        key, value = line.split("=", 1)
        key = key.strip()
        if not KEY_RE.fullmatch(key):
            raise ValueError(f"line {lineno}: invalid key {key!r}")
        if "\0" in value:
            raise ValueError(f"line {lineno}: NUL byte in value for {key}")
        out[key] = value

    if "ZULIP_CONFIG_DIR_DEFAULT" not in out and "ZULIP_WORKSPACE_DEFAULT" in out:
        out["ZULIP_CONFIG_DIR_DEFAULT"] = out["ZULIP_WORKSPACE_DEFAULT"]
    return out


def read_make_config() -> str:
    result = subprocess.run(
        ["make", "zulip-config"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "make zulip-config failed").strip())
    return result.stdout


def emit_shell(cfg: dict[str, str]) -> str:
    lines = []
    for key in sorted(cfg):
        lines.append(f"CFG_{key}={shlex.quote(cfg[key])}")
    return "\n".join(lines) + "\n"


def validate_required(cfg: dict[str, str]) -> None:
    missing = [key for key in REQUIRED_KEYS if not cfg.get(key)]
    if missing:
        raise ValueError(f"missing required zulip-config key(s): {', '.join(missing)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-stdin", action="store_true", help="read KEY=VALUE lines from stdin")
    parser.add_argument("--format", choices=("json", "shell"), default="json")
    args = parser.parse_args()

    try:
        text = sys.stdin.read() if args.from_stdin else read_make_config()
        cfg = parse_config(text)
        validate_required(cfg)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.format == "json":
        print(json.dumps(cfg, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(emit_shell(cfg), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
