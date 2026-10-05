"""Lab 4 - Agentic RAG: a retrieval loop with a critic.

Single-pass RAG:   question -> retrieve -> rerank -> answer
Agentic RAG:       question -> ROUTER -> [ retrieve -> rerank -> CRITIC -> (not enough?) rewrite query -> again ]
                                         -> answer -> ANSWER CHECK -> answer or hand over to a human

You complete 3 small TODOs (parse_critic, rewrite_query, should_continue). Everything else is built.
With the starter versions the loop never runs, so the agent behaves like single-pass RAG.
This file reuses the pipeline from Lab 3 (..\\lab03-askit-advanced-rag\\rag).
"""
import dataclasses
import json
import re
import sys
import time
from pathlib import Path

LAB3 = Path(__file__).resolve().parents[1] / "lab03-askit-advanced-rag"
if str(LAB3) not in sys.path:
    sys.path.insert(0, str(LAB3))

from rag import pipeline  # noqa: E402  (the Lab 3 pipeline)

EXTRA_PER_ROUND = 2                              # passages a follow-up round may add
MAX_ROUNDS = 2                                   # at most this many retrieval rounds per question
FDE = pipeline.PRESETS["FDE-grade (all on)"]     # the single-pass pipeline from Lab 3 (top 3 chunks to the LLM)

# ------------------------------------------------------------------ prompts (built)
CRITIC_PROMPT = """You check search results for an IT helpdesk assistant.
Question: {question}

Passages:
{passages}

Together, do the passages contain everything needed to answer EVERY part of the question?
Reply with JSON only: {{"enough": true or false, "missing": "what is still missing, in a few words (empty if enough)"}}"""

GROUND_PROMPT = """You check an IT helpdesk answer against its sources.
Sources:
{sources}

Answer: {answer}

Is every claim in the answer supported by the sources?
Reply with JSON only: {{"grounded": true or false, "reason": "one short sentence"}}"""


# ================================================================== YOUR 3 TODOs
def parse_critic(text):
    """TODO-1: turn the critic's reply into {"enough": bool, "missing": str}.

    The LLM was asked for JSON like {"enough": false, "missing": "personal laptop rule"}, but replies are messy:
      - it may be wrapped in ```json ... ``` fences
      - "enough" may be the text "yes" / "no" / "true" / "false" instead of a real boolean
      - it may not be JSON at all
    Rule for a broken reply: return {"enough": True, "missing": ""}  (never loop on a broken critic).
    """
    return {"enough": True, "missing": ""}          # starter: the critic is always satisfied


def rewrite_query(index, res, question, missing):
    """TODO-2: ask the LLM for a NEW search query that would find what is `missing`.

    Offline mode is built for you. Online you must:
      1. build a prompt that contains the original question AND what is missing,
      2. call  msg, row = index.llm.chat([{"role": "user", "content": prompt}], op="rewrite")
      3. add the usage row:  res.usage.append(row)
      4. return the new query as a plain string (strip spaces/quotes). If the reply is empty return `question`.
    """
    if index.llm.offline:
        return _offline_rewrite(question, missing)
    return question                                   # starter: no rewrite


def should_continue(rounds_done, critic, max_rounds):
    """TODO-3: decide whether to do another retrieval round.

    rounds_done = how many retrieval rounds have finished (1 after the first round)
    critic      = {"enough": bool, "missing": str}
    Go on only if the critic says NOT enough AND we have not used up max_rounds. Return True or False.
    """
    return False                                      # starter: never loop


# ================================================================== built for you
def route(question):
    """Adaptive routing: a simple lookup takes one pass; a multi-part question gets the critic loop.
    (Stretch: replace this rule with an LLM call.)"""
    q = question.lower()
    multi = len(q.split()) >= 14 or " and " in q or q.count("?") > 1 or ", " in q or ";" in q
    return "complex" if multi else "simple"


def _clauses(question):
    """Split a multi-part question into its parts (offline stand-in for 'decomposition')."""
    parts = re.split(r"[?.;]|,| and ", question)
    asks = [p.strip() for p in parts if re.match(r"\s*(what|when|how|who|which|where|why|can|could|does|do|is|are|will|should)\b", p, re.I)]
    return [p for p in asks if len(set(pipeline.tokens(p))) >= 2]   # only the parts that ASK something


def _clause_cover(index, clause, hits):
    """Best idf-weighted share of the clause's words found in ONE passage."""
    words = list(dict.fromkeys(pipeline.tokens(clause)))
    N = max(1, len(index.chunks))
    w = {t: pipeline.math.log(1 + N / (1 + index.df.get(t, 0))) for t in words}
    total = sum(w.values()) or 1.0
    return max((sum(w[t] for t in words if t in set(index.tok[h["idx"]])) / total for h in hits), default=0.0)


def _offline_critic(index, question, hits):
    """Stand-in without an LLM: is every part of the question answered by at least one passage?"""
    cl = _clauses(question) or [question]
    cover = [(_clause_cover(index, c, hits), c) for c in cl]
    worst = min(cover)
    return {"enough": worst[0] >= 0.5, "missing": "" if worst[0] >= 0.5 else worst[1]}


def _offline_rewrite(question, missing):
    return missing.strip() or question


