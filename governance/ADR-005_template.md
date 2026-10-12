# ADR-005: Multi-agent pattern and human approval points for AskIT

Team: team-___ · Date: ___ · Status: Proposed

Copy this file to `teams\team-<letter>\ADR-005.md` and fill every `___`. Keep it to one page.

## 1. Context

- AskIT receives 4 kinds of tickets: Network, Access, Hardware, General.
- Some actions change data (password reset, access grant). Some do not (search the knowledge base, read a ticket).
- New client rule (curveball): ___

## 2. Decision

- Pattern: ___ (example: Router + specialist agents + human approval step)
- Router model: ___ because ___ (example: Nova Micro, because it is one short classification call)
- Specialist model(s): ___
- Who decides that a human must approve: ___ (example: plain-code policy, not the LLM)
- Where write tools live: ___ (example: only in the Act step, after approval)

## 3. Alternatives considered

| Alternative | Why we did not choose it |
|---|---|
| One agent with all 4 tools | ___ |
| Handoffs between agents | ___ |
| Let the LLM decide when approval is needed | ___ |

## 4. Human-in-the-loop points

| Action | Who approves | If nobody answers in ___ hours |
|---|---|---|
| Password reset | ___ | ___ |
| Any VIP ticket | ___ | ___ |
| ___ | ___ | ___ |

## 5. Consequences

- Cost: about ___ LLM calls and ___ tokens per ticket (from Lab 8 tab 3). At 10,000 tickets/day ≈ ___ per month.
- Latency: ___ (approval can take minutes or days; state is kept in the checkpointer)
- Audit: ___
- Risk we accept: ___

## 6. Board verdict (filled by the board)

Approved · Approved with conditions · Rejected — Conditions: ___
