#!/usr/bin/env python3
"""Check freqtrade CLI flags in fenced shell blocks. Usage: check_cli.py [--root DIR]. Stdlib only.

Run inside the freqtrade image (needs `freqtrade` on PATH): scripts/dpy.sh scripts/check_cli.py
"""
import argparse
import re
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

SHELL_LANGS = {"bash", "sh", "shell", "console"}
OPENING_FENCE_RE = re.compile(r"^\s*```\s*(\w*)")
TOKEN_RE = re.compile(r"""(?:"[^"]*"|'[^']*'|\S)+""")
FLAG_RE = re.compile(r"(?<![\w-])(--?[A-Za-z][\w-]*)")
SUBCOMMANDS_RE = re.compile(r"\{([a-z0-9,-]+)\}")
IMAGE_RE = re.compile(r"^freqtradeorg/freqtrade(:\S+)?$")
OPERATORS = {"|", "||", "&&", ";", "&"}


@lru_cache(maxsize=None)
def help_text(sub):
    cmd = ["freqtrade"] + ([sub] if sub else []) + ["--help"]
    return subprocess.run(cmd, capture_output=True, text=True).stdout


@lru_cache(maxsize=None)
def known_flags(sub):
    return frozenset(FLAG_RE.findall(help_text(sub)))


@lru_cache(maxsize=None)
def known_subcommands():
    return frozenset(c for m in SUBCOMMANDS_RE.findall(help_text("")) for c in m.split(","))


def shell_commands(text):
    """Yield (line_number, joined_command_line) for each command in shell fences."""
    lang, pending, start = None, "", 0
    for n, raw in enumerate(text.splitlines(), 1):
        m = OPENING_FENCE_RE.match(raw)
        if m and lang is None:
            lang = m.group(1).lower() or "-"
            continue
        if raw.strip().startswith("```"):
            lang, pending = None, ""
            continue
        if lang not in SHELL_LANGS:
            continue
        line = raw.strip()
        if lang == "console" and line.startswith("$ "):
            line = line[2:]
        if not pending:
            start = n
        if line.endswith("\\"):
            pending += line[:-1] + " "
            continue
        yield start, pending + line
        pending = ""


def segments(line):
    """Split a command line into token lists at shell operators; drop # comments."""
    seg = []
    for tok in TOKEN_RE.findall(line):
        if tok.startswith("#"):
            break
        if tok in OPERATORS:
            yield seg
            seg = []
        else:
            seg.append(tok)
    yield seg


def freqtrade_args(tokens):
    """Return args after the freqtrade invocation, or None if the segment is not one."""
    while tokens and re.match(r"^\w+=", tokens[0]):  # VAR=value prefixes
        tokens = tokens[1:]
    if not tokens:
        return None
    if tokens[0] == "freqtrade":
        return tokens[1:]
    if tokens[0] in ("docker", "docker-compose"):
        for i, tok in enumerate(tokens):
            if tok == "freqtrade" or IMAGE_RE.match(tok):
                return tokens[i + 1:]
    return None


def check_segment(args, where):
    sub = next((t for t in args if not t.startswith("-")), None)
    if sub is not None and sub.startswith(("'", '"')):
        return
    if sub is not None and sub not in known_subcommands():
        yield f"{where}: unknown subcommand {sub}"
        return
    # flags before the subcommand belong to the main parser
    for tok in args:
        if tok.startswith(("'", '"')) or not tok.startswith("-"):
            continue
        flag = tok.split("=", 1)[0]
        if FLAG_RE.fullmatch(flag) and flag not in known_flags(sub or ""):
            yield f"{where}: {flag} not in freqtrade{' ' + sub if sub else ''}"


def check_file(path):
    text = path.read_text(encoding="utf-8-sig")
    for line_no, line in shell_commands(text):
        for tokens in segments(line):
            args = freqtrade_args(tokens)
            if args is not None:
                yield from check_segment(args, f"{path}:{line_no}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="skills")
    root = Path(ap.parse_args().root)
    errors = []
    for md in sorted(root.rglob("*.md")) if root.is_dir() else []:
        errors.extend(check_file(md))
    for e in errors:
        print(e)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
