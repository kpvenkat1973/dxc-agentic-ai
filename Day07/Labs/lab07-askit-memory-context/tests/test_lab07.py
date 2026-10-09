"""Lab 7 auto-checks. Run from the lab folder:   python check.py 7a   (or 7b, 7c, all)
No AWS or OpenAI key needed: the tests use a pretend model that gives scripted answers.
The "I completed Lab X" buttons on the session page run these same tests."""
import re
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LAB))

import json                                                                        # noqa: E402
from langchain_core.language_models.chat_models import BaseChatModel              # noqa: E402
from langchain_core.messages import AIMessage, AIMessageChunk                     # noqa: E402
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult  # noqa: E402
from langgraph.store.memory import InMemoryStore                                  # noqa: E402

import agent7                                                                      # noqa: E402

NOTES = LAB / "submission" / "lab07_notes.md"


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
        if reply.tool_calls:
            call = dict(reply.tool_calls[0], id=f"call{self.calls}")
            reply = AIMessage(content="", tool_calls=[call])
        return reply

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        return ChatResult(generations=[ChatGeneration(message=self._next(messages))])

    def _stream(self, messages, stop=None, run_manager=None, **kwargs):
        reply = self._next(messages)
        yield ChatGenerationChunk(message=AIMessageChunk(content=reply.content))


def wants(name, args):
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": "x", "type": "tool_call"}])


def says(text):
    return AIMessage(content=text)


def notes_section(prefix):
    assert NOTES.exists(), "submission\\lab07_notes.md is missing"
    parts = re.split(r"^## ", NOTES.read_text(encoding="utf-8"), flags=re.M)
    section = next((p for p in parts if p.startswith(prefix)), None)
    assert section is not None, f"Section '## {prefix}' not found in lab07_notes.md"
    return section


LONG_QUESTION = "Ticket TKT-0004 is mine and it is still not working for me, please check it again. " * 25   # about 2,000 tokens


# ================= LAB 7A  (TODO-1: bar) =================
def test_7a_1_bar():
    assert agent7.bar(1200) == "██", "TODO-1 is not done yet: bar() returns nothing. Write the one line (hint in lab07_hints.md)."
    assert agent7.bar(4100) == "████████", "one block for every 500 tokens"
    assert agent7.bar(100) == "█", "always show at least one block"


def test_7a_2_meter_logs_each_step():                                            # built
    agent7.reset_log()
    model = ScriptedModel(script=[says("First answer."), says("Second answer.")])
    agent = agent7.build_agent7(model, agent7.make_tools(), [agent7.context_meter])
    agent7.chat(agent, "t7a", ["Hi", "Hello again"])
    assert len(agent7.CONTEXT_LOG) == 2, "one entry per model call"
    assert agent7.CONTEXT_LOG[1] > agent7.CONTEXT_LOG[0], "the second call must be bigger: the chat is sent again"


def test_7a_notes():
    assert "<fill" not in notes_section("Lab 7A"), "NOTES ONLY, your code is fine: open submission\\lab07_notes.md, replace the <fill> in the Lab 7A line, save (Ctrl+S), run the check again."


# ================= LAB 7B  (TODO-2: compaction_middleware) =================
def test_7b_1_compaction_line():
    mw = agent7.compaction_middleware(ScriptedModel(script=[says("x")]))
    assert mw is not None, "TODO-2 is not done yet: compaction_middleware returns None. Write the SummarizationMiddleware(...) line (hint in lab07_hints.md)."


def test_7b_2_compaction_shrinks_the_chat():                                    # needs TODO-2
    agent7.reset_log()
    model = ScriptedModel(script=[says("Summary: the user has a VPN ticket.")])
    middleware = [agent7.compaction_middleware(model), agent7.context_meter]
    agent = agent7.build_agent7(model, agent7.make_tools(), middleware)
    agent7.chat(agent, "t7b", [LONG_QUESTION] * 4)
    sizes = agent7.CONTEXT_LOG
    assert any(sizes[i + 1] < sizes[i] for i in range(len(sizes) - 1)), \
        f"the chat should shrink after a summary; sizes were {sizes}"


def test_7b_notes():
    assert "<fill" not in notes_section("Lab 7B"), "NOTES ONLY, your code is fine: open submission\\lab07_notes.md, replace the <fill> in the Lab 7B line, save (Ctrl+S), run the check again."


# ================= LAB 7C  (TODO-3: remember) =================
def test_7c_1_remember():
    store = InMemoryStore()
    agent7.remember(store, "priya", "Laptop is a Dell")
    notes = agent7.recall(store, "priya")
    assert notes == ["Laptop is a Dell"], "TODO-3 is not done yet: remember() saves nothing. Write the store.put(...) line (hint in lab07_hints.md)."


def test_7c_2_recall_in_a_new_chat():                                           # needs TODO-3
    store = InMemoryStore()
    tools = agent7.make_memory_tools(store, "priya")
    m1 = ScriptedModel(script=[wants("save_note", {"text": "Laptop is a Dell"}), says("Saved.")])
    agent7.chat(agent7.build_agent7(m1, tools, store=store, system_prompt=agent7.SYSTEM_PROMPT_WITH_MEMORY), "chat-1",
                ["My laptop is a Dell. Remember it."])
    m2 = ScriptedModel(script=[wants("recall_notes", {}), says("You have a Dell.")])
    agent7.chat(agent7.build_agent7(m2, tools, store=store, system_prompt=agent7.SYSTEM_PROMPT_WITH_MEMORY), "chat-2",
                ["Which laptop do I have?"])
    assert "Laptop is a Dell" in agent7.recall(store, "priya"), "the note must be in the store"
    assert "Laptop is a Dell" in " ".join(str(c) for c in m2.seen[-1]), \
        "the second chat must receive the saved note from recall_notes"


def test_7c_notes():
    assert "<fill" not in notes_section("Lab 7C"), "NOTES ONLY, your code is fine: open submission\\lab07_notes.md, replace the <fill> in the Lab 7C line, save (Ctrl+S), run the check again."
