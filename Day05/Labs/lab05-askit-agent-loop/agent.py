r"""agent.py  --  the AskIT agent. This is the ONLY file you edit in Lab 5.

FIRST: in VS Code click  File > Open Folder  and open this folder:
    C:\AskIT\dxc-agentic-ai\Day05\Labs\lab05-askit-agent-loop

WHERE YOU EDIT  (press Ctrl+F and search for the word shown):
    Lab 5A    nothing to write. Read 3 small functions, then run run_5a.py
    Lab 5B    TODO-1   write the agent loop                      (search:  TODO-1)
    Lab 5C    TODO-2   say which tools need a human's approval   (search:  TODO-2)
    Incident  change one word, False to True                     (search:  STOP_ON_REPEAT)

Everything else is already built. Parts marked  READ ONLY  are for you to read, not to change.
Stuck? Open  Day05\Hints\lab05_hints.md . Every TODO there has a full answer you can copy.

The messages to the AI model use the AWS Bedrock "Converse" format. You will see these three shapes:
    the user says something :  {"role": "user",      "content": [ {"text": "What is ticket TKT-0004?"} ]}
    the model wants a tool  :  {"role": "assistant", "content": [ {"toolUse": {"toolUseId": "a1", "name": "get_ticket", "input": {"ticket_id": "TKT-0004"}}} ]}
    we give the tool result :  {"role": "user",      "content": [ {"toolResult": {"toolUseId": "a1", "content": [ {"json": {...}} ]}} ]}
"""
import json
import re
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

MAX_STEPS = 6            # the agent may take at most this many turns. Agents ALWAYS need a stop.
STOP_ON_REPEAT = False      # Incident lab: change False to True. The agent then stops when it repeats the same call.


# =============================================================================================
# SMALL HELPERS  (READ ONLY)
# =============================================================================================
def final_text(response):
    """Join all the text blocks of a model reply into one string."""
    text = "".join(b.get("text", "") for b in response["output"]["message"]["content"])
    text = re.sub(r"<thinking>.*?</thinking>", "", text, flags=re.S)     # some models print private notes: hide them
    return text.strip()


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
# LAB 5A  -  ONE TOOL CALL, BY HAND                                  (READ ONLY: nothing to write)
# =============================================================================================
# The AI model cannot run anything. It can only ASK for a tool. Your code does 3 jobs:
#   job 1  get_tool_requests : read the model's reply and find which tool it asked for
#   job 2  run_tool          : run that tool
#   job 3  make_tool_result  : wrap the tool's answer and send it back to the model
# Read the 3 functions below (about 5 minutes), then run  python run_5a.py  to watch them work.

def run_tool(name, args):
    """JOB 2: run the tool the model asked for and return its result (a dict).

    name = the tool's name, e.g. "get_ticket"        args = the inputs the model chose, e.g. {"ticket_id": "TKT-0004"}
    The agent must NEVER crash because the model picked a wrong tool or wrong inputs. So we return an error instead.
    """
    func = TOOLS.get(name)                      # TOOLS is a list of our tools: tool name -> Python function
    if func is None:                            # the model asked for a tool we do not have
        return {"error": f"Unknown tool: {name}"}
    try:
        return func(**args)                     # run it. **args turns {"ticket_id": "X"} into ticket_id="X"
    except Exception as e:                      # e.g. the model forgot an input: tell it, do not crash
        return {"error": f"{type(e).__name__}: {e}"}


def get_tool_requests(response):
    """JOB 1: find the tool requests inside the model's reply. Returns a LIST (an empty list when there are none).

    The reply is a list of blocks: some are plain text, some are tool requests (they have the key "toolUse").
    """
    blocks = response["output"]["message"]["content"]       # the model's reply is a list of blocks
    requests = []
    for block in blocks:
        if "toolUse" in block:                               # this block is a tool request
            use = block["toolUse"]
            requests.append({"id": use["toolUseId"], "name": use["name"], "input": use["input"]})
    return requests


def make_tool_result(tool_use_id, result):
    """JOB 3: wrap a tool's result so the model can read it.

    The toolUseId must be the SAME id the model sent in its request. That is how the model matches answer to question.
    """
    return {"toolResult": {"toolUseId": tool_use_id, "content": [{"json": result}]}}


