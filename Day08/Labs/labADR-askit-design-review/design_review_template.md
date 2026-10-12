# AskIT Design Review

**Team:** team-___ · **Members:** ___ · **Date:** ___
**Roles:** Scribe ___ · Architect ___ · Presenter ___ · Client voice ___

## Part 1. Our 6 decisions

Tick one option (replace `[ ]` with `[x]`) and write one line why.

**D1. Model**  [ ] A small everywhere  [ ] B large everywhere  [ ] C mix
Why: ___

**D2. Knowledge**  [ ] A RAG  [ ] B fine-tune  [ ] C paste all policies
Why: ___

**D3. Search quality**  [ ] A simple vector  [ ] B hybrid + reranker  [ ] C start simple, measure, upgrade
Why: ___

**D4. Actions**  [ ] A answer only  [ ] B act on its own  [ ] C act with human approval for writes
Why: ___

**D5. Memory**  [ ] A nothing  [ ] B current chat + compaction  [ ] C chat + facts per user
Why: ___
Never stored: ___

**D6. Agents**  [ ] A one agent  [ ] B router + specialists + approval  [ ] C handoffs
Why: ___

## Part 2. Cost check

Our model choice: ___ · Estimated cost per month: $___ · Fits the $2,000 budget? ___
(If mix: ___ % of tickets go to the large model)

## Part 3. Our decision record (ADR)

**Decision we argued about most:** D___

- **Context:** ___
- **Decision:** ___
- **Alternatives rejected (and why):** ___
- **Consequences (good):** ___
- **Consequences (bad, honest):** ___
- **How we will measure it:** ___

## Part 4. Answers to the client (one sentence each)

1. ChatGPT Enterprise / Copilot instead? ___
2. Made-up policies? ___
3. Resets on its own at 2 am? ___
4. Real monthly cost? ___
5. Why several agents? ___
6. Employees' chat data? ___
7. Cloud lock-in? ___
8. How will we know it works in 3 months? ___
