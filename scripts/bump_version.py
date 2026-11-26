#!/usr/bin/env python3
"""Bump the pinned Freqtrade release everywhere it is written.

usage: bump_version.py NEW_TAG [--docs-commit SHA] [--root DIR] [--repo-url URL]
The old tag comes from freqtrade-version.json. In skills only the allowed forms of
scripts/validate_skills.py are rewritten; a mention outside them aborts the bump.
Nothing is written unless every check passes. Stdlib only.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_skills import allowed_spans, mention_re, stray_mentions  # noqa: E402

TAG_RE = re.compile(r"^\d{4}\.\d{1,2}$")
REPO_URL = "https://github.com/freqtrade/freqtrade"
# Non-skill files that pin the release: the old tag is replaced as a whole version.
PIN_GLOBS = (".github/workflows/*.yml", "scripts/dpy.sh", "tests/*.sh", "tests/strategies.json",
             "tests/check_results.py", "tests/fixtures/**/SKILL.md", "README.md")
SKIP_PREFIX = "tests/fixtures/bump/"  # the bump self-test fixture stays at its own tag


def read(path):
    with open(path, encoding="utf-8", newline="") as fh:  # newline="" keeps CRLF files intact
        return fh.read()


def docs_commit_for(tag, repo_url):
    """Commit of refs/tags/<tag>, or None when git or the tag is unavailable."""
    try:
        out = subprocess.run(["git", "ls-remote", repo_url, f"refs/tags/{tag}"],
                             capture_output=True, text=True, timeout=60).stdout
    except (OSError, subprocess.TimeoutExpired):
        return None
    return out.split()[0] if out.strip() else None


def bump_skill(text, old, new, commit):
    """Rewrite old to new inside allowed spans; the footer gets the new docs commit."""
    parts, pos = [], 0
    for a, b in sorted(allowed_spans(text, old)):
        if a < pos:  # overlapping forms: the earlier span already covered it
            continue
        parts += [text[pos:a], mention_re(old).sub(new, text[a:b])]
        pos = b
    out = "".join(parts) + text[pos:]
    return re.sub(rf"^(Built from Freqtrade docs {re.escape(new)} \()\S+(\)\.)", rf"\g<1>{commit}\g<2>", out, flags=re.M)


def plan_changes(root, old, new, commit):
    """Return ({path: new_text}, [leftover 'file:line']) without writing anything."""
    changes, leftovers = {}, []
    for f in sorted((root / "skills").rglob("*.md")):
        text = read(f)
        leftovers += [f"{f.relative_to(root).as_posix()}:{n}" for n in stray_mentions(text, old)]
        changes[f] = bump_skill(text, old, new, commit)
    for pattern in PIN_GLOBS:
        for f in sorted(root.glob(pattern)):
            if f.relative_to(root).as_posix().startswith(SKIP_PREFIX):
                continue
            changes[f] = mention_re(old).sub(new, read(f))
    vfile = root / "freqtrade-version.json"
    data = json.loads(read(vfile))
    data.update(tag=new, docs_commit=commit, image=f"freqtradeorg/freqtrade:{new}")
    changes[vfile] = json.dumps(data) + "\n"
    return changes, leftovers


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("new_tag")
    ap.add_argument("--docs-commit")
    ap.add_argument("--root", default=".")
    ap.add_argument("--repo-url", default=REPO_URL)
    a = ap.parse_args()
    if not TAG_RE.match(a.new_tag):
        print(f"{a.new_tag}: not a release tag (YYYY.M)")
        return 1
    root = Path(a.root)
    try:
        old = json.loads(read(root / "freqtrade-version.json"))["tag"]
    except (OSError, ValueError, KeyError, TypeError) as e:
        print(f"{root / 'freqtrade-version.json'}: cannot read 'tag' ({e})")
        return 1
    commit = a.docs_commit or docs_commit_for(a.new_tag, a.repo_url)
    if not commit:
        print(f"cannot resolve docs commit for {a.new_tag} from {a.repo_url}; pass --docs-commit")
        return 1
    changes, leftovers = plan_changes(root, old, a.new_tag, commit)
    if leftovers:
        print(f"hand-written {old} outside the allowed forms (write 'the pinned release'); nothing changed:")
        print("\n".join(leftovers))
        return 1
    for f, text in changes.items():
        if read(f) != text:
            with open(f, "w", encoding="utf-8", newline="") as fh:
                fh.write(text)
    print(f"bumped {old} -> {a.new_tag} (docs {commit})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
