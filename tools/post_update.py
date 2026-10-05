"""Runs after START_DAY pulls the trainer's content. Makes trainer-owned files exactly match the trainer's version
(so nobody ever needs 'git stash'), and keeps YOUR files (your lab code, submission notes, progress) untouched.
Usage (automatic): python tools\\post_update.py [--force]
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Trainer-owned = students never edit these. Everything else (your lab code, submission\, teams\, progress\, me.json) is yours.
OWNED = [r"^tools/", r"^setup/", r"^governance/", r"^askit_core/", r"^askit_data/", r"^Day\d+/Content/", r"^Day\d+/Hints/",
         r"^Day\d+/Labs/[^/]+/tests/", r"^[^/]+\.(bat|md|txt|toml|ini)$", r"^conftest\.py$", r"^\.gitignore$", r"^\.env\.example$"]


def git(*a):
    p = subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr).strip()


def main():
    code, out = git("ls-tree", "-r", "--name-only", "upstream/main")
    if code != 0:
        print("[!!] Could not read trainer content (no upstream/main). Skipping sync.")
        return 0
    files = [f for f in out.splitlines() if f]
    own = [f for f in files if any(re.match(p, f) for p in OWNED)]
    missing = [f for f in files if not (ROOT / f).exists()]  # new files from the trainer (new labs, new days)
    todo = sorted(set(own + missing))
    for i in range(0, len(todo), 40):
        git("checkout", "upstream/main", "--", *todo[i:i + 40])
    git("add", "-A")
    code, _ = git("diff", "--cached", "--quiet")
    if code != 0:
        git("commit", "-q", "-m", "sync trainer content")
        print(f"[OK] Trainer content synced ({len(todo)} files checked). Your own work was kept.")
    else:
        print("[OK] Up to date.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
