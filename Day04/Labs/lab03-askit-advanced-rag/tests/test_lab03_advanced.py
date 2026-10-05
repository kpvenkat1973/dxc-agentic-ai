"""Lab 3 auto-checks - one test per challenge. Run: pytest Day04\\Labs\\lab03-askit-advanced-rag
Everything runs offline. Test 2 reads the runs saved by the Evals dashboard (evals\\runs.json).
"""
import json
import re
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LAB))

from rag import evals  # noqa: E402

KB = LAB / "data" / "kb"
REPORT = LAB / "submission" / "lab03_report.md"
RUNS = LAB / "evals" / "runs.json"


# ---------- Challenge 1: your own golden questions ----------
def test_challenge_1_my_questions():
    mine = evals.MY_QUESTIONS
    assert len(mine) >= 2, "TODO-1: add 2 questions to MY_QUESTIONS in rag\\evals.py"
    for g in mine:
        for field in ("q", "doc", "key", "expected"):
            assert g.get(field), f"Each question needs '{field}'"
        article = KB / f"{g['doc']}.md"
        assert article.exists(), f"doc '{g['doc']}' is not a file in data\\kb (use the file name without .md)"
        assert g["key"].lower() in article.read_text(encoding="utf-8").lower(), \
            f"key '{g['key']}' is not inside {g['doc']}.md"
    assert len({g["q"] for g in mine}) >= 2, "Use 2 different questions"


# ---------- Challenge 2: eval evidence ----------
def test_challenge_2_eval_runs():
    assert RUNS.exists(), "Run the evaluation in the 📊 Evals dashboard first"
    runs = json.loads(RUNS.read_text(encoding="utf-8"))
    latest = {r["config"]: r for r in runs}
    for name in ("Baseline (naive RAG)", "+ Metadata filter", "+ Section chunks + hybrid", "FDE-grade (all on)"):
        assert name in latest, f"Run '{name}' in the Evals dashboard"
    assert latest["FDE-grade (all on)"]["pass_rate"] > latest["Baseline (naive RAG)"]["pass_rate"], \
        "FDE-grade should beat the baseline. Check your settings and your questions."


# ---------- Challenge 3: security report ----------
def test_challenge_3_security_report():
    assert REPORT.exists(), "submission\\lab03_report.md is missing"
    text = REPORT.read_text(encoding="utf-8")
    section = text.split("## 2.", 1)[-1]
    assert "TODO" not in section, "Replace every TODO in section 2 of the report"
    for label in ("Baseline followed", "FDE-grade followed"):
        m = re.search(label + r".*?:\*\*\s*(.*)", text)
        assert m and m.group(1).strip().lower().startswith(("yes", "no")), f"Answer yes or no after '{label}'"
