# Trainer Model Solution - Gatekeeper MCP Homework (Day 9)

Folder contents: `SPEC.md`, `gatekeeper.py` (Day 8 model solution, unchanged), `gatekeeper_server.py`, `test_gatekeeper_server.py`, `my_notes.md`, `score_solution.bat`.
Run `score_solution.bat` (needs Python 3.10+): it installs fastmcp 4.1.0 and prints 20 PASS lines (10 checks over stdio, the same 10 over HTTP).

## How to build it the right way (the order matters)

1. **Spec first.** Save the spec as `SPEC.md` BEFORE any code. Copilot builds from the file, not from your memory of it. Say "ask me before coding" so it does not guess.
2. **Read the real function first.** The server must match `gatekeeper.py`, not the prompt. Open `needs_approval` and check its parameters.
3. **Thin wrapper.** Each tool is 1 line: `return gatekeeper.route(text)`. No `if`, no rules, no copy of the lists. If the server has logic, you have made a second Gatekeeper.
4. **Descriptions are the interface.** The model chooses a tool by its description (the docstring). One sentence: what it decides, what it needs. Not "route function".
5. **Type hints are the schema.** `text: str`, `hour: int`, `-> dict` become the JSON schema the agent sees. Remove them and the tool breaks or is mis-called.
6. **Errors stay errors.** Do NOT catch `ValueError` and return "ok" or `None`. FastMCP turns it into a tool error the agent can see. Swallowing it turns a refusal into a silent wrong answer (fail open).
7. **Test through MCP, not by importing.** The test starts the server, lists tools, calls them. That proves the thing an agent will actually touch.
8. **Fix the code, not the test.** When a check fails, change the server.

## Where the homework text and the real code disagree (discuss in class)

- The spec in the README says `needs_approval(action, is_vip, hour)` and "returns true or false". The real Day 8 function is `needs_approval(action, user_id, hour)` and returns a dict `{"approval", "approver"}`. The same README says "match the real parameter names and types", so the model solution follows the real function. Returning only true/false would also throw away WHO must approve. Good learners ask Copilot about the clash instead of letting it guess.
- A participant who sends `is_vip` has invented a parameter: the server would work but the VIP rule would have no way to run.

## Common mistakes to look for

1. Re-implementing the rules inside `gatekeeper_server.py` (copy of the lists, `if` chains).
2. Parameter names or types different from the real function (`is_vip`, `hour: str`).
3. `try/except` that returns `False` or `"General"` on error (fail open).
4. Missing docstring, or a vague one ("routes tickets").
5. Printing to stdout in a stdio server (`print(...)` breaks the MCP protocol: use stderr or logging).
6. Editing `gatekeeper.py` to make the server easier. The spec says do not.
7. `import gatekeeper` works only from one folder (no path handling): run from another folder and it fails.
8. Wrong port or `--http` ignored; the HTTP endpoint is `http://127.0.0.1:8778/mcp`.
9. Notes left empty, or the 3 answers have no reason.

## Model answers for my_notes.md

See `my_notes.md`. The marks are for the reason, not the choice: VM HTTP, Lambda or stdio are all acceptable if justified (stdio only for a single local agent).

## Stretch: safe_to_remember

- Add `@mcp.tool def safe_to_remember(fact: str) -> bool: return gatekeeper.safe_to_remember(fact)`.
- Model answer: this tool only CHECKS, it does not write, so it is read-like and safe for a read-only agent. The write-like part is the memory store itself: a read-only agent should not be able to save anything, whatever this tool answers. Put the role control on the memory-write tool, not on the check.
