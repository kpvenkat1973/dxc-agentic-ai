# Model notes (Gatekeeper as an MCP tool)

1. **One server, not copies.** One `gatekeeper.py` behind one server means one place to fix a rule (like the v2 "ransomware" change) and every agent gets it at once. Copies drift: agent A blocks "address", agent B still allows it. One server also gives one place for logs and audit.

2. **Controls in front of it: role first, then log, then timeout.** Role: only agents allowed to ask may call it, and `needs_approval` must not be bypassable by a prompt-injected agent. Log: every call (who asked, tool, answer) so a refusal or approval can be audited. Timeout: a slow Gatekeeper must fail CLOSED (treat as "needs approval"), never open. Mask matters least here: the inputs are ticket text and employee ids, but mask ids in the log.

3. **Home: VM HTTP for the team, Lambda for production.** Many agents share it, so not stdio (stdio = one private process per agent, fine for a laptop demo only). HTTP on a VM is the quickest shared home. For production AWS Lambda: no server to patch, scales to zero, and the code is tiny and stateless. Note: this is a stateless function, so Lambda fits well.
