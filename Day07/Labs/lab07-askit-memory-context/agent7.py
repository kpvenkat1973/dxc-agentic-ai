"""agent7.py  --  the AskIT agent remembers more, and it costs more when it remembers everything.

Three small parts. Each part has ONE thing for you to write. It is marked TODO and it is ONE line:

    Lab 7A  TODO-1   bar()                  one line that draws the context-size bar
    Lab 7B  TODO-2   compaction_middleware  one line that makes the agent SUMMARISE old messages
    Lab 7C  TODO-3   remember()             one line that saves a note in the long-term store

Everything NOT marked TODO is already built. Read the comments, run it, change one value, see what happens.
Stuck? Full line:  Day07\\Hints\\lab07_hints.md   (search for TODO-1, TODO-2 or TODO-3)
"""
import json
import sys
import uuid
from pathlib import Path

# --- Make "askit_core" (the shared code two folders up) importable. Leave this block alone. ---
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from langchain.agents import create_agent                                   # noqa: E402  (builds the agent loop)
from langchain.agents.middleware import SummarizationMiddleware, before_model   # noqa: E402  (summary + middleware hook)
from langchain.tools import tool                                            # noqa: E402  (turns a function into a tool)
from langchain_core.messages import AIMessage, HumanMessage                 # noqa: E402  (message types)
from langchain_core.messages.utils import count_tokens_approximately        # noqa: E402  (rough token counter: about characters / 4)
from langgraph.checkpoint.memory import InMemorySaver                       # noqa: E402  (remembers each chat thread)
from langgraph.store.memory import InMemoryStore                            # noqa: E402  (long-term notes, kept across threads)

from askit_core.tools import get_ticket, reset_password, search_kb, update_ticket   # noqa: E402  (the 4 tools from Day 5)

SYSTEM_PROMPT = """You are AskIT, the IT helpdesk assistant of Orbit Corp.
Rules:
1. For how-to questions, call search_kb and answer ONLY from what it returns. Cite the article id, like [KB-004].
2. For a question about a ticket, call get_ticket.
3. Use update_ticket or reset_password ONLY when the user clearly asks for that action.
4. If a tool returns an error, tell the user in one sentence.
5. When you have the answer, reply in 2-3 short sentences."""

SYSTEM_PROMPT_WITH_MEMORY = SYSTEM_PROMPT + """
6. If the user tells you a fact about themselves (for example their laptop), call save_note with it.
7. If the user asks about something from an earlier chat, call recall_notes first."""


# =============================================================================================
# SMALL HELPERS (already built)
# =============================================================================================
def text_of(message):
    """The text of a LangChain message (content can be a string or a list of blocks)."""
    c = message.content
    if isinstance(c, str):
        return c
    return "".join(b.get("text", "") for b in c if isinstance(b, dict))


def make_tools():
    """(built) The 4 Day 5 tools, wrapped for LangChain."""
    return [tool(search_kb), tool(get_ticket), tool(update_ticket), tool(reset_password)]


def build_agent7(model, tools, middleware=None, store=None, system_prompt=SYSTEM_PROMPT):
    """(built) The agent with a memory of each chat thread (InMemorySaver) and an optional long-term store.
    None entries in middleware are ignored, so a part you have not finished yet does not break the agent."""
    active = [m for m in (middleware or []) if m is not None]
    return create_agent(model=model, tools=tools, system_prompt=system_prompt, middleware=active,
                        checkpointer=InMemorySaver(), store=store)


def chat(agent, thread_id, questions):
    """(built) Asks several questions in ONE chat thread. The agent remembers the earlier questions in that thread."""
    config = {"configurable": {"thread_id": thread_id}}
    answers = []
    for q in questions:
        out = agent.invoke({"messages": [{"role": "user", "content": q}]}, config)
        answers.append(text_of(out["messages"][-1]))
    return answers


# =============================================================================================
# LAB 7A  -  LOG THE CONTEXT SIZE AT EVERY STEP
# =============================================================================================
# The "context" is everything the model is sent at each step: the system prompt, the chat so far, tool results.
# It is measured in tokens (roughly characters divided by 4 here). More context = more cost and slower answers.

CONTEXT_LOG = []      # one number per model call: the size of what the model was sent


def reset_log():
    """(built) Clears the log before a new run."""
    CONTEXT_LOG.clear()


def total_input_tokens():
    """(built) Adds up everything the model was sent during the run. Less = cheaper."""
    return sum(CONTEXT_LOG)


def bar(tokens, tokens_per_block=500):
    """TODO-1 (Lab 7A): draw the bar. ONE line to write.

    One block (the character █) for every 500 tokens. Show at least ONE block, even for small numbers.
    Replace the line  'return ""'  with ONE line, for example:  return "█" * max(1, tokens // tokens_per_block)
    Then run:  python check.py 7a
    """
    return ""  # TODO-1: replace this line with one line that returns the bar


@before_model
def context_meter(state, runtime):
    """(built) Runs BEFORE every model call. Prints one bar per step, and saves the size in CONTEXT_LOG."""
    tokens = count_tokens_approximately(state["messages"])
    CONTEXT_LOG.append(tokens)
    step = len(CONTEXT_LOG)
    print(f"step {step:>2}  [{bar(tokens):<10}]  {tokens:>6,} tokens", flush=True)
    return None


# =============================================================================================
# LAB 7B  -  COMPACTION: SUMMARISE THE OLD MESSAGES
# =============================================================================================
COMPACT_AT_TOKENS = 1500     # when the chat reaches this size, the agent summarises the old part. Try 800 or 3000.
KEEP_LAST_MESSAGES = 4       # the newest messages are kept word for word, the rest becomes a short summary


def compaction_middleware(model):
    """TODO-2 (Lab 7B): make the agent summarise old messages. ONE line to write.

    Replace the line  'return None'  with ONE line that creates SummarizationMiddleware with:
        model=model
        trigger=("tokens", COMPACT_AT_TOKENS)
        keep=("messages", KEEP_LAST_MESSAGES)
    Use exactly these names. Then run:  python check.py 7b
    """
    return None  # TODO-2: replace this line with: return SummarizationMiddleware(...)


# =============================================================================================
# LAB 7C  -  LONG-TERM MEMORY: NOTES THAT SURVIVE A NEW CHAT
# =============================================================================================
# A chat thread forgets nothing inside itself, but a NEW thread starts empty.
# The store keeps notes across threads. Each note is saved under ("memories", user_id).

def remember(store, user_id, text):
    """TODO-3 (Lab 7C): save ONE note in the store. ONE line to write.

    Replace the line  'return None'  with ONE line that calls  store.put(...)  with:
        namespace  = ("memories", user_id)
        key        = uuid.uuid4().hex          (a unique id for this note)
        value      = {"text": text}
    Then run:  python check.py 7c
    """
    return None  # TODO-3: replace this line with: store.put(...)


def recall(store, user_id):
    """(built) Returns the list of notes saved for this user, as plain text."""
    return [item.value["text"] for item in store.search(("memories", user_id))]


def make_memory_tools(store, user_id):
    """(built) Two tools the agent can call: save_note and recall_notes. They use the store and the user id."""

    @tool
    def save_note(text: str) -> str:
        """Save a short fact about the user (for example their laptop model) so a later chat can recall it."""
        remember(store, user_id, text)
        return "Saved."

    @tool
    def recall_notes() -> str:
        """Return the facts saved about this user in earlier chats."""
        return json.dumps(recall(store, user_id))

    return [save_note, recall_notes]
