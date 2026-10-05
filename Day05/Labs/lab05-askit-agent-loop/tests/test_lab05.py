"""Lab 5 auto-checks - one test per TODO. Run from the lab folder:   pytest tests
No AWS or OpenAI key needed: the tests use a pretend model that gives scripted answers.
The "I completed Lab X" buttons on the session page run these same tests."""
import re
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LAB))

import agent  # noqa: E402

NOTES = LAB / "submission" / "lab05_notes.md"


# ---------- helpers: a pretend model that replies from a script ----------
def tool_use(name, inp, tid="t1"):
    """A model reply that asks for a tool."""
    return {"output": {"message": {"role": "assistant", "content": [{"toolUse": {"toolUseId": tid, "name": name, "input": inp}}]}},
            "stopReason": "tool_use", "usage": {"inputTokens": 10, "outputTokens": 5}}


def text(t):
    """A model reply with a final answer."""
    return {"output": {"message": {"role": "assistant", "content": [{"text": t}]}},
            "stopReason": "end_turn", "usage": {"inputTokens": 10, "outputTokens": 5}}


class ScriptedModel:
    """Gives the prepared replies one by one (the last one repeats forever) and counts the calls."""

    def __init__(self, *replies):
        self.replies, self.calls = list(replies), 0

    def __call__(self, messages):
        self.calls += 1
        return self.replies[min(self.calls - 1, len(self.replies) - 1)]


def notes_section(prefix):
    """Return the text of one '## ...' section of submission/lab05_notes.md."""
    assert NOTES.exists(), "submission\\lab05_notes.md is missing"
    parts = re.split(r"^## ", NOTES.read_text(encoding="utf-8"), flags=re.M)
    section = next((p for p in parts if p.startswith(prefix)), None)
    assert section is not None, f"Section '## {prefix}' not found in lab05_notes.md"
    return section


# ================= LAB 5A =================
def test_challenge_1_run_tool():
    out = agent.run_tool("get_ticket", {"ticket_id": "TKT-0004"})
    assert out.get("subject") == "VPN not connecting", "run_tool should call the real tool and return its result"
    assert "error" in agent.run_tool("make_coffee", {}), "an unknown tool must return {'error': ...}, not crash"
    assert "Unknown" in agent.run_tool("make_coffee", {})["error"]
    assert "error" in agent.run_tool("get_ticket", {"wrong_name": 1}), "bad inputs must return {'error': ...}, not crash"


def test_challenge_2_get_tool_requests():
    one = agent.get_tool_requests(tool_use("get_ticket", {"ticket_id": "TKT-0004"}, "abc"))
    assert one == [{"id": "abc", "name": "get_ticket", "input": {"ticket_id": "TKT-0004"}}]
    assert agent.get_tool_requests(text("All done")) == [], "a plain answer has no tool requests: return []"
    two = tool_use("search_kb", {"query": "vpn"}, "a")
    two["output"]["message"]["content"].append({"toolUse": {"toolUseId": "b", "name": "get_ticket", "input": {"ticket_id": "TKT-0001"}}})
    assert [r["id"] for r in agent.get_tool_requests(two)] == ["a", "b"], "return ALL tool requests, in order"


def test_challenge_3_make_tool_result():
    block = agent.make_tool_result("abc", {"status": "Open"})
    assert block == {"toolResult": {"toolUseId": "abc", "content": [{"json": {"status": "Open"}}]}}


def test_challenge_3_notes():
    sec = notes_section("Lab 5A")
    assert "<fill" not in sec, "Fill in the Lab 5A lines in submission\\lab05_notes.md"


def test_stretch_a_get_user():
    out = agent.run_tool("get_user", {"user_id": "EMP-1002"})
    assert out.get("name") == "Priya Iyer", "write get_user and remove the two # in front of the registration lines"
    assert "error" in agent.run_tool("get_user", {"user_id": "EMP-9999"})


# ================= LAB 5B =================
def test_challenge_4_final_answer():
    model = ScriptedModel(text("Hello! How can I help?"))
    res = agent.run_agent("hi", call_model=model)
    assert res["answer"] == "Hello! How can I help?", "when the model asks for no tool, its text is the answer"
    assert res["steps"] == 1 and model.calls == 1
    assert res["handoff"] is False


