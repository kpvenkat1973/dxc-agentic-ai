"""Lab 4 auto-checks - one test per challenge. Run: pytest Day04\\Labs\\lab04-askit-agentic-rag
Offline, no key needed. Test 4 reads the runs saved by the Compare tab (evals_agentic\\runs.json)."""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

LAB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LAB))

import agentic  # noqa: E402

REPORT = LAB / "submission" / "lab04_report.md"
RUNS = LAB / "evals_agentic" / "runs.json"


class FakeLLM:
    offline = False

    def __init__(self, reply):
        self.reply, self.calls = reply, []

    def chat(self, messages, op="generate", json_mode=False, tools=None, model=None):
        self.calls.append(messages[0]["content"])
        return SimpleNamespace(content=self.reply), dict(operation=op)


def _index(reply):
    return SimpleNamespace(llm=FakeLLM(reply))


# ---------- Challenge 1: read the critic's reply ----------
def test_challenge_1_parse_critic():
    p = agentic.parse_critic
    assert p('{"enough": false, "missing": "personal laptop rule"}') == {"enough": False, "missing": "personal laptop rule"}
    assert p('```json\n{"enough": true, "missing": ""}\n```')["enough"] is True
    assert p('{"enough": "no", "missing": "SLA"}') == {"enough": False, "missing": "SLA"}
    assert p('{"enough": "yes"}')["enough"] is True
    assert p("sorry, I cannot say") == {"enough": True, "missing": ""}, "a broken reply must never start a loop"
    assert p("") == {"enough": True, "missing": ""}


# ---------- Challenge 2: write the rewrite step ----------
def test_challenge_2_rewrite_query():
    idx, res = _index('  "laptop lost response time"  '), SimpleNamespace(usage=[])
    out = agentic.rewrite_query(idx, res, "I lost my laptop, how fast do you respond?", "response time")
    assert out == "laptop lost response time", "strip spaces and quotes from the reply"
    assert len(idx.llm.calls) == 1, "call the LLM once"
    assert "I lost my laptop, how fast do you respond?" in idx.llm.calls[0], "the prompt must contain the original question"
    assert "response time" in idx.llm.calls[0], "the prompt must contain what is missing"
    assert len(res.usage) == 1, "append the usage row to res.usage"
    assert agentic.rewrite_query(_index(""), SimpleNamespace(usage=[]), "my question", "x") == "my question", "empty reply: keep the question"


# ---------- Challenge 3: loop control ----------
def test_challenge_3_should_continue():
    f = agentic.should_continue
    assert f(1, {"enough": False, "missing": "x"}, 2) is True
    assert f(2, {"enough": False, "missing": "x"}, 2) is False, "round limit reached"
    assert f(1, {"enough": True, "missing": ""}, 2) is False, "critic is satisfied"
    assert f(1, {"enough": False, "missing": "x"}, 1) is False, "max_rounds = 1 means no loop"


# ---------- Challenge 4: evidence ----------
def test_challenge_4_evidence():
    assert REPORT.exists(), "submission\\lab04_report.md is missing"
    text = REPORT.read_text(encoding="utf-8")
    assert "<fill" not in text.lower(), "Replace every <fill ...> in the report"
    assert RUNS.exists(), "Run both pipelines in the Compare tab first"
    runs = json.loads(RUNS.read_text(encoding="utf-8"))
    by = {r["config"]: r for r in runs}
    assert set(by) >= set(agentic_cfgs()), "Run BOTH pipelines in the Compare tab"
    assert by["Agentic RAG (critic loop)"]["loop_rate"] > 0, "The loop never ran: finish TODO-1..3"
    assert by["Agentic RAG (critic loop)"]["multi_part_pass"] >= by["Single pass (Lab 3)"]["multi_part_pass"], \
        "The agentic run should not be worse on multi-part questions: check your TODOs"


def agentic_cfgs():
    import eval_agentic
    return eval_agentic.CONFIGS
