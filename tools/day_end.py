"""Day End: save XP + lab results into progress/, then commit and push to your fork.

Used two ways:
  1. By the portal's "Day End" button (tools/portal.py calls run_day_end()).
  2. Directly: DAY_END.bat  ->  python tools/day_end.py [S01]
"""
import json
import os
import subprocess
import sys
import threading
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROGRESS = ROOT / "progress"
GIT_LOCK = threading.Lock()  # portal heartbeat and Day End never run git at the same time
SESSIONS = json.loads((ROOT / "tools" / "sessions.json").read_text(encoding="utf-8"))


def load_me():
    f = ROOT / "me.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None


def today_session():
    """Session picked by START_DAY.bat <number> (env ASKIT_DAY). No date check.
    Without a number: the last session whose page exists."""
    n = os.environ.get("ASKIT_DAY", "").strip()
    if n.isdigit():
        key = f"S{int(n):02d}"
        if key in SESSIONS:
            return key
    have = [k for k, v in SESSIONS.items() if (ROOT / v["html"]).exists()]
    return have[-1] if have else "S01"


def run(cmd, timeout=180):
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    return p.returncode, (p.stdout + p.stderr).strip()


def is_trainer_repo():
    """True when 'origin' is the trainer's own repo (not a participant fork).
    Progress must never be pushed there: it would clash with the trainer's real pushes."""
    if os.environ.get("ASKIT_ALLOW_PUSH") == "1":
        return False
    _, url = run(["git", "remote", "get-url", "origin"])
    return "askanilkumar/dxc-agentic-ai" in url.lower()


def lab_results(session):
    """Run pytest for the session's labs; return {lab: {passed, failed, total}}."""
    out = {}
    for lab in SESSIONS[session]["labs"]:
        lab_dir = ROOT / SESSIONS[session]["labs_dir"] / lab
        if not (lab_dir / "tests").exists():
            out[lab] = {"passed": [], "failed": [], "total": 0, "note": "no tests yet"}
            continue
        xml = PROGRESS / f".tmp_{lab}.xml"
        run([sys.executable, "-m", "pytest", str(lab_dir), "-q", f"--junitxml={xml}"], timeout=600)
        passed, failed = [], []
        if xml.exists():
            for tc in ET.parse(xml).getroot().iter("testcase"):
                bad = tc.find("failure") is not None or tc.find("error") is not None
                skip = tc.find("skipped") is not None
                if skip:
                    continue
                (failed if bad else passed).append(tc.get("name"))
            xml.unlink()
        out[lab] = {"passed": passed, "failed": failed, "total": len(passed) + len(failed)}
    return out



EVIDENCE_MAX = 8000  # bytes per evidence file


def _pytest(lab_dir, k=None):
    """Run pytest on one lab (optionally -k filter). Returns {passed:[names], failed:[{name,msg}]}."""
    xml = PROGRESS / f".tmp_{lab_dir.name}.xml"
    cmd = [sys.executable, "-m", "pytest", str(lab_dir), "-q", f"--junitxml={xml}"] + (["-k", k] if k else [])
    run(cmd, timeout=600)
    passed, failed = [], []
    if xml.exists():
        for tc in ET.parse(xml).getroot().iter("testcase"):
            bad = tc.find("failure") if tc.find("failure") is not None else tc.find("error")
            if tc.find("skipped") is not None:
                continue
            if bad is not None:
                msg = (bad.get("message") or "").strip().splitlines()
                failed.append({"name": tc.get("name"), "msg": (msg[0] if msg else "")[:200]})
            else:
                passed.append(tc.get("name"))
        xml.unlink()
    return {"passed": passed, "failed": failed}


def _evidence(lab_dir):
    """Small, readable proof of work: submission notes + eval run summaries (no secrets, no code)."""
    ev = {"files": {}, "eval_runs": []}
    sub = lab_dir / "submission"
    if sub.exists():
        for f in sorted(sub.glob("*.md")):
            ev["files"][f.name] = {"modified": datetime.fromtimestamp(f.stat().st_mtime, timezone.utc).isoformat(),
                                   "text": f.read_text(encoding="utf-8", errors="replace")[:EVIDENCE_MAX]}
    for rel in ("evals/runs.json", "evals_agentic/runs.json"):
        f = lab_dir / rel
        if f.exists():
            try:
                for r in json.loads(f.read_text(encoding="utf-8")):
                    ev["eval_runs"].append({k: r.get(k) for k in (
                        "run_at", "config", "model", "pass_rate", "hit_at_1", "recall_at_k", "mrr", "faithfulness",
                        "correctness", "multi_part_pass", "avg_llm_calls", "avg_cost_usd", "cost_usd", "avg_latency_ms",
                        "loop_rate") if k in r})
            except ValueError:
                pass
    ev["eval_runs"] = ev["eval_runs"][-12:]
    return ev


