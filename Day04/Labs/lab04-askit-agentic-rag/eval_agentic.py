"""Lab 4 evaluation: single-pass RAG vs the agentic loop on multi-part questions.
A question passes when the final evidence holds EVERY article the answer needs ("evidence complete")."""
import json
import os
from datetime import datetime

import agentic
from rag import pipeline

QUESTIONS = [
    dict(kind="multi-part", audience="Contractor",
         q="I'm a contractor and my VPN shows error 809. What should I try, and can I use my own laptop?",
         docs=["KB-004_vpn_connect", "KB-005_vpn_contractors"], keys=["switch gateway", "Personal devices are not allowed"]),
    dict(kind="multi-part", audience="Employee",
         q="I left my laptop at the airport. What will the helpdesk do with it, and how fast will they respond?",
         docs=["KB-014_lost_device", "KB-016_priority_sla"], keys=["lock and remotely wipe", "15 min"]),
    dict(kind="multi-part", audience="Employee",
         q="My manager is a VIP and her account keeps locking. When does it unlock, and who handles her ticket?",
         docs=["KB-002_account_lockout", "KB-018_vip_support"], keys=["30 minutes", "named support engineer"]),
    dict(kind="multi-part", audience="Employee",
         q="Email on my phone stopped syncing after I changed my password and now I get locked out. What do I do, and when will it unlock?",
         docs=["KB-009_email_mobile", "KB-002_account_lockout"], keys=["re-entering the password", "30 minutes"]),
    dict(kind="multi-part", audience="Employee",
         q="Who approves temporary admin rights, and how long does an access request usually take?",
         docs=["KB-008_software_install", "KB-015_access_request"], keys=["manager approval", "working days"]),
    dict(kind="simple", audience="Employee", q="What is the minimum password length?",
         docs=["KB-001_password_reset"], keys=["14 characters"]),
    dict(kind="simple", audience="Employee", q="How long can I restore deleted OneDrive files?",
         docs=["KB-013_backup"], keys=["93 days"]),
    dict(kind="simple", audience="Employee", q="Who approves access to a shared mailbox?",
         docs=["KB-010_shared_mailbox"], keys=["mailbox owner"]),
]

CONFIGS = ["Single pass (Lab 3)", "Agentic RAG (critic loop)"]
RUNS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "evals_agentic", "runs.json")


def evidence_complete(res, item):
    chunks = [h["chunk"] for h in res.hits]
    return all(any(c.doc.doc_id == d and k.lower() in c.text.lower() for c in chunks)
               for d, k in zip(item["docs"], item["keys"]))


def evaluate(index, config, max_rounds=agentic.MAX_ROUNDS, progress=None):
    rows = []
    for n, item in enumerate(QUESTIONS):
        if config == CONFIGS[0]:
            res = agentic.run_single(index, item["q"], item["audience"])
        else:
            res = agentic.run(index, item["q"], item["audience"], max_rounds)
        rows.append(dict(question=item["q"], kind=item["kind"], route=res.route, rounds=res.rounds,
                         llm_calls=agentic.llm_calls(res), complete=evidence_complete(res, item), abstained=res.abstained,
                         sources=agentic._docs(res.hits), cost_usd=res.cost, latency_ms=res.timings.get("total_ms", 0),
                         answer=res.answer))
        if progress:
            progress((n + 1) / len(QUESTIONS))
    return rows


def summarize(config, rows, model):
    multi = [r for r in rows if r["kind"] == "multi-part"]
    n = len(rows)
    return dict(run_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), config=config, model=model,
                pass_rate=round(sum(r["complete"] for r in rows) / n, 3),
                multi_part_pass=round(sum(r["complete"] for r in multi) / max(1, len(multi)), 3),
                avg_llm_calls=round(sum(r["llm_calls"] for r in rows) / n, 2),
                avg_cost_usd=round(sum(r["cost_usd"] for r in rows) / n, 6),
                avg_latency_ms=int(sum(r["latency_ms"] for r in rows) / n),
                loop_rate=round(sum(r["rounds"] > 1 for r in rows) / n, 3), questions=rows)


def load_runs():
    try:
        with open(RUNS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):   # no file yet, or a half-written one: start fresh
        return []


def save_run(summary):
    runs = load_runs() + [summary]
    os.makedirs(os.path.dirname(RUNS_FILE), exist_ok=True)
    with open(RUNS_FILE, "w", encoding="utf-8") as f:
        json.dump(runs, f, indent=1)
    return runs
