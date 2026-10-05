"""agent.py  --  the AskIT agent, built step by step today.

Open this file in VS Code. It has 4 parts, one per lab slot. Work from top to bottom:

    Lab 5A  TODO-1, 2, 3   run ONE tool call by hand
    Lab 5B  TODO-4, 5, 6   the agent LOOP (think -> act -> observe -> repeat)
    Lab 5C  TODO-7, 8      ask a human before the agent changes anything
    Incident TODO-9        stop the agent when it repeats itself

Everything NOT marked TODO is already built. Read the comments: they explain each line.
Each TODO has a short description, a starter, and a hint file:  Day05\\Hints\\lab05_hints.md  (answers are there too).

The messages use the AWS Bedrock "Converse" format. You will see these three shapes:
    the user says something :  {"role": "user",      "content": [ {"text": "What is ticket TKT-0004?"} ]}
    the model wants a tool  :  {"role": "assistant", "content": [ {"toolUse": {"toolUseId": "a1", "name": "get_ticket", "input": {"ticket_id": "TKT-0004"}}} ]}
    we give the tool result :  {"role": "user",      "content": [ {"toolResult": {"toolUseId": "a1", "content": [ {"json": {...}} ]}} ]}
"""
import json
import sys
from pathlib import Path

# --- Make "askit_core" (the shared code two folders up) importable. Leave this block alone. ---
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from askit_core.data import load_tickets, load_users          # noqa: E402  (the Orbit Corp data)
from askit_core.tools import TOOLS, TOOL_SPECS                # noqa: E402  (the 4 tools + what the model is told about them)
import provider                                               # noqa: E402  (talks to Bedrock / OpenAI / offline)

# The agent's "job description". The model reads this before every question.
SYSTEM_PROMPT = """You are AskIT, the IT helpdesk assistant of Orbit Corp.
Rules:
1. For how-to questions, call search_kb and answer ONLY from what it returns. Cite the article id, like [KB-004].
2. For a question about a ticket, call get_ticket.
3. Use update_ticket or reset_password ONLY when the user clearly asks for that action.
4. If a tool returns an error, tell the user in one sentence.
5. When you have the answer, reply in 2-3 short sentences."""

MAX_STEPS = 6          # the agent may take at most this many turns. Agents ALWAYS need a stop.


# =============================================================================================
# SMALL HELPERS (already built)
# =============================================================================================
def final_text(response):
    """Join all the text blocks of a model reply into one string."""
    return "".join(b.get("text", "") for b in response["output"]["message"]["content"]).strip()


def short(value, limit=110):
    """Turn anything into a short one-line string for printing."""
    text = json.dumps(value, ensure_ascii=False)
    return text if len(text) <= limit else text[:limit] + "..."


def say(result, line):
    """Print a line AND keep it in the trace, so you can read what the agent did."""
    result["trace"].append(line)
    print(line)


def add_usage(result, response):
    """Add this call's token counts to the running totals (used for the cost line)."""
    usage = response.get("usage", {})
    result["input_tokens"] += usage.get("inputTokens", 0)
    result["output_tokens"] += usage.get("outputTokens", 0)


def give_up(result, reason):
    """Stop the agent and hand the user over to a human."""
    result["answer"] = reason
    result["handoff"] = True
    say(result, f"🛑 Handoff to a human: {reason}")
    return result


# =============================================================================================
# LAB 5A  -  ONE TOOL CALL, BY HAND
# =============================================================================================
def run_tool(name, args):
    """TODO-1: run the tool the model asked for.

    name = the tool's name, e.g. "get_ticket"
    args = a dict of inputs the model chose, e.g. {"ticket_id": "TKT-0004"}
    Return the tool's result (a dict). The agent must NEVER crash because the model chose a bad tool or bad inputs:
      - unknown tool name  -> return {"error": "Unknown tool: <name>"}
      - the tool raises    -> return {"error": "<what went wrong>"}
    """
    return {"error": "TODO-1 not done yet"}


def get_tool_requests(response):
    """TODO-2: find the tool requests inside the model's reply. Return a LIST (an empty list when there are none).

    The reply looks like:
      response["output"]["message"]["content"] = [ {"text": "Let me check."},
                                                   {"toolUse": {"toolUseId": "a1", "name": "get_ticket", "input": {...}}} ]
    For every block that has a "toolUse" key, add  {"id": <toolUseId>, "name": <name>, "input": <input>}  to the list.
    """
    blocks = response["output"]["message"]["content"]       # the model's reply is a list of blocks
    return []


def make_tool_result(tool_use_id, result):
    """TODO-3: wrap a tool's result so the model can read it.

    Return ONE block shaped like:
      {"toolResult": {"toolUseId": <tool_use_id>, "content": [ {"json": <result>} ]}}
    The toolUseId must be the SAME id the model sent in its request. That is how the model matches answer to question.
    """
    return {}


# --- STRETCH for Lab 5A: add a 5th tool, get_user ---------------------------------------------
def get_user(user_id):
    """STRETCH-A: return {"user_id", "name", "department", "vip"} for an employee (data: load_users()).
    If the user does not exist, return {"error": "User <id> not found."}.
    Then remove the two '#' in front of the lines just below this function to register the tool."""
    return {"error": "STRETCH-A not built yet"}