def submit_lab(session, key):
    """'I completed the lab' button: run that lab's tests, gather evidence, save progress/<S>_lab_<key>.json, push.
    Honest mode: always saves and pushes, passing or not."""
    me = load_me()
    if not me:
        return False, [{"ok": False, "step": "Identity missing", "detail": "run SETUP.bat first (creates me.json)"}], {}
    spec = (SESSIONS.get(session) or {}).get("lab_keys", {}).get(key)
    if not spec:
        return False, [{"ok": False, "step": "Unknown lab", "detail": f"{session}/{key}"}], {}
    lab_dir = ROOT / SESSIONS[session]["labs_dir"] / spec["lab"]
    if not lab_dir.exists():
        return False, [{"ok": False, "step": "Lab folder not found", "detail": str(lab_dir)}], {}
    PROGRESS.mkdir(exist_ok=True)
    res = _pytest(lab_dir, spec.get("k"))
    stretch = _pytest(lab_dir, spec["stretch_k"]) if spec.get("stretch_k") else None
    f = PROGRESS / f"{session}_lab_{key}.json"
    try:
        attempts = json.loads(f.read_text(encoding="utf-8")).get("attempts", 0) + 1
    except (OSError, ValueError):
        attempts = 1
    out = {"session": session, "lab": key, "title": spec.get("title", key), "folder": spec["lab"], "participant": me,
           "submitted_at": datetime.now(timezone.utc).isoformat(), "attempts": attempts,
           "passed": res["passed"], "failed": res["failed"], "total": len(res["passed"]) + len(res["failed"]),
           "stretch": stretch, "evidence": _evidence(lab_dir)}
    f.write_text(json.dumps(out, indent=2), encoding="utf-8")
    steps = [{"ok": True, "step": "Tests run", "detail": f"{len(res['passed'])}/{out['total']} passing"
              + (f" · stretch {len(stretch['passed'])}/{len(stretch['passed']) + len(stretch['failed'])}" if stretch else "")}]
    with GIT_LOCK:
        ok, steps = _commit_and_push(session, me, steps, f"{session} {key} submitted - {me.get('name', '')}")
    return ok, steps, {"passed": len(res["passed"]), "total": out["total"], "failed": res["failed"][:6],
                       "stretch": None if not stretch else [len(stretch["passed"]), len(stretch["passed"]) + len(stretch["failed"])]}


def aggregate_labs(session):
    """Build progress/<S>_lab.json (used by My Status) from the per-lab submissions."""
    labs = {}
    for key in SESSIONS[session].get("lab_keys", {}):
        f = PROGRESS / f"{session}_lab_{key}.json"
        if f.exists():
            d = json.loads(f.read_text(encoding="utf-8"))
            labs[d.get("title", key)] = {"passed": d["passed"], "failed": [x["name"] for x in d["failed"]], "total": d["total"]}
    return labs


