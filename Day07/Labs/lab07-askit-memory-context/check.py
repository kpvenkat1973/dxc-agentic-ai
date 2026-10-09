"""check.py  --  run the automatic checks for one part of the lab.

Type ONE of these lines in the VS Code terminal (Terminal > New Terminal), then press Enter:
    python check.py 7a          Lab 7A   (TODO-1)
    python check.py 7b          Lab 7B   (TODO-2)
    python check.py 7c          Lab 7C   (TODO-3)
    python check.py all         everything (7a, 7b and 7c)

A check that fails tells you what is wrong. Fix it, run the same line again.
The "I completed" buttons on the session page run these same checks.
"""
import sys
from pathlib import Path

import pytest

PARTS = {
    "7a": "test_7a_",
    "7b": "test_7b_",
    "7c": "test_7c_",
    }
part = sys.argv[1].lower() if len(sys.argv) > 1 else "all"
if part != "all" and part not in PARTS:
    sys.exit("Use: python check.py 7a | 7b | 7c | all")


class Summary:
    """Collects what passed and what failed, so we can print one friendly sentence at the end."""

    def __init__(self):
        self.passed, self.failed = 0, []

    def pytest_runtest_logreport(self, report):
        if report.when == "call" and report.passed:
            self.passed += 1
        elif report.failed:
            self.failed.append(report.nodeid)


summary = Summary()
args = [str(Path(__file__).parent / "tests"), "-q", "--tb=short", "-p", "no:cacheprovider"]
if part != "all":
    args += ["-k", PARTS[part]]
code = pytest.main(args, plugins=[summary])

print()
if not summary.failed:
    print(f"RESULT: all {summary.passed} checks passed. Well done!")
elif all("_notes" in f for f in summary.failed):
    print("RESULT: your code is fine. Only your notes are missing.")
    print("  Open submission\\lab07_notes.md, replace every <fill> with your answer, save the file (Ctrl+S),")
    print("  then run the same check line again.")
else:
    print(f"RESULT: {len(summary.failed)} check(s) failed. Read the message under FAILURES above.")
    print("  Stuck? Open Day07\\Hints\\lab07_hints.md and find your TODO.")
sys.exit(code)
