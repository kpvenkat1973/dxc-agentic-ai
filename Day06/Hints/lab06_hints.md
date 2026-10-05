# Lab 6 hints and answers

Try first. Look at the **Hint**. Only then open the **Answer**. All code goes in `agent6.py`. Check yourself with `python check.py 6a` (or 6b, 6c).

---
## Lab 6A: build the agent

### TODO-1 `make_tools()`
**Hint:** `tool(some_function)` wraps one function as a LangChain tool. Put the four wrapped functions in a list, in the order: search_kb, get_ticket, update_ticket, reset_password.

**Answer**
```python
def make_tools():
    return [tool(search_kb), tool(get_ticket), tool(update_ticket), tool(reset_password)]
```

### TODO-2 `build_agent(model, tools, middleware=None)`
**Hint:** One call: `create_agent(...)` with `model=`, `tools=`, `system_prompt=` and `middleware=`. Use `middleware or []` so that `None` becomes an empty list.

**Answer**
```python
def build_agent(model, tools, middleware=None):
    return create_agent(model=model, tools=tools, system_prompt=SYSTEM_PROMPT, middleware=middleware or [])
```

### TODO-3 `ask(agent, question)`
**Hint:** `agent.invoke(...)` returns a dict; the conversation is `result["messages"]`. The last message is the answer (use `text_of`). For the tool names, loop over the messages, keep the `AIMessage`s, and read `call["name"]` for each call in `m.tool_calls`.

**Answer**
```python
def ask(agent, question):
    result = agent.invoke({"messages": [{"role": "user", "content": question}]})    # run the whole loop
    messages = result["messages"]                                                   # the full conversation
    answer = text_of(messages[-1])                                                  # the last message = the answer
    tools_used = [call["name"] for m in messages if isinstance(m, AIMessage) for call in m.tool_calls]
    return {"answer": answer, "tools_used": tools_used, "messages": messages}
```

---
## Lab 6B: middleware

### TODO-4 `redact_pii(text)`
**Hint:** Two `re.sub` calls, one for emails and one for phone numbers. The patterns are in the docstring. Assign the result back to `text` each time.

**Answer**
```python
def redact_pii(text):
    text = re.sub(r"[\w.+-]+@[\w-]+\.[\w.-]+", "[EMAIL]", text)                         # name@company.com
    text = re.sub(r"(?<!\d)(\+?\d{2}[\s-]?)?\d{5}[\s-]?\d{5}(?!\d)", "[PHONE]", text)   # +91 98765 43210
    return text
```

### TODO-5 `over_budget(model_calls, max_calls)`
**Hint:** One comparison. "Has the agent reached the limit?"

**Answer**
```python
def over_budget(model_calls, max_calls):
    return model_calls >= max_calls
```

### TODO-6 `tool_guard(request, handler)`
**Hint:** `try:` return `handler(request)`. `except Exception as e:` return a `ToolMessage` with `content` and `tool_call_id=request.tool_call["id"]`. Keep the `@wrap_tool_call` line above the function.

**Answer**
```python
@wrap_tool_call
def tool_guard(request, handler):
    try:
        return handler(request)                                       # run the tool normally
    except Exception as e:                                            # the tool crashed (e.g. database down)
        return ToolMessage(content=f"Tool failed: {e}. Tell the user a human will follow up.",
                           tool_call_id=request.tool_call["id"])      # the model gets an error it can explain
```

---
## Lab 6C: streaming

### TODO-7 `describe_step(update)`
**Hint:** `update` is a dict like `{"model": {"messages": [...]}}`. Loop over `update.values()`, skip anything that is not a dict, then loop over `data.get("messages", [])`. Three cases: an `AIMessage` with `tool_calls`, an `AIMessage` without, a `ToolMessage`.

**Answer**
```python
def describe_step(update):
    lines = []
    for data in update.values():
        if not isinstance(data, dict):                                  # some steps carry no data
            continue
        for m in data.get("messages", []):
            if isinstance(m, AIMessage) and m.tool_calls:               # the model asks for tools
                for call in m.tool_calls:
                    lines.append(f"🔧 asks for {call['name']}({short(call['args'])})")
            elif isinstance(m, AIMessage):                              # the model gives its answer
                lines.append(f"✅ answer: {text_of(m)}")
            elif isinstance(m, ToolMessage):                            # a tool result came back
                lines.append(f"👁️ result: {short(text_of(m))}")
    return lines
```

### TODO-8 `stream_answer(agent, question)`
**Hint:** `agent.stream(..., stream_mode="updates")` is a loop that gives you one update per step. Pass each update to `describe_step`, print the lines (add `flush=True`) and keep them in a list.

**Answer**
```python
def stream_answer(agent, question):
    printed = []
    for update in agent.stream({"messages": [{"role": "user", "content": question}]}, stream_mode="updates"):
        for line in describe_step(update):          # one update can hold several lines
            print(line, flush=True)                 # show it NOW, not at the end
            printed.append(line)
    return printed
```

### Stretch C `stream_tokens(agent, question)`
**Hint:** Use `stream_mode="messages"`: you get `(chunk, meta)` pairs. Keep only the chunks where `meta.get("langgraph_node") == "model"` and `text_of(chunk)` is not empty.

**Answer**
```python
def stream_tokens(agent, question):
    pieces = []
    for chunk, meta in agent.stream({"messages": [{"role": "user", "content": question}]}, stream_mode="messages"):
        piece = text_of(chunk)
        if meta.get("langgraph_node") == "model" and piece:       # only the model's words, skip tool output
            print(piece, end="", flush=True)
            pieces.append(piece)
    print()
    return pieces
```
