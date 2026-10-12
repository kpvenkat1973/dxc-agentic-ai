# ADR-EXAMPLE: Which model powers AskIT's router?

**Status:** Accepted · **Example ADR** (read this before writing your team's ADR-AskIT-01 in Lab 8, tab 6)

## 1. Context
- The router makes ONE short classification per ticket: Network, Access, Hardware or General.
- Orbit Corp gets about 10,000 tickets a day. The router must answer in under a second.

## 2. Decision
Use a **small model (Amazon Nova Micro)** for the router.

## 3. Alternatives we rejected
- **Claude Sonnet:** better on vague tickets, but many times the price per token, for a one-word answer.
- **Nova Lite:** a middle option. Kept as plan B if routing accuracy drops.

## 4. Evidence
- Lab 8: all 6 test tickets went to the right team.
- A few hundred tokens per ticket for the router call.

## 5. Consequences
- \+ Lowest cost and latency.
- − Vague tickets may be misrouted. They fall back to General and a human.
- Revisit if more than 5% of tickets are misrouted (measured on Day 10 with evals).
