# SPEC: AskIT Ticket Triage v1

## Purpose
Classify an IT support ticket into a priority, a queue and an SLA. Pure function, no I/O, no LLM.

## Interface
`triage(ticket: dict) -> dict` in `triage.py`

Input keys: `title` (str, required), `description` (str, optional), `affected_users` (int, optional, default 1)
Output keys: `priority` ("P1".."P4"), `queue` (str), `sla_hours` (int)

## Rules
- R1 Text = title + description, matched case-insensitive, **whole words only** ("download" does not match "down").
- R2 Priority, first match wins:
  P1 if affected_users >= 50 or text has the word `outage` or `down`
  P2 if affected_users >= 10 or text has the word `urgent` or `blocked`
  P3 if affected_users >= 2
  P4 otherwise
- R3 Queue, first match wins:
  Network: vpn, wifi, network
  Access: password, login, locked
  Hardware: laptop, keyboard, screen
  General: none of the above
- R4 SLA hours: P1 = 4, P2 = 8, P3 = 24, P4 = 72
- R5 Empty or missing title: raise ValueError
- R6 affected_users missing: treat as 1. affected_users < 1 or not an int: raise ValueError
- R7 TODO: decide what happens when the description is None (we say: ______)
- R8 TODO: decide whether to log anything (we say: ______)

## Acceptance Criteria
- AC1 60 affected users -> P1, SLA 4
- AC2 "Email outage" -> P1
- AC3 "Slow download speed" -> P4 (whole word rule)
- AC4 12 users -> P2, SLA 8
- AC5 "URGENT: cannot print" -> P2
- AC6 3 users -> P3, SLA 24
- AC7 "Laptop wifi broken" -> queue Network (order matters)
- AC8 "Password reset" -> queue Access
- AC9 empty title -> ValueError; 0 users -> ValueError

## Out of scope
Persistence, authentication, ML, UI.

## Changelog
- v1 initial