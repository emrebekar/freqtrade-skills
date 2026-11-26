#!/usr/bin/env python3
"""Validate Agent Skills. Usage: validate_skills.py [--root DIR] [--agents FILE] [--version-file FILE]. Stdlib only."""
import argparse
import json
import re
import sys
from pathlib import Path

ALLOWED_KEYS = {"name", "description", "license"}
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)[^)]*\)")
FOOTER_RE = re.compile(r"^Built from Freqtrade docs \S+ \(\S+\)\. Source: https://github\.com/freqtrade/freqtrade/tree/\S+/docs\s*$", re.M)
# Docker images must name the pinned release tag (freqtrade-version.json, plus optional flavor); latest/develop*/stable,
# no tag or a stale release drift from the docs. A missed bump after a new release fails here.
IMAGE_RE = re.compile(r"freqtradeorg/freqtrade(?::([\w.-]*\w))?")
RELEASE_TAG_RE = re.compile(r"^\d{4}\.\d{1,2}(_[a-z]+)?$")
FENCE_RE = re.compile(r"^(```|~~~).*?^\1[ \t]*$", re.M | re.S)
MAX_LINES, MAX_NAME, MAX_DESC = 300, 64, 1024
# The pinned version may appear in skills only in these forms, which scripts/bump_version.py rewrites.
# Anywhere else it is hand-written prose: write "the pinned release" instead.
PIN_LINE_FMT = "Pinned Freqtrade release: {}."
ALLOWED_FORMS = (
    r"freqtradeorg/freqtrade:{P}(?:_[a-z]+)?",
    r"`{P}_[a-z]+`",
    r"Pinned Freqtrade release: {P}\.",
    r"^Built from Freqtrade docs {P} \(\S+\)\. Source: https://github\.com/freqtrade/freqtrade/tree/{P}/docs[ \t]*$",
    r"git checkout {P}",
    r"freqtrade:{P}#",
    r"freqtrade {P}`",  # `--version` output quoted in setup
)


def mention_re(pinned):
    """The pinned literal as a whole version, not part of 2026.100 or 12026.10."""
    return re.compile(rf"(?<![\d.]){re.escape(pinned)}(?!\d)")


def allowed_spans(text, pinned):
    """Character spans of every allowed form of the pinned version in text."""
    p = re.escape(pinned)
    return [m.span() for f in ALLOWED_FORMS for m in re.finditer(f.replace("{P}", p), text, re.M)]


def stray_mentions(text, pinned):
    """Line numbers of pinned-version mentions outside the allowed forms."""
    spans = allowed_spans(text, pinned)
    return [text.count("\n", 0, m.start()) + 1 for m in mention_re(pinned).finditer(text)
            if not any(a <= m.start() and m.end() <= b for a, b in spans)]


def read(path):
    """Return (text, error); utf-8-sig tolerates a BOM."""
    try:
        return path.read_text(encoding="utf-8-sig"), None
    except (UnicodeDecodeError, OSError) as e:
        return None, f"{path}: cannot read ({e})"


def parse_frontmatter(lines):
    """Return (dict, error). shortcut: flat `key: value` only, no YAML nesting/multiline."""
    if not lines or lines[0].strip() != "---":
        return None, "missing frontmatter"
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        return None, "unterminated frontmatter"
    fm = {}
    for ln in lines[1:end]:
        if ln.strip() and ":" in ln:
            k, v = ln.split(":", 1)
            fm[k.strip()] = v.strip().strip("\"'")
    return fm, None