# --- OPTIONAL STRETCH for Lab 5A: add a 5th tool, get_user -------------------------------------
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
# LAB 5B  -  THE AGENT LOOP                                          (you write TODO-1 here)
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

        # ============ TODO-1: write the rest of the loop (3 parts). Full answer: Hints file, TODO-1 ============
        # PART A. The model asked for NO tool = it already has the answer. Write these 3 lines inside  if not requests:
        #       result["answer"] = final_text(response)          save the model's text as the answer
        #       say(result, f"Step {step}: ✅ final answer")      print a line
        #       return result                                    stop here
        #
        # PART B. The model asked for tool(s). Write these steps (after the if), then delete the  break  line below:
        #   1. messages.append(response["output"]["message"])         remember the model's tool request
        #   2. blocks = []                                            a list to collect the tool answers
        #   3. for req in requests:                                   (the model may ask for several tools at once)
        #          if STOP_ON_REPEAT and is_repeat(history, req["name"], req["input"]):          (used in the Incident)
        #              return give_up(result, "I kept repeating the same action, so a human will take over.")
        #          history.append((req["name"], req["input"]))        remember this call
        #          output = run_tool_safely(req["name"], req["input"], approve)     ACT: run the tool
        #          say(result, f"Step {step}: 🔧 {req['name']}({short(req['input'])}) -> {short(output)}")
        #          blocks.append(make_tool_result(req["id"], output))   wrap the answer
        #   4. messages.append({"role": "user", "content": blocks})   send all the answers back to the model
        break   # <- delete this line when PART A and PART B are written

    # PART C. If we get here the loop ran out of steps without an answer. Replace the next line with:
    #       return give_up(result, f"I could not finish within {max_steps} steps, so a human will take over.")
    return result


# =============================================================================================
# LAB 5C  -  ASK A HUMAN BEFORE THE AGENT CHANGES ANYTHING          (you write TODO-2 here)
# =============================================================================================
def needs_approval(name, args):
    """TODO-2: should a human approve this tool call first? Return True (yes, ask) or False (no, just run it).

    Two tools only READ data:   search_kb, get_ticket          -> return False
    Two tools CHANGE data:      update_ticket, reset_password  -> return True
    Replace the line  return False  with ONE line. Full answer: Hints file, TODO-2.
    """
    return False


def ask_human(name, args):
    """READ ONLY. Ask the person at the keyboard to approve an action. Returns True for 'y'."""
    answer = input(f"   ⚠️  AskIT wants to run {name}({short(args)}). Approve? [y/N] ")
    return answer.strip().lower() == "y"


def vip_block(name, args):
    """OPTIONAL STRETCH-B: KB-018 says: for a VIP user, AskIT may gather information but must hand over to a human
    before taking any ACTION. Return True when this call must be blocked completely:
      - the tool changes data (needs_approval says so) AND
      - the person it is about is a VIP (users.csv column 'vip' == 'yes').
    For reset_password the person is args["user_id"]. For update_ticket find the ticket's user_id first
    (data: load_tickets()). Everything else: return False."""
    return False


def run_tool_safely(name, args, approve=None):
    """READ ONLY. Run a tool, but ask a human first when needs_approval() says the tool changes data.

    The check lives HERE, in code, between the model's request and the tool. The model cannot skip it.
    """
    if vip_block(name, args):                                # STRETCH-B (does nothing until vip_block is written)
        return {"error": "This user is a VIP. A human must handle this action. Do not retry."}
    if needs_approval(name, args):                           # a tool that changes data: stop and ask a human
        approve = approve or ask_human
        if not approve(name, args):
            return {"error": "A human did not approve this action. Do not retry. Tell the user a human will follow up."}
    return run_tool(name, args)                              # approved (or a harmless read tool): run it


# =============================================================================================
# INCIDENT  -  "THE AGENT IS STUCK IN A LOOP"                       (READ ONLY)
# =============================================================================================
def is_repeat(history, name, args):
    """Has the agent already made EXACTLY this call (same tool, same inputs)?

    history = a list of (tool_name, inputs) pairs the agent has already run, e.g. [("get_ticket", {"ticket_id": "TKT-0004"})]
    The loop in run_agent uses this when  STOP_ON_REPEAT = True  (see the top of this file).
    """
    return (name, args) in history                           # same tool AND same inputs = a repeat