def find_downloaded_xp(session):
    """Fallback: XP file the browser downloaded (page not opened via START_DAY.bat)."""
    dl = Path.home() / "Downloads"
    files = sorted(dl.glob(f"askit_{session}_xp*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    return json.loads(files[0].read_text(encoding="utf-8")) if files else None


def run_day_end(session=None, xp_payload=None):
    steps = []
    me = load_me()
    if not me:
        return False, [{"ok": False, "step": "Identity missing", "detail": "run SETUP.bat first (creates me.json)"}]
    session = session or today_session()
    if session not in SESSIONS:
        return False, [{"ok": False, "step": "Unknown session", "detail": session}]
    PROGRESS.mkdir(exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()

    # 1. XP
    xp = xp_payload or find_downloaded_xp(session)
    xp_file = PROGRESS / f"{session}_xp.json"
    if xp:
        xp["participant"] = me
        xp["saved_at"] = now
        xp_file.write_text(json.dumps(xp, indent=2), encoding="utf-8")
        steps.append({"ok": True, "step": "XP saved", "detail": f"{xp.get('xp_total', 0)} XP -> progress/{xp_file.name}"})
    elif xp_file.exists():
        steps.append({"ok": True, "step": "XP kept", "detail": "using earlier saved file"})
    else:
        steps.append({"ok": False, "step": "No XP found", "detail": "click Day End in the session page"})

    # 2. Labs: results come from the "I completed the lab" buttons (progress/<S>_lab_<key>.json)
    labs = aggregate_labs(session) if SESSIONS[session].get("lab_keys") else lab_results(session)
    lab_file = PROGRESS / f"{session}_lab.json"
    lab_file.write_text(json.dumps({"session": session, "participant": me, "saved_at": now, "labs": labs}, indent=2), encoding="utf-8")
    p = sum(len(v["passed"]) for v in labs.values())
    t = sum(v["total"] for v in labs.values())
    n_sub, n_all = len(labs), len(SESSIONS[session].get("lab_keys", {}))
    steps.append({"ok": n_sub > 0 or n_all == 0, "step": "Labs", "detail": f"{n_sub}/{n_all} labs submitted, {p}/{t} challenges passing"
                  + ("" if n_sub == n_all else " - press 'I completed the lab' on the lab pages you skipped")})

    # 3. Git commit + push
    with GIT_LOCK:
        return _commit_and_push(session, me, steps)


def _commit_and_push(session, me, steps, message=None):
    lab_roots = sorted({v["labs_dir"] for v in SESSIONS.values() if v.get("labs_dir") and (ROOT / v["labs_dir"]).exists()})
    run(["git", "add", "progress", "teams", "me.json", *lab_roots])
    code, _ = run(["git", "diff", "--cached", "--quiet"])
    if code != 0:
        code, msg = run(["git", "commit", "-m", message or f"{session} day end - {me.get('name', '')}"])
        if code != 0:
            steps.append({"ok": False, "step": "Commit failed", "detail": msg[-200:]})
            return False, steps
        steps.append({"ok": True, "step": "Committed"})
    else:
        steps.append({"ok": True, "step": "Nothing new to commit"})
    if is_trainer_repo():
        steps.append({"ok": True, "step": "Trainer copy: progress saved locally, NOT pushed"})
        return True, steps
    code, msg = run(["git", "push", "origin", "HEAD"])
    if code != 0:  # fork has newer commits (e.g. pushed from another place): merge them, keep my files, retry once
        run(["git", "pull", "--no-edit", "-X", "ours", "origin", "main"])
        code, msg = run(["git", "push", "origin", "HEAD"])
    if code != 0:
        steps.append({"ok": False, "step": "Push failed", "detail": msg[-200:] + " - call the trainer"})
        return False, steps
    steps.append({"ok": True, "step": "Pushed to your GitHub fork"})
    return True, steps


def push_heartbeat(session):
    """Commit + push only progress/<session>_live.json. Silent on failure (retried next cycle)."""
    f = f"progress/{session}_live.json"
    if is_trainer_repo():
        return True  # trainer/test copy: never push progress to the trainer repo
    if not (ROOT / f).exists() or not GIT_LOCK.acquire(timeout=5):
        return False
    try:
        run(["git", "add", f])
        code, _ = run(["git", "diff", "--cached", "--quiet", "--", f])
        if code == 0:
            return True  # nothing changed
        run(["git", "commit", "-q", "-m", f"{session} heartbeat", "--", f])
        code, _ = run(["git", "push", "-q", "origin", "HEAD"], timeout=60)
        if code != 0:
            run(["git", "pull", "-q", "--no-edit", "-X", "ours", "origin", "main"], timeout=60)
            code, _ = run(["git", "push", "-q", "origin", "HEAD"], timeout=60)
        return code == 0
    finally:
        GIT_LOCK.release()

if __name__ == "__main__":
    ok, steps = run_day_end(sys.argv[1] if len(sys.argv) > 1 else None)
    for s in steps:
        print(("[OK]  " if s["ok"] else "[!!]  ") + s["step"] + (" - " + s["detail"] if s.get("detail") else ""))
    print("\nDAY END COMPLETE" if ok else "\nDAY END NOT COMPLETE - call the trainer")
    sys.exit(0 if ok else 1)