def check_skill(d, agents_text, pinned=None):
    errs = []
    md = d / "SKILL.md"
    if not md.is_file():
        return [f"{d}: missing SKILL.md"]
    text, rerr = read(md)
    if rerr:
        return [rerr]
    lines = text.splitlines()
    p = str(md)
    fm, err = parse_frontmatter(lines)
    if err:
        errs.append(f"{p}: {err}")
        fm = {}
    for k in sorted(set(fm) - ALLOWED_KEYS):
        errs.append(f"{p}: frontmatter key '{k}' not allowed")
    name = fm.get("name", "")
    if not name:
        errs.append(f"{p}: name missing")
    elif not NAME_RE.match(name) or len(name) > MAX_NAME:
        errs.append(f"{p}: name '{name}' invalid (lowercase-hyphenated, <= {MAX_NAME})")
    if name and name != d.name:
        errs.append(f"{p}: name '{name}' != folder '{d.name}'")
    desc = fm.get("description", "")
    if desc in (">", "|", ">-", "|-", ">+", "|+"):
        errs.append(f"{p}: description block scalar unsupported, use a single line")
    elif not desc:
        errs.append(f"{p}: description missing")
    elif len(desc) > MAX_DESC:
        errs.append(f"{p}: description {len(desc)} chars > {MAX_DESC}")
    if len(lines) > MAX_LINES:
        errs.append(f"{p}: {len(lines)} lines > {MAX_LINES}")
    last = next((ln for ln in reversed(lines) if ln.strip()), "")
    if not FOOTER_RE.match(last):
        errs.append(f"{p}: footer line missing or not the last non-empty line")
    elif pinned and not last.startswith(f"Built from Freqtrade docs {pinned} "):
        errs.append(f"{p}: footer tag != {pinned}")
    if pinned and text.count(PIN_LINE_FMT.format(pinned)) != 1:
        errs.append(f"{p}: pinned line '{PIN_LINE_FMT.format(pinned)}' missing or repeated")
    refs =sorted((d / "references").glob("*.md"))
    for md_file in [md, *refs]:
        body, rerr = (text, None) if md_file == md else read(md_file)
        if rerr:
            errs.append(rerr)
            continue
        for target in LINK_RE.findall(FENCE_RE.sub("", body)):
            if re.match(r"^([a-z]+:|#|/)", target):
                continue
            if not (md_file.parent / target.split("#")[0]).exists():
                errs.append(f"{md_file}: broken link '{target}'")
        for tag in IMAGE_RE.findall(body):
            if not RELEASE_TAG_RE.match(tag) or (pinned and tag.split("_")[0] != pinned):
                want = f" (want {pinned})" if pinned else ""
                errs.append(f"{md_file}: image 'freqtradeorg/freqtrade:{tag or '(no tag)'}' is not the pinned release tag{want}")
        for n in stray_mentions(body, pinned) if pinned else []:
            errs.append(f"{md_file}:{n}: hand-written version '{pinned}', write 'the pinned release'")
        if md_file != md and not body.startswith("Source: "):
            errs.append(f"{md_file}: first line must start with 'Source: '")
    if not re.search(rf"(?<![\w-]){re.escape(d.name)}(?![\w-])", agents_text):
        errs.append(f"{d}: not listed in AGENTS file")
    return errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="skills")
    ap.add_argument("--agents", default="AGENTS.md")
    ap.add_argument("--version-file", default="freqtrade-version.json")
    a = ap.parse_args()
    root, agents = Path(a.root), Path(a.agents)
    if not root.is_dir():
        print(f"{root}: root dir not found")
        return 1
    if not agents.is_file():
        print(f"{agents}: agents file not found")
        return 1
    agents_text, rerr = read(agents)
    if rerr:
        print(rerr)
        return 1
    vtext, rerr = read(Path(a.version_file))
    if rerr:
        print(rerr)
        return 1
    try:
        pinned = json.loads(vtext)["tag"]
    except (ValueError, KeyError, TypeError) as e:
        print(f"{a.version_file}: no 'tag' ({e})")
        return 1
    errs = [e for d in sorted(p for p in root.iterdir() if p.is_dir()) for e in check_skill(d, agents_text, pinned)]
    if errs:
        print("\n".join(errs))
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
