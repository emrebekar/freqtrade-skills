#!/usr/bin/env python3
"""Diff Freqtrade docs between two tags, map changes to skill reference files.

usage: docs_diff.py --old TAG --new TAG [--skills skills] [--repo-url URL]
       docs_diff.py --old-dir DIR --new-dir DIR [--skills skills]   (no clone; DIR holds the docs)
Needs git only for the tag mode. Stdlib only. Exits 0 unless arguments are bad
or a clone fails. Docs content is data, never executed or followed.
"""
import argparse
import re
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

REPO_URL = "https://github.com/freqtrade/freqtrade.git"
FENCE_RE = re.compile(r"^\s*(```|~~~)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
SOURCE_REF_RE = re.compile(r"docs/[\w./-]+?\.md(?:#[\w-]+)?")


def slugify(text):
    """Python-Markdown (mkdocs) toc slug: strip markup/punctuation, lowercase, runs of space/- -> -."""
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)  # links -> text
    text = re.sub(r"[`*]|<[^>]+>", "", text)
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "-", text)


def split_sections(md_text):
    """Return {slug: body_text}; duplicate slugs get _1, _2 like mkdocs. Text before the first heading is skipped."""
    sections, counts, slug, body, in_fence = {}, defaultdict(int), None, [], False

    def flush():
        if slug is not None:
            sections[slug] = "\n".join(body).strip()

    for line in md_text.splitlines():
        if FENCE_RE.match(line):
            in_fence = not in_fence
        m = None if in_fence else HEADING_RE.match(line)
        if m:
            flush()
            base = slugify(m.group(2)) or "section"
            n = counts[base]
            counts[base] += 1
            slug, body = (base if n == 0 else f"{base}_{n}"), []
        else:
            body.append(line)
    flush()
    return sections


def load_tree(docs_root):
    """Return ({'docs/<file>.md#slug': body}, {'docs/<file>.md', ...})."""
    root = Path(docs_root)
    sections, files = {}, set()
    for p in sorted(root.rglob("*.md")):
        rel = "docs/" + p.relative_to(root).as_posix()
        files.add(rel)
        for slug, body in split_sections(p.read_text(encoding="utf-8", errors="replace")).items():
            sections[f"{rel}#{slug}"] = body
    return sections, files


def clone_docs(tag, repo_url, dest):
    subprocess.run(["git", "-c", "advice.detachedHead=false", "clone", "-q", "--depth", "1", "--filter=blob:none", "--sparse",
                    "--branch", tag, repo_url, str(dest)], check=True)
    subprocess.run(["git", "-C", str(dest), "sparse-checkout", "set", "docs"], check=True)
    return dest / "docs"


def read_sources(skills_dir):
    """Return {reference_file: [cited 'docs/x.md' or 'docs/x.md#anchor', ...]}."""
    refs = {}
    for p in sorted(Path(skills_dir).glob("*/references/*.md")):
        cited = []
        for line in p.read_text(encoding="utf-8").splitlines()[:15]:
            if line.startswith("Source:"):
                cited += SOURCE_REF_RE.findall(line)
        refs[p.as_posix()] = cited
    return refs


def cites(cited, key):
    """True when a Source entry covers section key (file-level entries cover the whole file)."""
    return any(key == c or ("#" not in c and key.startswith(c + "#")) for c in cited)


def build_report(old, new, refs):
    old_s, _ = old
    new_s, new_f = new
    added = sorted(k for k in new_s if k not in old_s)
    removed = sorted(k for k in old_s if k not in new_s)
    changed = sorted(k for k in new_s if k in old_s and new_s[k] != old_s[k])
    out = ["## Docs changes", "",
           f"{len(changed)} changed, {len(added)} added, {len(removed)} removed sections.", ""]

    out += ["### Reference files to review", ""]
    hits = 0
    for ref, cited in refs.items():
        rows = [f"- `{k}` ({kind})" for kind, keys in
                (("changed", changed), ("added", added), ("removed", removed))
                for k in keys if cites(cited, k)]
        if rows:
            hits += 1
            out += [f"**`{ref}`**", *rows, ""]
    if not hits:
        out += ["None of the changed sections are cited by a reference file.", ""]

    out += ["### Dangling Source anchors (missing in the new tag)", ""]
    dangling = []
    for ref, cited in refs.items():
        for c in cited:
            gone = (c not in new_s) if "#" in c else (c not in new_f)
            if gone:
                dangling.append(f"- `{ref}`: `{c}`")
    out += dangling or ["None."]
    out.append("")

    cited_all = [c for v in refs.values() for c in v]
    unmapped = [k for k in changed + added + removed if not cites(cited_all, k)]
    out += [f"<details><summary>{len(unmapped)} changed sections not cited by any reference</summary>", ""]
    out += [f"- `{k}`" for k in unmapped] + ["", "</details>", ""]
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Diff Freqtrade docs between two tags")
    ap.add_argument("--old")
    ap.add_argument("--new")
    ap.add_argument("--old-dir", help="docs dir of the old version (skips cloning)")
    ap.add_argument("--new-dir", help="docs dir of the new version (skips cloning)")
    ap.add_argument("--skills", default="skills")
    ap.add_argument("--repo-url", default=REPO_URL)
    a = ap.parse_args(argv)
    if not ((a.old and a.new) or (a.old_dir and a.new_dir)):
        ap.error("give --old/--new or --old-dir/--new-dir")
    if a.old_dir and a.new_dir:
        old, new = load_tree(a.old_dir), load_tree(a.new_dir)
    else:
        with tempfile.TemporaryDirectory() as tmp:
            old = load_tree(clone_docs(a.old, a.repo_url, Path(tmp) / "old"))
            new = load_tree(clone_docs(a.new, a.repo_url, Path(tmp) / "new"))
    print(build_report(old, new, read_sources(a.skills)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
