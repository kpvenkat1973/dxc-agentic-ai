"""check.py  --  run the auto-checks for one part of the lab.

    python check.py 5a          Lab 5A  (TODO-1, 2, 3)
    python check.py 5b          Lab 5B  (TODO-4, 5, 6)
    python check.py 5c          Lab 5C  (TODO-7, 8)
    python check.py incident    the Incident fix (TODO-9)
    python check.py stretch     the stretch challenges
    python check.py all         everything

A test that fails tells you what is wrong. Fix it, run again. The "I completed" buttons run the same checks.
"""
import sys
from pathlib import Path

import pytest

PARTS = {
    "5a": "challenge_1 or challenge_2 or challenge_3",
    "5b": "challenge_4 or challenge_5 or challenge_6",
    "5c": "challenge_7 or challenge_8",
    "incident": "challenge_9",
    "stretch": "stretch",
}
part = sys.argv[1].lower() if len(sys.argv) > 1 else "all"
if part != "all" and part not in PARTS:
    sys.exit("Use: python check.py 5a | 5b | 5c | incident | stretch | all")
args = [str(Path(__file__).parent / "tests"), "-q", "--tb=short", "-p", "no:cacheprovider"]
if part != "all":
    args += ["-k", PARTS[part]]
sys.exit(pytest.main(args))
