"""agent6.py  --  yesterday you wrote the agent loop by hand. Today LangChain gives you that loop, ready made.

You will build AskIT again, in 3 steps. Each step is one lab:

    Lab 6A  TODO-1, 2, 3   build the agent with LangChain  (about 10 lines instead of 100)
    Lab 6B  TODO-4, 5, 6   add MIDDLEWARE: small guards that run around the model and the tools
    Lab 6C  TODO-7, 8      STREAMING: watch the agent work step by step instead of waiting

Everything NOT marked TODO is already built. Read the comments: they explain each line.
Hints and full answers:  Day06\\Hints\\lab06_hints.md

Compare with Day 5:    your loop (while / for)        ->  create_agent(...)
                       your run_tool + TOOLS dict      ->  LangChain "tools"
                       your give_up / is_repeat checks ->  middleware
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
    """TODO-1: turn the 4 plain Python functions into LangChain tools.

    The functions are already imported at the top: search_kb, get_ticket, update_ticket, reset_password.
    tool(some_function) wraps one function. LangChain reads the function's name, its docstring (= the description
    the model sees) and its inputs. Return the 4 tools in a list, in that order.
    """
    return []


def build_agent(model, tools, middleware=None):
    """TODO-2: create the agent. create_agent builds the whole loop (think, act, observe, repeat) for you.

    Call create_agent with these named inputs:
        model=model              the chat model
        tools=tools              the list from make_tools()
        system_prompt=SYSTEM_PROMPT
        middleware=middleware or []      (the guards you add in Lab 6B; an empty list for now)
    and return what it gives back.
    """
    return None


def ask(agent, question):
    """TODO-3: ask the agent one question and return a dict:
         {"answer": <the final text>, "tools_used": [<tool names, in order>], "messages": <all messages>}

    How: result = agent.invoke({"messages": [{"role": "user", "content": question}]})
         result["messages"] is the whole conversation (a list of messages).
         - the LAST message is the final answer  -> use text_of(...)
         - every AIMessage has .tool_calls, a list of dicts with a "name" -> collect all the names
    """
    return {"answer": "", "tools_used": [], "messages": []}


# =============================================================================================
# LAB 6B  -  MIDDLEWARE: GUARDS AROUND THE MODEL AND THE TOOLS
# =============================================================================================
# Middleware = small functions LangChain calls at fixed moments:
#     before_model  ->  just BEFORE every model call   (look at, change or stop the conversation)
#     wrap_tool_call -> AROUND every tool call          (catch errors, log, block)
# You write the logic. LangChain decides WHEN it runs.

MAX_MODEL_CALLS = 6        # the same limit as Day 5's MAX_STEPS


def redact_pii(text):
    """TODO-4: hide personal data BEFORE the model sees it.

    Replace every email address with [EMAIL] and every phone number with [PHONE]. Use re.sub twice.
    Email pattern : r"[\\w.+-]+@[\\w-]+\\.[\\w.-]+"
    Phone pattern : r"(?<!\\d)(\\+?\\d{2}[\\s-]?)?\\d{5}[\\s-]?\\d{5}(?!\\d)"      (10 digits, optional +91 in front)
    Ticket ids like TKT-0004 and employee ids like EMP-1021 must stay untouched.
    """
    return text


def over_budget(model_calls, max_calls):
    """TODO-5: True when the agent has used up its model calls (model_calls has reached max_calls)."""
    return False


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
    """TODO-6: wrap every tool call so a crashing tool does not crash the agent.

    request = the tool call (request.tool_call is a dict with "id" and "name")
    handler(request) = actually runs the tool and returns its result (a ToolMessage)

    Do this:  try to return handler(request).
              If it raises any Exception e, return a ToolMessage instead:
                  ToolMessage(content=f"Tool failed: {e}. Tell the user a human will follow up.",
                              tool_call_id=request.tool_call["id"])
    (Day 5 did the same inside run_tool.)
    """
    return handler(request)


GUARDS = [pii_guard, budget_guard, tool_guard]      # the three guards together. Pass this list to build_agent in Lab 6B.


# =============================================================================================
# LAB 6C  -  STREAMING: SEE EACH STEP AS IT HAPPENS
# =============================================================================================
def describe_step(update):
    """TODO-7: turn ONE streamed update into printable lines (a list of strings).

    agent.stream(..., stream_mode="updates") gives one update per step, shaped like:
         {"model": {"messages": [AIMessage]}}   or   {"tools": {"messages": [ToolMessage]}}
    For each message inside (use update.values(), then data["messages"]):
         an AIMessage WITH tool_calls  -> for each call: f"🔧 asks for {call['name']}({short(call['args'])})"
         an AIMessage without tool_calls -> f"✅ answer: {text_of(m)}"
         a ToolMessage                 -> f"👁️ result: {short(text_of(m))}"
         anything else (e.g. HumanMessage) -> skip
    Some updates have data = None: skip those.
    """
    return []


def stream_answer(agent, question):
    """TODO-8: ask the agent a question and print every step AS IT HAPPENS. Return the list of printed lines.

    for update in agent.stream({"messages": [{"role": "user", "content": question}]}, stream_mode="updates"):
        ...use describe_step(update); print each line and keep it in a list...
    """
    return []


def stream_tokens(agent, question):
    """STRETCH-C: stream the answer WORD BY WORD. Return the list of text pieces.

    for chunk, meta in agent.stream({...same input...}, stream_mode="messages"):
        chunk = a small piece of a message;  meta["langgraph_node"] says where it came from.
        Keep only pieces from the "model" node that have text (text_of(chunk) is not empty):
        print(piece, end="", flush=True) and add it to the list.
    """
    return []
