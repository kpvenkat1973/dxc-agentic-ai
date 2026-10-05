"""Golden-set evaluation: retrieval metrics + optional LLM-as-judge for answer quality."""
import json, os, time
from datetime import datetime
from . import pipeline

GOLDEN = [
    dict(q="How many failed sign-ins lock my account and when does it unlock?", doc="KB-002_account_lockout",
         key="5 failed sign-in attempts", expected="After 5 failed sign-in attempts; it unlocks automatically after 30 minutes."),
    dict(q="What is the minimum password length?", doc="KB-001_password_reset", key="minimum 14 characters",
         expected="14 characters (an older article says 8: that one is superseded)."),
    dict(q="Can I use a personal laptop for VPN access?", audience="Employee", doc="KB-021_byod_employees",
         key="after enrolling it", expected="Yes, only after enrolling it in Orbit Mobile Management and turning on disk encryption."),
    dict(q="Can I use a personal laptop for VPN access?", audience="Contractor", doc="KB-005_vpn_contractors",
         key="Personal devices are not allowed", expected="No. Contractors may only use Orbit-issued laptops."),
    dict(q="My VPN shows error 809. What should I try?", doc="KB-004_vpn_connect", key="switch gateway",
         expected="Switch gateway, then restart the OrbitConnect service."),
    dict(q="How often does the VPN disconnect?", doc="KB-004_vpn_connect", key="every 12 hours",
         expected="Every 12 hours, by design (an older article says 24: superseded)."),
    dict(q="How long can I restore deleted OneDrive files?", doc="KB-013_backup", key="93 days",
         expected="93 days from the OneDrive recycle bin."),
    dict(q="I lost my phone with the authenticator app. What happens now?", doc="KB-003_mfa_setup", key="temporary access code",
         expected="Call the helpdesk. After a video-call identity check you get a temporary access code valid for 24 hours."),
    dict(q="What is the first response time for a High priority ticket?", doc="KB-016_priority_sla", key="1 hour |",
         expected="1 hour."),
    dict(q="Who approves access to a shared mailbox?", doc="KB-010_shared_mailbox", key="mailbox owner",
         expected="The mailbox owner."),
    dict(q="I clicked a phishing link and typed my password. What priority is this?", doc="KB-019_phishing",
         key="priority Critical", expected="Critical. Report it immediately, then reset your password."),
    dict(q="Can I get permanent admin rights?", doc="KB-008_software_install", key="never granted permanently",
         expected="No. Temporary admin (4 hours) needs manager approval."),
    dict(q="How quickly must a VIP ticket be acknowledged by phone?", doc="KB-018_vip_support", key="within 30 minutes",
         expected="Within 30 minutes during business hours."),
    dict(q="What is Orbit Corp's parental leave policy?", doc=None, key=None,
         expected="Not in the IT knowledge base: should say it doesn't know."),
    dict(q="Which cafeteria serves vegan food on Fridays?", doc=None, key=None,
         expected="Not in the IT knowledge base: should say it doesn't know."),
]

# ---------------------------------------------------------------- Challenge 1: YOUR questions
# TODO-1: add 2 questions of your own. Look in data/kb/ for an article that contains the answer.
#   doc      = the file name without .md   (example: "KB-012_wifi")
#   key      = a short phrase that must appear in the chunk that answers it   (example: "Orbit-Guest")
#   expected = the right answer in one sentence
#   audience = optional: "Employee" or "Contractor" (leave out to use the sidebar choice)
MY_QUESTIONS = [
    # dict(q="...", doc="KB-0xx_name", key="...", expected="..."),
]
GOLDEN = GOLDEN + MY_QUESTIONS

JUDGE_PROMPT = """You are grading an IT helpdesk assistant (AskIT).
Question: {q}
Reference answer: {ref}
Retrieved context:
{ctx}
Assistant answer: {ans}

Score 1-5:
- faithfulness: is every claim in the answer supported by the retrieved context? (5 = fully supported)
- correctness: does the answer match the reference answer? (5 = same meaning)
Return JSON only: {{"faithfulness": <1-5>, "correctness": <1-5>, "reason": "<one short sentence>"}}"""


