# Lab 7 hints and answers

Each part has ONE TODO. Try first, look at the **Hint**, and only then use the **Answer**.

**How to paste an answer:** in `agent7.py` press **Ctrl+F**, type `TODO-1` (or 2, 3) and press Enter. Select the whole old function (from its `def` line to its last line), delete it, paste the answer block from here, and press **Ctrl+S**. Then run `python check.py 7a` (or 7b, 7c).

---
## Lab 7A: TODO-1 `bar`
**Hint:** One line. Blocks = tokens divided by 500 (use `//`). Use `max(1, ...)` so small numbers still show one block.

**Answer**
```python
def bar(tokens, tokens_per_block=500):
    return "█" * max(1, tokens // tokens_per_block)
```

---
## Lab 7B: TODO-2 `compaction_middleware`
**Hint:** One line that creates `SummarizationMiddleware`. Use the three named inputs: `model=`, `trigger=("tokens", COMPACT_AT_TOKENS)`, `keep=("messages", KEEP_LAST_MESSAGES)`.

**Answer**
```python
def compaction_middleware(model):
    return SummarizationMiddleware(model=model, trigger=("tokens", COMPACT_AT_TOKENS), keep=("messages", KEEP_LAST_MESSAGES))
```

---
## Lab 7C: TODO-3 `remember`
**Hint:** One line: `store.put(namespace, key, value)`. The namespace is `("memories", user_id)`. The key is `uuid.uuid4().hex` (a unique id). The value is `{"text": text}`.

**Answer**
```python
def remember(store, user_id, text):
    store.put(("memories", user_id), uuid.uuid4().hex, {"text": text})
```
