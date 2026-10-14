# Trainer Model Solution - Gatekeeper Homework

Compare YOUR `SPEC.md`, `gatekeeper.py` and `submission\my_notes.md` with the files in this folder.
Run `score_solution.bat` to see the model solution pass (34 checks: the 21 client tests + 13 extra edge cases).

## Model notes (my_notes.md)

**Q1. D1 / D2 / D3 and why**
- D1 = **no**. Reading changes nothing, so approval adds delay with no risk reduction, even for a VIP.
- D2 = **on-call**. A locked-out user at night should not wait until 8 am, and a human still approves the write.
- D3 = **30 days**. Keep as little personal data as possible for as short a time as possible; refresh it when the fact is used again.
(Any sensible choice scores 21/21. The marks are for the reason you give.)

**Q2. The rule an LLM must never decide alone: R2 `needs_approval`.**
It is the control that stops a wrong action (reset password, grant access). An LLM can be fooled by prompt injection or just be wrong. Approval must be plain code that gives the same answer every time and can be audited. (R3 is a close second: "never store secrets".)

**Q3. Spec first, then code.**
The spec is the source of truth. If I edit only the code, the spec lies, the next regeneration silently drops my change, and the client cannot see what was agreed. Spec first -> code follows -> tests prove nothing old broke.

## What good looks like
- Whole-word matching with `\b`, so "download" is not "down" and "pinning" is not "pin".
- Team order is by the LIST, not by where the word appears in the text (Security before Access).
- `needs_approval` validates action AND hour; `True`/`"10"`/`24` are rejected.
- VIP check comes before the night check (rule 3 before rule 4).
- Digits: strip spaces and dashes first, then look for 6 or more digits in a row.
- v2: changelog line added, spec edited BEFORE the code, `score.bat` still 21.

## Common mistakes to look for
1. Substring match (`"down" in text`) instead of whole word.
2. Night written as `hour > 20` or `hour <= 8` (boundaries 20 and 8 are wrong).
3. Night check placed before the VIP check, so a VIP at night gets the wrong approver.
4. `hour` not validated, or `bool` accepted.
5. Digit rule applied per word, so "4111 1111 1111 1111" slips through.
6. Code edited for the v2 change but SPEC.md left at v1.
7. Notes left as `___`, or D1/D2/D3 given with no reason.

## Discussion points for the class
- "address" blocks "email address" too. Right for this client? Plural "addresses" is NOT blocked by the spec as written. A spec bug to fix by changing the spec.
- The digit rule is conservative: "Ticket 12 34 56" is also refused. Fail safe, not fail open.
- Which of D1/D2 would you ask the client to sign off, and why?