def critic_passages(index, res, question, hits):
    if index.llm.offline:
        return _offline_critic(index, question, hits)
    passages = "\n".join(f"[{k + 1}] {h['chunk'].text}" for k, h in enumerate(hits))
    msg, row = index.llm.chat([{"role": "user", "content": CRITIC_PROMPT.format(question=question, passages=passages)}],
                              op="critic", json_mode=True)
    res.usage.append(row)
    return parse_critic(msg.content)


def critic_answer(index, res, question, hits):
    """Second critic: is the final answer supported by its sources? Returns (grounded, reason)."""
    if index.llm.offline:
        return True, "offline stand-in: not checked"
    sources = "\n".join(f"[{k + 1}] {h['chunk'].text}" for k, h in enumerate(hits))
    msg, row = index.llm.chat([{"role": "user", "content": GROUND_PROMPT.format(sources=sources, answer=res.answer)}],
                              op="answer check", json_mode=True)
    res.usage.append(row)
    try:
        data = json.loads(msg.content)
        grounded = data.get("grounded", True)
        if isinstance(grounded, str):
            grounded = grounded.strip().lower() in ("true", "yes")
        return bool(grounded), str(data.get("reason", ""))
    except Exception:
        return True, "check reply was not JSON: answer kept"


def _step(res, icon, title, detail=""):
    res.trace.append(dict(icon=icon, title=title, detail=detail))


def _docs(hits):
    return ", ".join(dict.fromkeys(h["chunk"].doc.meta.get("code", h["chunk"].doc.doc_id) for h in hits))


def llm_calls(res):
    return sum(1 for u in res.usage if not str(u.get("operation", "")).startswith("embed"))


def run_single(index, question, audience):
    """The Lab 3 pipeline, one pass. Used for simple questions and as the comparison baseline."""
    res = pipeline.run(index, question, FDE, audience)
    res.trace = [dict(icon="➡️", title="Single pass", detail=f"retrieve + rerank + answer · sources: {_docs(res.hits)}")]
    res.rounds, res.route = 1, "single"
    return res


def run(index, question, audience, max_rounds=MAX_ROUNDS):
    """The agentic loop. Returns a pipeline.Result with extra fields: trace, rounds, route."""
    t0 = time.perf_counter()
    path = route(question)
    if path == "simple":
        res = run_single(index, question, audience)
        res.trace.insert(0, dict(icon="🧭", title="Router", detail="simple question → one pass, no critic"))
        res.route = "simple"
        return res

    cfg = FDE
    res = pipeline.Result(question, cfg)
    res.trace, res.rounds, res.route = [], 0, "complex"
    _step(res, "🧭", "Router", f"multi-part question → critic loop (max {max_rounds} rounds)")
    evidence, query = [], question                  # evidence = passages kept so far (best first)
    while True:
        res.rounds += 1
        sub = pipeline.Result(query, cfg)
        pipeline.retrieve(index, query, cfg, audience, sub)
        res.usage += sub.usage
        res.removed_by_filter = sub.removed_by_filter
        _step(res, "🔎", f"Round {res.rounds}: retrieve", f"query “{query}” → {_docs(sub.hits)}")
        # rerank this round's hits against the query that found them
        cands = sorted(sub.hits, key=lambda h: -h["retrieval_score"])[:10]
        for h in cands:
            h["coverage"] = round(index.coverage(query, h["idx"]), 2)
        tmp = pipeline.Result(query, cfg)
        tmp.hits = cands
        pipeline.rerank(index, query, cfg, tmp)
        res.usage += tmp.usage
        have = {h["idx"] for h in evidence}
        new = [h for h in tmp.hits if h["idx"] not in have]
        take = cfg.top_k if res.rounds == 1 else EXTRA_PER_ROUND   # round 1: the usual top 3; later rounds add a few more
        evidence += new[:take]
        _step(res, "🏅", "Rerank", f"evidence now: {_docs(evidence)}")
        crit = critic_passages(index, res, question, evidence)
        _step(res, "🧐", "Critic", "enough evidence" if crit["enough"] else f"NOT enough — missing: {crit['missing'] or '?'}")
        if not should_continue(res.rounds, crit, max_rounds):
            if not crit["enough"]:
                _step(res, "⏹️", "Stop", "round limit reached: answering with what we have")
            break
        new_query = (rewrite_query(index, res, question, crit["missing"]) or "").strip()
        if not new_query or new_query.lower() == query.lower():
            _step(res, "⏹️", "Stop", "the rewrite did not change the query: answering with what we have")
            break
        _step(res, "✏️", "Rewrite", f"“{new_query}”")
        query = new_query
    top = evidence
    cfg = dataclasses.replace(cfg, top_k=len(evidence))   # the answer step sees all the evidence
    res.hits = top
    pipeline.generate(index, question, cfg, audience, res)
    _step(res, "💬", "Answer", "abstained: evidence too weak" if res.abstained else f"answer with sources: {_docs(top)}")
    if not res.abstained:
        ok, why = critic_answer(index, res, question, top)
        _step(res, "🛡️", "Answer check", "grounded in the sources" if ok else f"NOT grounded ({why}) → handed to a human")
        if not ok:
            res.abstained = True
            res.answer = "I could not verify this answer against the knowledge base. I will route this to a human agent."
    res.timings["total_ms"] = int((time.perf_counter() - t0) * 1000)
    return res
