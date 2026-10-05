# Lab 5 hints and answers

Try first. Look at the **Hint**. Only then open the **Answer**. All code goes in `agent.py`. Run `pytest tests` in the lab folder to check.

---
## Lab 5A

### TODO-1 `run_tool(name, args)`
**Hint:** `TOOLS` is a dict: tool name -> Python function. Use `TOOLS.get(name)`. If it is `None`, return an error dict. Call the function with `func(**args)` inside `try / except Exception`.

**Answer**
```python
def run_tool(name, args):
    func = TOOLS.get(name)                      # TOOLS maps a tool name to its Python function
    if func is None:                            # the model asked for a tool we do not have
        return {"error": f"Unknown tool: {name}"}
    try:
        return func(**args)                     # call it. **args turns {"ticket_id": "X"} into ticket_id="X"
    except Exception as e:                      # e.g. the model forgot an input: tell it, do not crash
        return {"error": f"{type(e).__name__}: {e}"}
```

### TODO-2 `get_tool_requests(response)`
**Hint:** The line `blocks = ...` is already written. Loop over `blocks`. A block that asks for a tool has the key `"toolUse"`. Build `{"id":..., "name":..., "input":...}` from `block["toolUse"]` (`toolUseId`, `name`, `input`) and append it to a list. Return the list.

**Answer** (keep the `blocks = ...` line above it)
```python
requests = []
for block in blocks:
    if "toolUse" in block:                               # this block is a tool request
        use = block["toolUse"]
        requests.append({"id": use["toolUseId"], "name": use["name"], "input": use["input"]})
return requests
```

### TODO-3 `make_tool_result(tool_use_id, result)`
**Hint:** Return exactly the shape in the docstring: a dict with one key `"toolResult"`.

**Answer**
```python
def make_tool_result(tool_use_id, result):
    return {"toolResult": {"toolUseId": tool_use_id, "content": [{"json": result}]}}
```

### Stretch A: `get_user`
**Hint:** Same pattern as the other tools: loop over `load_users()`, compare `user_id`, return the fields. Then remove the `#` in front of the two registration lines.

**Answer**
```python
def get_user(user_id):
    for u in load_users():                                   # each u is a dict from users.csv
        if u["user_id"].lower() == str(user_id).strip().lower():
            return {"user_id": u["user_id"], "name": u["name"], "department": u["department"], "vip": u["vip"]}
    return {"error": f"User {user_id} not found."}
```

Registration lines (remove the `#`):
```python
TOOLS = {**TOOLS, "get_user": get_user}                      # register: the function ...
TOOL_SPECS = TOOL_SPECS + [GET_USER_SPEC]                    # ... and what the model is told about it
```

---
## Lab 5B

### TODO-4 inside `run_agent`: the model is finished
**Hint:** No tool requests means the model wrote its final answer. Save the text, print a line with `say(...)`, and `return result`.

**Answer** (replace the `pass` line)
```python
if not requests:                                                  # no tool request = the model is finished
    result["answer"] = final_text(response)                       # its text IS the answer
    say(result, f"Step {step}: ✅ final answer")
    return result
```

### TODO-5 inside `run_agent`: run the tools and go round again
**Hint:** Four steps: (1) append the model's message, (2) one `blocks` list, (3) for each request run the tool and add a `make_tool_result` block, (4) append ONE user message with all the blocks. Delete the `break` line.

**Answer** (replace the comments and the `break` line; the `is_repeat` lines belong to the Incident, skip them for now)
```python
messages.append(response["output"]["message"])                    # 1. remember the model's tool request
blocks = []                                                       # 2. all tool results go back in ONE user message
for req in requests:
    history.append((req["name"], req["input"]))                   # remember this call
    output = run_tool_safely(req["name"], req["input"], approve)  # ACT: run the tool
    say(result, f"Step {step}: 🔧 {req['name']}({short(req['input'])}) -> {short(output)}")   # OBSERVE
    blocks.append(make_tool_result(req["id"], output))
messages.append({"role": "user", "content": blocks})              # 3. give the results back to the model
```

### TODO-6 end of `run_agent`: out of steps
**Hint:** The `for` loop finished without an answer. Use the helper `give_up(result, "...")`. It already returns `result`.

**Answer** (replace `return result`)
```python
return give_up(result, f"I could not finish within {max_steps} steps, so a human will take over.")
```

---
## Lab 5C

### TODO-7 `needs_approval(name, args)`
**Hint:** Two tools change data: `update_ticket` and `reset_password`. Return `True` for those names only.

**Answer**
```python
def needs_approval(name, args):
    return name in ("update_ticket", "reset_password")       # the two tools that change something
```

### TODO-8 `run_tool_safely(name, args, approve=None)`
**Hint:** If `needs_approval(...)` is true, call `approve(name, args)` (use `ask_human` when `approve` is `None`). If the answer is false, return the error dict from the docstring. Otherwise `return run_tool(name, args)`.

**Answer** (the first two lines are Stretch B; they do nothing until `vip_block` is written)
```python
def run_tool_safely(name, args, approve=None):
    if vip_block(name, args):                                # STRETCH-B (harmless until vip_block is written)
        return {"error": "This user is a VIP. A human must handle this action. Do not retry."}
    if needs_approval(name, args):                           # a write tool: stop and ask a human
        approve = approve or ask_human
        if not approve(name, args):
            return {"error": "A human did not approve this action. Do not retry. Tell the user a human will follow up."}
    return run_tool(name, args)                              # approved (or a harmless read tool): run it
```

### Stretch B: `vip_block(name, args)`
**Hint:** Reading is always fine. For `update_ticket`, find the ticket in `load_tickets()` to get its `user_id`. Then find that user in `load_users()` and check `vip == "yes"`.

**Answer**
```python
def vip_block(name, args):
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

### TODO-9 `is_repeat(history, name, args)`
**Hint:** `history` is a list of `(name, args)` pairs. Is this pair already in it?

**Answer**
```python
def is_repeat(history, name, args):
    return (name, args) in history                           # same tool AND same inputs = a repeat
```

Then add this inside `for req in requests:` in `run_agent`, BEFORE the line that runs the tool:
```python
            if is_repeat(history, req["name"], req["input"]):
                return give_up(result, "I kept repeating the same action, so a human will take over.")
```
