# Lab 5 hints and full answers

**How to use this file:** try first. Read the **Hint** in plain words. If you are still stuck, copy the **Answer**. Every answer is the **complete block**, so you can select the whole block, copy it, and paste it over the same block in `agent.py`.

All code goes in `agent.py` (open the folder `C:\AskIT\dxc-agentic-ai\Day05\Labs\lab05-askit-agent-loop` in VS Code first).

Check your work with the lines in the README (for example `python check.py 5b`).

---

## Lab 5A

Nothing to write in Lab 5A. The 3 functions (`get_tool_requests`, `run_tool`, `make_tool_result`) are already built. Read them, then run `python run_5a.py`.

### Optional Stretch A: `get_user`

**Hint:** Look through the list of users (`load_users()`). When a user's id matches, return a dict with the name, department and vip flag. If nobody matches, return an error dict. Then remove the two `#` in front of the two lines below `GET_USER_SPEC`.

**Answer** (copy the whole function over the old `get_user`):
```python
def get_user(user_id):
    """STRETCH-A: return {"user_id", "name", "department", "vip"} for an employee (data: load_users()).
    If the user does not exist, return {"error": "User <id> not found."}.
    Then remove the two '#' in front of the lines just below this function to register the tool."""
    for u in load_users():                                   # each u is a dict from users.csv
        if u["user_id"].lower() == str(user_id).strip().lower():
            return {"user_id": u["user_id"], "name": u["name"], "department": u["department"], "vip": u["vip"]}
    return {"error": f"User {user_id} not found."}
```

**Answer** (copy these two lines over the two lines that start with `#`):
```python
TOOLS = {**TOOLS, "get_user": get_user}                      # register: the function ...
TOOL_SPECS = TOOL_SPECS + [GET_USER_SPEC]                    # ... and what the model is told about it
```

---

## Lab 5B

### TODO-1: the agent loop (`run_agent`)

**Hint:** The loop asks the model, then checks: did the model ask for a tool? If **no**, its text is the answer, so save it and stop. If **yes**, run each tool, collect the answers in a list, send them back to the model, and go round again. If the loop ends with no answer (out of steps), hand over to a human with `give_up`.

**Answer.** Select the old `run_agent` in `agent.py` (from the line `def run_agent(` down to the line `return result` at the end), delete it, and paste this whole function:
```python
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

        if not requests:                                                  # PART A: no tool request = the model is finished
            result["answer"] = final_text(response)                       # its text IS the answer
            say(result, f"Step {step}: ✅ final answer")
            return result

        messages.append(response["output"]["message"])                    # PART B-1: remember the model's tool request
        blocks = []                                                       # PART B-2: all tool answers go back in ONE message
        for req in requests:
            if STOP_ON_REPEAT and is_repeat(history, req["name"], req["input"]):    # Incident: the exact same call again?
                return give_up(result, "I kept repeating the same action, so a human will take over.")
            history.append((req["name"], req["input"]))                   # remember this call
            output = run_tool_safely(req["name"], req["input"], approve)  # ACT: run the tool
            say(result, f"Step {step}: 🔧 {req['name']}({short(req['input'])}) -> {short(output)}")   # OBSERVE: print what came back
            blocks.append(make_tool_result(req["id"], output))            # wrap the answer for the model
        messages.append({"role": "user", "content": blocks})              # PART B-4: give the answers back to the model

    # PART C: the loop ended without an answer = out of steps. Hand over to a human.
    return give_up(result, f"I could not finish within {max_steps} steps, so a human will take over.")

```

---

## Lab 5C

### TODO-2: which tools need approval (`needs_approval`)

**Hint:** Two tools change data (`update_ticket`, `reset_password`). For those the function must return `True`. For every other tool it must return `False`. One line is enough.

**Answer** (copy the whole function over the old `needs_approval`):
```python
def needs_approval(name, args):
    """TODO-2: should a human approve this tool call first? Return True (yes, ask) or False (no, just run it).

    Two tools only READ data:   search_kb, get_ticket          -> return False
    Two tools CHANGE data:      update_ticket, reset_password  -> return True
    Replace the line  return False  with ONE line. Full answer: Hints file, TODO-2.
    """
    return name in ("update_ticket", "reset_password")       # the two tools that change something
```

### Optional Stretch B: `vip_block`

**Hint:** Only tools that change data matter (use `needs_approval`). Find who the action is about: for `reset_password` it is `args["user_id"]`; for `update_ticket` look up the ticket first. Then check whether that user's `vip` column is `yes`.

**Answer** (copy the whole function over the old `vip_block`):
```python
def vip_block(name, args):
    """OPTIONAL STRETCH-B: KB-018 says: for a VIP user, AskIT may gather information but must hand over to a human
    before taking any ACTION. Return True when this call must be blocked completely:
      - the tool changes data (needs_approval says so) AND
      - the person it is about is a VIP (users.csv column 'vip' == 'yes').
    For reset_password the person is args["user_id"]. For update_ticket find the ticket's user_id first
    (data: load_tickets()). Everything else: return False."""
    if not needs_approval(name, args):
        return False                                         # reading is always fine
    user_id = args.get("user_id")
    if name == "update_ticket":                              # a ticket belongs to a user: look it up
        ticket = next((t for t in load_tickets() if t["ticket_id"] == args.get("ticket_id")), None)
        user_id = ticket["user_id"] if ticket else None
    user = next((u for u in load_users() if u["user_id"] == user_id), None)
    return bool(user and user["vip"].lower() == "yes")
```

---

## Incident: the agent is stuck in a loop

Nothing to write. The check `is_repeat` is already built, and the loop already uses it when you switch it on.

**Hint:** In `agent.py` press Ctrl+F, type `STOP_ON_REPEAT` and press Enter. Change `False` to `True`. Save.

**Answer** (the line must read exactly):
```python
STOP_ON_REPEAT = True
```

If the agent still does not stop after 2 steps, check that your `run_agent` has these 2 lines directly under `for req in requests:` (the full `run_agent` answer in **TODO-1** above has them):
```python
            if STOP_ON_REPEAT and is_repeat(history, req["name"], req["input"]):    # Incident: the exact same call again?
                return give_up(result, "I kept repeating the same action, so a human will take over.")
```
