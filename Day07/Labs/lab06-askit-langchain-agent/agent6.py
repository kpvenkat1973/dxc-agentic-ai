"""agent6.py  --  yesterday you wrote the agent loop by hand. Today LangChain gives you that loop, ready made.

Three small parts. Each part has ONE thing for you to write. It is marked TODO and it is ONE line:

    Lab 6A  TODO-1   build_agent     one line that creates the agent
    Lab 6B  TODO-2   over_budget     one comparison that stops a runaway agent
    Lab 6C  TODO-3   describe_step   one line that shows the final answer while it streams

Everything NOT marked TODO is already built. Read the comments, run it, change one value, see what happens.
Stuck? Full line:  Day06\\Hints\\lab06_hints.md   (search for TODO-1, TODO-2 or TODO-3)
"""
import json
import re
import sys
from pathlib import Path

# --- Make "askit_core" (the shared code two folders up) importable. Leave this block alone. ---
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from langchain.agents import create_agent                                   # noqa: E402  (builds the whole agent loop)
from langchain.agents.middleware import before_model, wrap_tool_call        # noqa: E402  (two kinds of middleware hooks)
from langchain.tools import tool                                            # noqa: E402  (turns a Python function into a tool)
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage    # noqa: E402  (the message types)

from askit_core.tools import get_ticket, reset_password, search_kb, update_ticket   # noqa: E402  (the 4 tools from Day 5)

SYSTEM_PROMPT = """You are AskIT, the IT helpdesk assistant of Orbit Corp.
Rules:
1. For how-to questions, call search_kb and answer ONLY from what it returns. Cite the article id, like [KB-004].
2. For a question about a ticket, call get_ticket.
3. Use update_ticket or reset_password ONLY when the user clearly asks for that action.
4. If a tool returns an error, tell the user in one sentence.
5. When you have the answer, reply in 2-3 short sentences."""


# =============================================================================================
# SMALL HELPERS (already built)
# =============================================================================================
def text_of(message):
    """The text of a LangChain message (content can be a string or a list of blocks)."""
    c = message.content
    if isinstance(c, str):
        return c
    return "".join(b.get("text", "") for b in c if isinstance(b, dict))


def short(value, limit=110):
    """Turn anything into a short one-line string for printing."""
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    return text if len(text) <= limit else text[:limit] + "..."


# =============================================================================================
# LAB 6A  -  BUILD THE AGENT WITH LANGCHAIN
# =============================================================================================
def make_tools():
    """(built) Wraps the 4 Day 5 functions as LangChain tools: search_kb, get_ticket, update_ticket, reset_password."""
    return [tool(search_kb), tool(get_ticket), tool(update_ticket), tool(reset_password)]


def build_agent(model, tools, middleware=None):
    """TODO-1 (Lab 6A): create the agent. ONE line to write.

    create_agent(...) builds the whole loop for you: think, act, observe, repeat.
    Replace the line  'return None'  with ONE line that calls create_agent with:
        model=model
        tools=tools
        system_prompt=SYSTEM_PROMPT
        middleware=middleware or []
    Use exactly these names. Then run:  python check.py 6a
    """
    return None  # TODO-1: replace this line with: return create_agent(...)


def ask(agent, question):
    """(built) Asks the agent one question and returns the answer, the tool names used, and the messages."""
    result = agent.invoke({"messages": [{"role": "user", "content": question}]})
    messages = result["messages"]
    answer = text_of(messages[-1])
    tools_used = [call["name"] for m in messages if isinstance(m, AIMessage) for call in m.tool_calls]
    return {"answer": answer, "tools_used": tools_used, "messages": messages}


# =============================================================================================
# LAB 6B  -  MIDDLEWARE: GUARDS AROUND THE MODEL AND THE TOOLS
# =============================================================================================
# Middleware = small functions LangChain calls at fixed moments:
#     before_model   ->  just BEFORE every model call   (look at, change or stop the conversation)
#     wrap_tool_call -> AROUND every tool call          (catch errors, log, block)
# You write the logic. LangChain decides WHEN it runs.

MAX_MODEL_CALLS = 6        # the maximum number of model calls before the guard stops the agent (same idea as Day 5)