GET_USER_SPEC = {"toolSpec": {"name": "get_user", "description": "Look up an employee by id: name, department, VIP flag.",
                              "inputSchema": {"json": {"type": "object", "required": ["user_id"],
                                                       "properties": {"user_id": {"type": "string"}}}}}}
# TOOLS = {**TOOLS, "get_user": get_user}                    # register: the function ...
# TOOL_SPECS = TOOL_SPECS + [GET_USER_SPEC]                  # ... and what the model is told about it


# =============================================================================================
# LAB 5C  -  ASK A HUMAN BEFORE THE AGENT CHANGES ANYTHING  (defined here because the loop below uses it)
# =============================================================================================
def needs_approval(name, args):
    """TODO-7: should a human approve this tool call first?

    Two tools only READ data: search_kb, get_ticket        -> no approval needed (return False)
    Two tools CHANGE data:    update_ticket, reset_password -> a human must approve (return True)
    """
    return False


def ask_human(name, args):
    """Ask the person at the keyboard to approve an action. Returns True for 'y'."""
    answer = input(f"   ⚠️  AskIT wants to run {name}({short(args)}). Approve? [y/N] ")
    return answer.strip().lower() == "y"


def vip_block(name, args):
    """STRETCH-B: KB-018 says: for a VIP user, AskIT may gather information but must hand over to a human
    before taking any ACTION. Return True when this call must be blocked completely:
      - the tool changes data (needs_approval says so) AND
      - the person it is about is a VIP (users.csv column 'vip' == 'yes').
    For reset_password the person is args["user_id"]. For update_ticket find the ticket's user_id first
    (data: load_tickets()). Everything else: return False."""
    return False


def run_tool_safely(name, args, approve=None):
    """TODO-8: run a tool, but ask for approval first when needs_approval() says so.

    1. If needs_approval(name, args): ask   approve(name, args)   (use ask_human when approve is None).
       If the answer is False, DO NOT run the tool. Return
       {"error": "A human did not approve this action. Do not retry. Tell the user a human will follow up."}
    2. Otherwise return run_tool(name, args).
    STRETCH-B: before step 1, if vip_block(name, args) return an error that says a human must handle VIP users.
    """
    return run_tool(name, args)                              # starter: runs everything, no questions asked


# =============================================================================================
# INCIDENT  -  "THE AGENT IS STUCK IN A LOOP"
# =============================================================================================
def is_repeat(history, name, args):
    """TODO-9: has the agent already made EXACTLY this call?

    history = a list of (tool_name, inputs) pairs the agent has already run, e.g. [("get_ticket", {"ticket_id": "TKT-0004"})]
    Return True if (name, args) is already in the list. Return False for the first time.

    THEN use it: in run_agent, inside `for req in requests:` and BEFORE the line that runs the tool, add
        if is_repeat(history, req["name"], req["input"]):
            return give_up(result, "I kept repeating the same action, so a human will take over.")
    """
    return False


# =============================================================================================
# LAB 5B  -  THE AGENT LOOP
# =============================================================================================
def run_agent(question, call_model=None, max_steps=MAX_STEPS, approve=None):
    """Answer a question by looping:  THINK (ask the model) -> ACT (run its tool) -> OBSERVE (give it the result) -> repeat.

    Returns a dict:  answer, steps, handoff (True if a human must take over), trace (list of lines),
                     messages (the whole conversation), input_tokens, output_tokens.
    call_model is only replaced in the tests. Normally it is provider.ask_model.
    """
    call_model = call_model or provider.ask_model
    messages = [{"role": "user", "content": [{"text": question}]}]       # the conversation starts with the question
    result = {"answer": "", "steps": 0, "handoff": False, "trace": [], "messages": messages,
              "input_tokens": 0, "output_tokens": 0}
    history = []                                                          # every (tool, inputs) already run

    for step in range(1, max_steps + 1):                                  # the loop, with a hard limit
        response = call_model(messages)                                   # THINK: ask the model what to do next
        result["steps"] = step
        add_usage(result, response)
        requests = get_tool_requests(response)                            # did the model ask for a tool?

        pass   # TODO-4: if `requests` is empty, save final_text(response) in result["answer"], say(...) a line, and return result

        # TODO-5: write these 4 steps, then delete the `break` line below:
        #   1. messages.append(response["output"]["message"])       remember the model's tool request
        #   2. blocks = []                                          all tool results go back in ONE user message
        #   3. for req in requests:                                 (the model may ask for several tools at once)
        #          history.append((req["name"], req["input"]))      remember the call
        #          output = run_tool_safely(req["name"], req["input"], approve)     ACT: run the tool
        #          say(result, f"Step {step}: 🔧 {req['name']}({short(req['input'])}) -> {short(output)}")
        #          blocks.append(make_tool_result(req["id"], output))
        #   4. messages.append({"role": "user", "content": blocks})   give the results back to the model
        break   # <- delete this line when TODO-5 is written

    return result   # TODO-6: the loop ended without an answer: use give_up(result, "...") instead
