"""Lab 6 auto-checks. Run from the lab folder:   python check.py 6a   (or 6b, 6c, stretch, all)
No AWS or OpenAI key needed: the tests use a pretend model that gives scripted answers.
The "I completed Lab X" buttons on the session page run these same tests."""
import re
import sys
from pathlib import Path
from types import SimpleNamespace

LAB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LAB))

from langchain_core.language_models.chat_models import BaseChatModel          # noqa: E402
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, ToolMessage   # noqa: E402
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult   # noqa: E402
import json                                                                    # noqa: E402

import agent6                                                                  # noqa: E402

NOTES = LAB / "submission" / "lab06_notes.md"


# ---------- helpers: a pretend model that replies from a script ----------
class ScriptedModel(BaseChatModel):
    """Gives the prepared replies one by one (the last one repeats) and remembers what it was shown."""
    script: list = []
    calls: int = 0
    seen: list = []

    @property
    def _llm_type(self):
        return "scripted"

    def bind_tools(self, tools, **kwargs):
        return self

    def _next(self, messages):
        self.seen.append([m.content for m in messages])
        reply = self.script[min(self.calls, len(self.script) - 1)]
        self.calls += 1
        if reply.tool_calls:                         # give every tool request a fresh unique id
            call = dict(reply.tool_calls[0], id=f"call{self.calls}")
            reply = AIMessage(content="", tool_calls=[call])
        return reply

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        return ChatResult(generations=[ChatGeneration(message=self._next(messages))])

    def _stream(self, messages, stop=None, run_manager=None, **kwargs):
        reply = self._next(messages)
        if reply.tool_calls:
            yield ChatGenerationChunk(message=AIMessageChunk(content="", tool_call_chunks=[
                {"name": t["name"], "args": json.dumps(t["args"]), "id": t["id"], "index": 0} for t in reply.tool_calls]))
        else:
            for word in reply.content.split(" "):
                yield ChatGenerationChunk(message=AIMessageChunk(content=word + " "))


def wants(name, args):
    """A model reply that asks for a tool."""
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": "x", "type": "tool_call"}])


def says(text):
    return AIMessage(content=text)


def agent_with(model, middleware=None):
    return agent6.build_agent(model, agent6.make_tools(), middleware)


def notes_section(prefix):
    assert NOTES.exists(), "submission\\lab06_notes.md is missing"
    parts = re.split(r"^## ", NOTES.read_text(encoding="utf-8"), flags=re.M)
    section = next((p for p in parts if p.startswith(prefix)), None)
    assert section is not None, f"Section '## {prefix}' not found in lab06_notes.md"
    return section


# ================= LAB 6A  (TODO-1: build_agent) =================
def test_6a_1_build_agent():
    agent = agent_with(ScriptedModel(script=[says("Hello!")]))
    assert agent is not None, "TODO-1 is not done yet: build_agent still returns None. Write the create_agent(...) line (hint in lab06_hints.md)."
    out = agent.invoke({"messages": [{"role": "user", "content": "hi"}]})
    assert out["messages"][-1].content == "Hello!"


def test_6a_2_make_tools():                                                    # built
    tools = agent6.make_tools()
    assert [t.name for t in tools] == ["search_kb", "get_ticket", "update_ticket", "reset_password"]
    assert tools[1].invoke({"ticket_id": "TKT-0004"})["subject"] == "VPN not connecting"


def test_6a_3_ask():                                                           # built, needs TODO-1
    model = ScriptedModel(script=[wants("get_ticket", {"ticket_id": "TKT-0004"}), says("It is open.")])
    out = agent6.ask(agent_with(model), "Status of TKT-0004?")
    assert out["answer"] == "It is open."
    assert out["tools_used"] == ["get_ticket"]
    assert len(out["messages"]) == 4, "messages: question, tool request, tool result, answer"


def test_6a_notes():
    assert "<fill" not in notes_section("Lab 6A"), "NOTES ONLY, your code is fine: open submission\\lab06_notes.md, replace the <fill> in the Lab 6A line, save (Ctrl+S), run the check again."


# ================= LAB 6B  (TODO-2: over_budget) =================
def test_6b_1_over_budget():
    assert agent6.over_budget(6, 6) is True, "TODO-2: over_budget must be True when model_calls has reached max_calls"
    assert agent6.over_budget(7, 6) is True
    assert agent6.over_budget(2, 6) is False


def test_6b_2_budget_stops_agent():                                            # needs TODO-2
    model = ScriptedModel(script=[wants("get_ticket", {"ticket_id": "TKT-0001"})])   # asks for a tool forever
    out = agent_with(model, [agent6.budget_guard]).invoke({"messages": [{"role": "user", "content": "go on"}]})
    assert model.calls == agent6.MAX_MODEL_CALLS, "the agent must stop after MAX_MODEL_CALLS model calls"
    assert "human" in out["messages"][-1].content.lower()


