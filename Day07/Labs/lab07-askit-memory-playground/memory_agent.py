"""memory_agent.py  --  the AskIT agent behind the Memory Playground.   (read it, you do not need to edit it)

WHO DOES WHAT
  app.py            the screen (Streamlit): chat box, sliders, charts. It calls build_agent() and ask().
  memory_agent.py   THIS FILE: builds the agent and its three memory pieces.
  model_factory.py  picks the model: Bedrock (main) -> Azure -> OpenAI -> Offline.
  askit_core/tools.py  the 4 helpdesk tools from Day 5 (search_kb, get_ticket, update_ticket, reset_password).

THE THREE MEMORY PIECES
  1. Checkpointer (InMemorySaver)  = SHORT-TERM memory. Keeps the messages of ONE chat (one thread_id).
  2. SummarizationMiddleware       = COMPACTION. When the chat gets big, old messages become one short summary.
  3. Store (InMemoryStore)         = LONG-TERM memory. Notes about a user that survive a NEW chat.
"""
import json
import time
import uuid

from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware, SummarizationMiddleware
from langchain.tools import tool
from langchain_core.messages.utils import count_tokens_approximately

import model_factory
from askit_core.tools import get_ticket, reset_password, search_kb, update_ticket

SUMMARY_MARK = "Here is a summary of the conversation to date"

SYSTEM_PROMPT = """You are AskIT, the IT helpdesk assistant of Orbit Corp.
Rules:
1. For how-to questions, call search_kb and answer ONLY from what it returns. Cite the article id, like [KB-004].
2. For a question about a ticket, call get_ticket.
3. Use update_ticket or reset_password ONLY when the user clearly asks for that action.
4. If the user asks about something said earlier in THIS chat, answer from the chat. Do not call a tool for that.
5. Reply in 2-3 short sentences."""

MEMORY_RULES = """
6. If the user tells you a lasting fact about themselves (laptop model, location, team), call save_note with that fact.
7. If the user asks about themselves or something from an earlier chat, call recall_notes first."""

# The scripted chat used by the "Play" and "Compare" buttons. Line 1 holds a detail we ask for again at the end.
SCRIPT = [
    "Hi, I am Priya, employee id EMP-1002. My ticket TKT-0004 is still open. What is its status?",
    "How do I connect to the VPN from home?",
    "The VPN shows error 809. What should I try?",
    "Also, what is the status of ticket TKT-0046?",
    "How do I set up MFA on my new phone?",
    "My laptop battery looks swollen. What should I do?",
    "Which ticket did I ask about first?",
    "What is my employee id?",
]


# ------------------------------------------------------------------------------------------------ the context meter
class ContextMeter(AgentMiddleware):
    """Runs around EVERY model call and writes one row: how many tokens went in, how many came out, was a summary present.
    This is how the app draws the bars. In production the same numbers come from Langfuse / CloudWatch (Day 10)."""

    def __init__(self, log):
        super().__init__()
        self.log = log            # a list owned by app.py
        self.turn = 0             # which user question we are on

    def before_model(self, state, runtime):
        msgs = state["messages"]
        summary = next((model_factory.text_of(m) for m in msgs if SUMMARY_MARK in model_factory.text_of(m)), "")
        self._pending = {"turn": self.turn, "messages": len(msgs), "approx_in": count_tokens_approximately(msgs),
                         "summary": summary, "t0": time.time()}
        return None

    def after_model(self, state, runtime):
        last = state["messages"][-1]
        use = getattr(last, "usage_metadata", None) or {}
        row = dict(self._pending)
        row["in_tokens"] = use.get("input_tokens") or row["approx_in"]
        row["out_tokens"] = use.get("output_tokens") or model_factory.approx_tokens(model_factory.text_of(last) or "x")
        row["tools"] = [t["name"] for t in getattr(last, "tool_calls", [])]
        row["seconds"] = round(time.time() - row.pop("t0"), 2)
        row["step"] = len(self.log) + 1
        self.log.append(row)
        return None


# ------------------------------------------------------------------------------------------------ long-term memory tools
def make_memory_tools(store, user_id):
    """Two tools that read/write the long-term store. Notes live under the namespace ("memories", user_id)."""

    @tool
    def save_note(text: str) -> str:
        """Save one short, lasting fact about the user (e.g. 'Laptop: Dell XPS 13') so a later chat can recall it."""
        store.put(("memories", user_id), uuid.uuid4().hex, {"text": text, "saved_at": time.strftime("%H:%M:%S")})
        return "Saved."

    @tool
    def recall_notes() -> str:
        """Return the facts saved about this user in earlier chats."""
        return json.dumps([i.value["text"] for i in store.search(("memories", user_id))])

    return [save_note, recall_notes]


def notes(store, user_id):
    return [{"note": i.value["text"], "saved at": i.value.get("saved_at", "")} for i in store.search(("memories", user_id))]


def forget_user(store, user_id):
    """'Right to be forgotten': delete every note for this user."""
    for i in store.search(("memories", user_id)):
        store.delete(("memories", user_id), i.key)


# ------------------------------------------------------------------------------------------------ build + ask
def build_agent(model, checkpointer, log, compaction=False, compact_at=1500, keep_last=4,
                memory=False, store=None, user_id="EMP-1002"):
    """Builds the agent. The SAME checkpointer is passed in every time, so changing a setting keeps the chat.
    Returns (agent, meter)."""
    tools = [tool(search_kb), tool(get_ticket), tool(update_ticket), tool(reset_password)]
    prompt = SYSTEM_PROMPT
    if memory:
        tools += make_memory_tools(store, user_id)
        prompt += MEMORY_RULES
    meter = ContextMeter(log)
    middleware = []
    if compaction:                                                         # piece 2: compaction
        middleware.append(SummarizationMiddleware(model=model, trigger=("tokens", compact_at),
                                                  keep=("messages", keep_last)))
    middleware.append(meter)                                               # last: measures what really goes in
    agent = create_agent(model=model, tools=tools, system_prompt=prompt, middleware=middleware,
                         checkpointer=checkpointer,                        # piece 1: short-term memory
                         store=store if memory else None)                  # piece 3: long-term memory
    return agent, meter


def ask(agent, meter, thread_id, question, turn=0):
    """Send one user message into a chat thread. Returns the answer text."""
    meter.turn = turn
    out = agent.invoke({"messages": [{"role": "user", "content": question}]}, {"configurable": {"thread_id": thread_id}})
    return model_factory.text_of(out["messages"][-1])


def chat_messages(agent, thread_id):
    """The messages currently kept in this chat thread (what the checkpointer holds)."""
    snap = agent.get_state({"configurable": {"thread_id": thread_id}})
    return snap.values.get("messages", []) if snap and snap.values else []