def test_challenge_5_tool_then_answer():
    model = ScriptedModel(tool_use("get_ticket", {"ticket_id": "TKT-0004"}, "t9"), text("It is open."))
    res = agent.run_agent("Status of TKT-0004?", call_model=model)
    assert res["answer"] == "It is open.", "after the tool result the model answers: the loop must go round again"
    assert res["steps"] == 2
    msgs = res["messages"]
    assert [m["role"] for m in msgs] == ["user", "assistant", "user"], "messages: question, tool request, tool result"
    result_block = msgs[2]["content"][0]["toolResult"]
    assert result_block["toolUseId"] == "t9", "the result must carry the model's toolUseId"
    assert result_block["content"][0]["json"]["subject"] == "VPN not connecting"


def test_challenge_6_step_limit():
    # a model that never stops asking for new tools (different ticket each time, so it is not a repeat)
    model = ScriptedModel(*[tool_use("get_ticket", {"ticket_id": f"TKT-000{i}"}, f"t{i}") for i in range(1, 9)])
    res = agent.run_agent("keep going", call_model=model, max_steps=3)
    assert model.calls == 3, "the agent must stop after max_steps model calls"
    assert res["handoff"] is True, "out of steps: hand over to a human with give_up(...)"
    assert "human" in res["answer"].lower()


def test_challenge_6_notes():
    assert "<fill" not in notes_section("Lab 5B"), "Fill in the Lab 5B lines in submission\\lab05_notes.md"


# ================= LAB 5C =================
def test_challenge_7_needs_approval():
    assert agent.needs_approval("update_ticket", {"ticket_id": "TKT-0004", "note": "x"}) is True
    assert agent.needs_approval("reset_password", {"user_id": "EMP-1021"}) is True
    assert agent.needs_approval("get_ticket", {"ticket_id": "TKT-0004"}) is False
    assert agent.needs_approval("search_kb", {"query": "vpn"}) is False


def test_challenge_8_run_tool_safely():
    no = agent.run_tool_safely("reset_password", {"user_id": "EMP-1021"}, approve=lambda n, a: False)
    assert "error" in no and "approve" in no["error"].lower(), "a refused action must return an error"
    yes = agent.run_tool_safely("reset_password", {"user_id": "EMP-1021"}, approve=lambda n, a: True)
    assert yes.get("ok") is True, "an approved action runs the tool"

    def must_not_ask(n, a):
        raise AssertionError("read-only tools must NOT ask for approval")
    assert "subject" in agent.run_tool_safely("get_ticket", {"ticket_id": "TKT-0004"}, approve=must_not_ask)


def test_challenge_8_notes():
    assert "<fill" not in notes_section("Lab 5C"), "Fill in the Lab 5C lines in submission\\lab05_notes.md"


def test_stretch_b_vip_block():
    assert agent.vip_block("reset_password", {"user_id": "EMP-1001"}) is True, "EMP-1001 is a VIP"
    assert agent.vip_block("reset_password", {"user_id": "EMP-1021"}) is False
    assert agent.vip_block("update_ticket", {"ticket_id": "TKT-0044", "note": "x"}) is True, "TKT-0044 belongs to a VIP"
    assert agent.vip_block("get_ticket", {"ticket_id": "TKT-0044"}) is False, "reading is allowed for VIPs"
    blocked = agent.run_tool_safely("reset_password", {"user_id": "EMP-1001"}, approve=lambda n, a: True)
    assert "error" in blocked, "even when a human approves, run_tool_safely must refuse VIP actions (KB-018)"


# ================= INCIDENT =================
def test_challenge_9_is_repeat():
    seen = [("get_ticket", {"ticket_id": "TKT-0004"})]
    assert agent.is_repeat(seen, "get_ticket", {"ticket_id": "TKT-0004"}) is True
    assert agent.is_repeat(seen, "get_ticket", {"ticket_id": "TKT-0005"}) is False, "different inputs are not a repeat"
    assert agent.is_repeat(seen, "search_kb", {"ticket_id": "TKT-0004"}) is False, "different tool is not a repeat"
    assert agent.is_repeat([], "get_ticket", {"ticket_id": "TKT-0004"}) is False


def test_challenge_9_loop_stops_early():
    model = ScriptedModel(tool_use("get_ticket", {"ticket_id": "TKT-0004"}))   # asks for the SAME call forever
    res = agent.run_agent("status of TKT-0004?", call_model=model, max_steps=6)
    assert res["handoff"] is True
    assert model.calls <= 2, "after the 2nd identical request the agent must stop (add the is_repeat check inside run_agent)"


def test_challenge_9_notes():
    assert "<fill" not in notes_section("Incident"), "Fill in the Incident lines in submission\\lab05_notes.md"