def test_6b_3_pii_hidden():                                                    # built
    r = agent6.redact_pii
    out = r("Mail aarav.sharma@orbitcorp.example or call +91 98765 43210 about TKT-0044 for EMP-1001.")
    assert "@" not in out and "[EMAIL]" in out
    assert "98765" not in out and "[PHONE]" in out
    assert "TKT-0044" in out and "EMP-1001" in out, "ticket and employee ids must stay"
    assert r("Created 2026-09-14 08:00 on TKT-0004") == "Created 2026-09-14 08:00 on TKT-0004", "dates are not phone numbers"


def test_6b_4_model_never_sees_pii():                                          # built
    model = ScriptedModel(script=[says("ok")])
    agent_with(model, [agent6.pii_guard]).invoke(
        {"messages": [{"role": "user", "content": "Call me on 9876543210 or mail me@orbitcorp.example"}]})
    seen = " ".join(str(c) for c in model.seen[0])
    assert "9876543210" not in seen and "me@orbitcorp.example" not in seen, "the model was shown personal data"


def test_6b_5_tool_guard():                                                    # built
    request = SimpleNamespace(tool_call={"id": "abc", "name": "get_ticket"})
    ok = agent6.tool_guard.wrap_tool_call(request, lambda r: "fine")
    assert ok == "fine"

    def broken(r):
        raise RuntimeError("database down")
    bad = agent6.tool_guard.wrap_tool_call(request, broken)
    assert isinstance(bad, ToolMessage) and bad.tool_call_id == "abc" and "database down" in bad.content


def test_6b_6_agent_survives_crash():                                          # built
    import os
    os.environ["ASKIT_TOOLS_DOWN"] = "1"                       # the ticket database is "down"
    try:
        model = ScriptedModel(script=[wants("get_ticket", {"ticket_id": "TKT-0004"}), says("Sorry, the ticket system is down.")])
        out = agent6.ask(agent_with(model, [agent6.tool_guard]), "Status of TKT-0004?")
        assert "down" in out["answer"].lower(), "with tool_guard the agent must still answer"
    finally:
        os.environ.pop("ASKIT_TOOLS_DOWN", None)


def test_6b_notes():
    assert "<fill" not in notes_section("Lab 6B"), "NOTES ONLY, your code is fine: open submission\\lab06_notes.md, replace the <fill> in the Lab 6B line, save (Ctrl+S), run the check again."


# ================= LAB 6C  (TODO-3: the final answer line in describe_step) =================
def test_6c_1_final_answer_line():
    final = agent6.describe_step({"model": {"messages": [says("It is open.")]}})
    assert len(final) == 1, "TODO-3 is not done yet: describe_step gives no line for the final answer. Replace 'pass' (hint in lab06_hints.md)."
    assert "answer" in final[0] and "It is open." in final[0]


def test_6c_2_other_steps():                                                   # built
    d = agent6.describe_step
    ask_tool = d({"model": {"messages": [wants("get_ticket", {"ticket_id": "TKT-0004"})]}})
    assert len(ask_tool) == 1 and "get_ticket" in ask_tool[0] and "asks for" in ask_tool[0]
    result = d({"tools": {"messages": [ToolMessage(content='{"status": "Open"}', tool_call_id="x")]}})
    assert len(result) == 1 and "Open" in result[0] and "result" in result[0]
    assert d({"some_guard.before_model": None}) == [], "an update without data gives no lines"
    assert d({"x": {"messages": [HumanMessage(content="hi")]}}) == [], "human messages are skipped"


def test_6c_3_stream_answer():                                                 # built, needs TODO-3
    model = ScriptedModel(script=[wants("get_ticket", {"ticket_id": "TKT-0004"}), says("It is open.")])
    lines = agent6.stream_answer(agent_with(model), "Status of TKT-0004?")
    assert len(lines) == 3, "expected: the tool request, the tool result, the answer"
    assert "asks for" in lines[0] and "result" in lines[1] and "answer" in lines[2]


def test_6c_notes():
    assert "<fill" not in notes_section("Lab 6C"), "NOTES ONLY, your code is fine: open submission\\lab06_notes.md, replace the <fill> in the Lab 6C line, save (Ctrl+S), run the check again."


# ================= STRETCH (optional) =================
def test_stretch_c_stream_tokens():
    model = ScriptedModel(script=[says("It is open right now.")])
    pieces = agent6.stream_tokens(agent_with(model), "hi")
    if not pieces:
        import pytest
        pytest.skip("Stretch C is optional and not written yet")
    assert len(pieces) >= 4, "the answer should arrive in several small pieces"
    assert "".join(pieces).strip() == "It is open right now."
