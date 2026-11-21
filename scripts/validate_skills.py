#!/usr/bin/env python3
"""Validate Agent Skills. Usage: validate_skills.py [--root DIR] [--agents FILE]. Stdlib only."""
import argparse
import re
import sys
from pathlib import Path

ALLOWED_KEYS = {"name", "description", "license"}
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)[^)]*\)")
FOOTER_RE = re.compile(r"^Built from Freqtrade docs \S+ \(\S+\)\. Source: https://github\.com/freqtrade/freqtrade/tree/\S+/docs\s*$", re.M)
MAX_LINES, MAX_NAME, MAX_DESC = 300, 64, 1024


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


def check_skill(d, agents_text):
    errs = []
    md = d / "SKILL.md"
    if not md.is_file():
        return [f"{d}: missing SKILL.md"]
    text = md.read_text(encoding="utf-8")
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
    if not desc:
        errs.append(f"{p}: description missing")
    elif len(desc) > MAX_DESC:
        errs.append(f"{p}: description {len(desc)} chars > {MAX_DESC}")
    if len(lines) > MAX_LINES:
        errs.append(f"{p}: {len(lines)} lines > {MAX_LINES}")
    if not FOOTER_RE.search(text):
        errs.append(f"{p}: footer line missing")
    for md_file in [md, *sorted((d / "references").glob("*.md"))]:
        for target in LINK_RE.findall(md_file.read_text(encoding="utf-8")):
            if re.match(r"^([a-z]+:|#|/)", target):
                continue
            if not (md_file.parent / target.split("#")[0]).exists():
                errs.append(f"{md_file}: broken link '{target}'")
    for ref in sorted((d / "references").glob("*.md")):
        first = ref.read_text(encoding="utf-8").splitlines()[:1]
        if not first or not first[0].startswith("Source: "):
            errs.append(f"{ref}: first line must start with 'Source: '")
    if d.name not in agents_text:
        errs.append(f"{d}: not listed in AGENTS file")
    return errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="skills")
    ap.add_argument("--agents", default="AGENTS.md")
    a = ap.parse_args()
    root, agents = Path(a.root), Path(a.agents)
    if not root.is_dir():
        print(f"{root}: root dir not found")
        return 1
    if not agents.is_file():
        print(f"{agents}: agents file not found")
        return 1
    agents_text = agents.read_text(encoding="utf-8")
    errs = [e for d in sorted(p for p in root.iterdir() if p.is_dir()) for e in check_skill(d, agents_text)]
    print("\n".join(errs))
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
