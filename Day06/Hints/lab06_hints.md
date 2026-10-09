# Lab 6 hints and answers

Each part has ONE TODO. Try first, look at the **Hint**, and only then use the **Answer**.

**How to paste an answer:** in `agent6.py` press **Ctrl+F**, type `TODO-1` (or 2, 3) and press Enter. Select the whole old function (from its `def` line to its last line), delete it, paste the answer block from here, and press **Ctrl+S**. Then run `python check.py 6a` (or 6b, 6c).

---
## Lab 6A: TODO-1 `build_agent`
**Hint:** One line. `create_agent(...)` with four named inputs: `model=`, `tools=`, `system_prompt=` and `middleware=`. Use `middleware or []` so that `None` becomes an empty list.

**Answer**
```python
def build_agent(model, tools, middleware=None):
    return create_agent(model=model, tools=tools, system_prompt=SYSTEM_PROMPT, middleware=middleware or [])
```

---
## Lab 6B: TODO-2 `over_budget`
**Hint:** One comparison: "has model_calls reached max_calls?" Use `>=`.

**Answer**
```python
def over_budget(model_calls, max_calls):
    return model_calls >= max_calls
```

---
## Lab 6C: TODO-3 `describe_step` (the final-answer line)
**Hint:** Look at the `elif` with `pass`. Replace the word `pass` with the `lines.append(...)` line. It is the same kind of line as the tool lines above it.

**Answer** (the whole function, so you can copy it over the old one)
```python
def describe_step(update):
    lines = []
    for data in update.values():
        if not isinstance(data, dict):                                  # some steps carry no data
            continue
        for m in data.get("messages", []):
            if isinstance(m, AIMessage) and m.tool_calls:               # the model asks for a tool
                for call in m.tool_calls:
                    lines.append(f"🔧 asks for {call['name']}({short(call['args'])})")
            elif isinstance(m, AIMessage):
                lines.append(f"✅ answer: {text_of(m)}")
            elif isinstance(m, ToolMessage):                            # a tool result came back
                lines.append(f"👁️ result: {short(text_of(m))}")
    return lines
```

---
## Stretch C (optional): `stream_tokens`
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