IDK_PHRASES = ("don't know", "not mention", "doesn't mention", "does not mention", "no information",
               "not covered", "doesn't cover", "does not cover", "not specified", "human agent", "route this to")


def _hit(chunk, g):
    return chunk.doc.doc_id == g["doc"] and g["key"].lower() in chunk.text.lower()


def evaluate(index, cfg, audience="Employee", judge=False, progress=None):
    rows = []
    for n, g in enumerate(GOLDEN):
        aud = g.get("audience", audience)   # a question can fix who is asking
        res = pipeline.run(index, g["q"], cfg, aud)
        chunks = [h["chunk"] for h in res.hits]
        if g["doc"] is None:
            a = res.answer.lower().replace("’", "'")
            said_idk = res.abstained or any(p in a for p in IDK_PHRASES)
            hit1 = recall = rr = None
            passed = said_idk
        else:
            ranks = [k for k, c in enumerate(chunks) if _hit(c, g)]
            hit1 = 1.0 if ranks and ranks[0] == 0 else 0.0
            recall = 1.0 if ranks else 0.0
            rr = 1 / (ranks[0] + 1) if ranks else 0.0
            passed = bool(hit1) and not res.abstained
        wrong_src = any(not pipeline.is_ok_source(c, aud) for c in chunks[:1])
        row = dict(question=g["q"], passed=passed, hit_at_1=hit1, recall_at_k=recall, mrr=rr,
                   abstained=res.abstained, stale_or_wrong_office_top1=wrong_src,
                   top_source=chunks[0].citation if chunks else "-", answer=res.answer,
                   faithfulness=None, correctness=None, judge_reason="",
                   tokens=res.tokens_in + res.tokens_out, cost_usd=res.cost, latency_ms=res.timings.get("total_ms", 0))
        if judge and not index.llm.offline and not res.abstained:
            ctx = "\n".join(c.text for c in chunks)
            msg, u = index.llm.chat([{"role": "user", "content": JUDGE_PROMPT.format(
                q=g["q"], ref=g["expected"], ctx=ctx, ans=res.answer)}], op="judge", json_mode=True)
            try:
                j = json.loads(msg.content)
                row.update(faithfulness=float(j["faithfulness"]), correctness=float(j["correctness"]),
                           judge_reason=j.get("reason", ""))
            except Exception:
                pass
            row["judge_cost_usd"] = u["cost_usd"]
        rows.append(row)
        if progress:
            progress((n + 1) / len(GOLDEN))
    return rows


def summarize(cfg, rows, model):
    def avg(k):
        v = [r[k] for r in rows if r[k] is not None]
        return round(sum(v) / len(v), 3) if v else None
    return dict(run_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), config=cfg.name, settings=cfg.label(),
                model=model, pass_rate=round(sum(r["passed"] for r in rows) / len(rows), 3),
                hit_at_1=avg("hit_at_1"), recall_at_k=avg("recall_at_k"), mrr=avg("mrr"),
                faithfulness=avg("faithfulness"), correctness=avg("correctness"),
                wrong_source_top1=sum(r["stale_or_wrong_office_top1"] for r in rows),
                avg_latency_ms=int(sum(r["latency_ms"] for r in rows) / len(rows)),
                cost_usd=round(sum(r["cost_usd"] + r.get("judge_cost_usd", 0) for r in rows), 5),
                questions=rows)


RUNS_FILE = "evals/runs.json"


def load_runs():
    return json.load(open(RUNS_FILE)) if os.path.exists(RUNS_FILE) else []


def save_run(summary):
    runs = load_runs() + [summary]
    os.makedirs(os.path.dirname(RUNS_FILE), exist_ok=True)
    json.dump(runs, open(RUNS_FILE, "w"), indent=1)
    return runs
