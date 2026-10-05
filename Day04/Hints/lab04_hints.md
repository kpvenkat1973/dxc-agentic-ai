# Lab 4 hints

**TODO-1 `parse_critic`**
1. Strip whitespace and remove ```` ```json ```` fences (`re.sub`).
2. `json.loads(...)` inside `try / except`. On any error return `{"enough": True, "missing": ""}`.
3. If `enough` is a string, compare lower-case to `"true"` / `"yes"`.

**TODO-2 `rewrite_query`**
1. The prompt needs two things: the question and `missing`. Ask for ONE short query, query only.
2. `msg, row = index.llm.chat([{"role": "user", "content": prompt}], op="rewrite")`
3. `res.usage.append(row)` then `msg.content.strip().strip('"\'')`. Empty? Return `question`.

**TODO-3 `should_continue`**
Two conditions joined by `and`: the critic is **not** enough, and `rounds_done < max_rounds`.

**Loop never runs?** All three must be done. Look at the trace on the right side of **Ask**: the Critic line must say "NOT enough".