def redact_pii(text):
    """(built) Replaces email addresses with [EMAIL] and phone numbers with [PHONE]. Ticket and employee ids stay."""
    text = re.sub(r"[\w.+-]+@[\w-]+\.[\w.-]+", "[EMAIL]", text)                         # name@company.com
    text = re.sub(r"(?<!\d)(\+?\d{2}[\s-]?)?\d{5}[\s-]?\d{5}(?!\d)", "[PHONE]", text)   # +91 98765 43210
    return text


def over_budget(model_calls, max_calls):
    """TODO-2 (Lab 6B): True when the agent has used up its model calls. ONE line to write.

    Ask: has model_calls reached max_calls?  Use >=  (greater than or equal).
    Replace the line  'return False'  with ONE comparison. Then run:  python check.py 6b
    """
    return False  # TODO-2: replace this line with one comparison


@before_model
def pii_guard(state, runtime):
    """(built) Runs BEFORE every model call. Replaces personal data in the user's messages with redact_pii()."""
    changed = []
    for m in state["messages"]:
        if isinstance(m, HumanMessage) and isinstance(m.content, str):
            clean = redact_pii(m.content)
            if clean != m.content:
                changed.append(HumanMessage(content=clean, id=m.id))     # same id = this REPLACES the old message
    return {"messages": changed} if changed else None                    # None = "nothing to change"


@before_model(can_jump_to=["end"])
def budget_guard(state, runtime):
    """(built) Runs BEFORE every model call. Every AIMessage so far = one model call already paid for."""
    calls = sum(1 for m in state["messages"] if isinstance(m, AIMessage))
    if over_budget(calls, MAX_MODEL_CALLS):
        # add a final message and jump straight to the end of the agent: no more model calls
        return {"messages": [AIMessage(content="I used up my step budget, so a human will take over.")], "jump_to": "end"}
    return None


@wrap_tool_call
def tool_guard(request, handler):
    """(built) Runs AROUND every tool call. If a tool crashes, the agent gets a short error message instead of crashing."""
    try:
        return handler(request)                                       # run the tool normally
    except Exception as e:                                            # the tool crashed (e.g. database down)
        return ToolMessage(content=f"Tool failed: {e}. Tell the user a human will follow up.",
                           tool_call_id=request.tool_call["id"])      # the model gets an error it can explain


GUARDS = [pii_guard, budget_guard, tool_guard]      # the three guards together. Passed to build_agent in Lab 6B.


# =============================================================================================
# LAB 6C  -  STREAMING: SEE EACH STEP AS IT HAPPENS
# =============================================================================================
def describe_step(update):
    """Turns ONE streamed update into printable lines (a list of strings).

    One TODO here: the final answer line (TODO-3). Everything else is built.
    """
    lines = []
    for data in update.values():
        if not isinstance(data, dict):                                  # some steps carry no data
            continue
        for m in data.get("messages", []):
            if isinstance(m, AIMessage) and m.tool_calls:               # the model asks for a tool
                for call in m.tool_calls:
                    lines.append(f"🔧 asks for {call['name']}({short(call['args'])})")
            elif isinstance(m, AIMessage):
                # TODO-3 (Lab 6C): the final answer. ONE line to write.
                # Replace the word 'pass' with:  lines.append(f"✅ answer: {text_of(m)}")
                pass  # TODO-3
            elif isinstance(m, ToolMessage):                            # a tool result came back
                lines.append(f"👁️ result: {short(text_of(m))}")
    return lines


def stream_answer(agent, question):
    """(built) Asks the agent a question and prints every step AS IT HAPPENS. Returns the printed lines."""
    printed = []
    for update in agent.stream({"messages": [{"role": "user", "content": question}]}, stream_mode="updates"):
        for line in describe_step(update):          # one update can hold several lines
            print(line, flush=True)                 # show it NOW, not at the end
            printed.append(line)
    return printed


def stream_tokens(agent, question):
    """STRETCH-C (optional): stream the answer WORD BY WORD. Returns the list of text pieces.

    for chunk, meta in agent.stream({...same input...}, stream_mode="messages"):
        chunk = a small piece of a message;  meta["langgraph_node"] says where it came from.
        Keep only pieces from the "model" node that have text (text_of(chunk) is not empty):
        print(piece, end="", flush=True) and add it to the list.
    """
    return []
