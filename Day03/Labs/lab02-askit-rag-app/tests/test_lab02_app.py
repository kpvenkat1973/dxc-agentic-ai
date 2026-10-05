"""Lab 2 auto-checks. Run: pytest Day03\\Labs\\lab02-askit-rag-app
Test 1 checks the KB is in your repo. Tests 2-3 check your experiment evidence.
"""
import re
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
REPO = LAB.parents[2]
EXPERIMENT = LAB / "submission" / "experiment.md"


def _rows():
    rows = []
    for line in EXPERIMENT.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 5 and cells[0].isdigit():
            rows.append(cells)
    return rows


def test_kb_is_in_repo():
    kb = REPO / "askit_data" / "kb"
    assert kb.is_dir() and len(list(kb.glob("KB-*.md"))) == 20, "askit_data\\kb should hold 20 KB articles. Run START_DAY.bat to update your repo."


def test_experiment_numbers():
    assert EXPERIMENT.exists(), "submission\\experiment.md is missing"
    done = [r for r in _rows() if re.fullmatch(r"\d+/\d+", r[3]) and re.fullmatch(r"\d+/\d+", r[4])]
    assert len(done) >= 3, "Fill at least 3 rows of the table with your Mini eval results (replace the ?/10)"
    assert len({r[0] for r in done}) >= 2, "Use at least 2 different chunk sizes"


def test_experiment_conclusion():
    text = EXPERIMENT.read_text(encoding="utf-8")
    m = re.search(r"\*\*What I learned.*?\*\*(.*)", text)
    assert m and m.group(1).strip() and "TODO" not in m.group(1), "Write 1-2 sentences after 'What I learned' (replace TODO)"
