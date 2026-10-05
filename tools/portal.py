"""Local course portal (runs on YOUR VM only, http://localhost:8765).

- Serves the session pages (DayNN/Content) and labs (DayNN/Labs)
- /api/me       -> your identity from me.json
- /me           -> "My Status" page: your XP, quiz, labs and points for every session
- /api/dayend   -> Day End button: saves XP + lab results, commits and pushes
Started by START_DAY.bat. Close the window to stop it.
"""
import html as _html
import json
import posixpath
import re
import sys
import threading
import time
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from datetime import datetime, timezone
from pathlib import Path

from day_end import PROGRESS, ROOT, SESSIONS, aggregate_labs, load_me, push_heartbeat, run_day_end, submit_lab, today_session

PORT = 8765
HEARTBEAT_PUSH_MIN = 5  # live progress pushed to GitHub every 5 min (feeds the trainer dashboard)
LIVE_SESSIONS = set()


class Server(ThreadingHTTPServer):
    allow_reuse_address = False  # on Windows this makes a 2nd copy fail cleanly instead of sharing the port
    daemon_threads = True


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(ROOT), **kw)

    def log_message(self, fmt, *args):  # keep the console quiet
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")  # always show the latest content
        super().end_headers()

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/me":
            return self._json(load_me() or {}, 200 if load_me() else 404)
        if self.path in ("/", "/index.html"):
            return self._index()
        if self.path.split("?")[0] == "/me":
            return self._me()
        # only serve session pages and labs (no secrets like .env)
        clean = posixpath.normpath(self.path.split("?")[0])
        if not re.match(r"^/Day\d+/(Content|Labs)/", clean):
            return self._json({"error": "not found"}, 404)
        return super().do_GET()

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        try:
            payload = json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            return self._json({"error": "bad json"}, 400)
        if self.path == "/api/heartbeat":
            return self._heartbeat(payload)
        if self.path == "/api/labdone":
            print(f"Lab submit: {payload.get('session')} {payload.get('lab')} ... (running tests, ~20-60 s)")
            ok, steps, summary = submit_lab(payload.get("session"), payload.get("lab"))
            for st in steps:
                print(("  [OK] " if st["ok"] else "  [!!] ") + st["step"], st.get("detail", ""))
            return self._json({"ok": ok, "steps": steps, "summary": summary})
        if self.path != "/api/dayend":
            return self._json({"error": "not found"}, 404)
        print(f"Day End requested for {payload.get('session')} ... (this can take a minute)")
        ok, steps = run_day_end(payload.get("session"), payload)
        for s in steps:
            print(("  [OK] " if s["ok"] else "  [!!] ") + s["step"], s.get("detail", ""))
        return self._json({"ok": ok, "steps": steps})

    def _heartbeat(self, p):
        session = p.get("session")
        if session not in SESSIONS:
            return self._json({"ok": False}, 400)
        p["participant"] = load_me()
        p["updated_at"] = datetime.now(timezone.utc).isoformat()
        PROGRESS.mkdir(exist_ok=True)
        (PROGRESS / f"{session}_live.json").write_text(json.dumps(p, indent=2), encoding="utf-8")
        LIVE_SESSIONS.add(session)
        return self._json({"ok": True})

    def _me(self):
        """My Status: reads only your own progress/*.json files (no internet needed)."""
        me = load_me() or {}
        esc = _html.escape

        def rd(name):
            try:
                return json.loads((PROGRESS / name).read_text(encoding="utf-8"))
            except (OSError, ValueError):
                return {}

        rows, tot_pts, tot_xp, tot_pass, tot_lab = "", 0, 0, 0, 0
        details = ""
        for k, v in SESSIONS.items():
            xp, live = rd(f"{k}_xp.json"), rd(f"{k}_live.json")
            lab = {"labs": aggregate_labs(k)} if v.get("lab_keys") else rd(f"{k}_lab.json")
            if not (xp or lab.get("labs") or live):
                rows += f'<tr class="dim"><td>{k}</td><td>{esc(v["title"])}</td><td colspan="6">not started</td></tr>'
                continue
            xpv = xp.get("xp_total", live.get("xp_total", 0)) or 0
            q = xp.get("quiz") or {}
            qn, qc = len(q), sum(1 for a in q.values() if isinstance(a, dict) and a.get("correct"))
            labs = lab.get("labs", {})
            passed = sum(len(x.get("passed", [])) for x in labs.values())
            total = sum(x.get("total", 0) for x in labs.values())
            pts = xpv + 10 * passed
            tot_pts, tot_xp, tot_pass, tot_lab = tot_pts + pts, tot_xp + xpv, tot_pass + passed, tot_lab + total
            mins = xp.get("active_minutes", live.get("active_minutes", 0)) or 0
            done = "&#9989;" if xp else "&#10060; not yet"
            rows += (f"<tr><td>{k}</td><td>{esc(v['title'])}</td><td>{xpv}</td><td>{qc}/{qn}</td>"
                     f"<td>{passed}/{total}</td><td>{mins}</td><td>{done}</td><td><b>{pts}</b></td></tr>")
            for name, x in labs.items():
                if x.get("failed"):
                    details += (f"<p><b>{k} &middot; {esc(name)}</b> &mdash; still to do: "
                                + ", ".join(esc(f) for f in x["failed"]) + "</p>")
        if not details:
            details = "<p>Nothing pending. &#127881;</p>"
        page = f"""<!doctype html><meta charset="utf-8"><title>My Status</title>
<body style="font-family:Segoe UI,system-ui;max-width:1000px;margin:30px auto;font-size:20px;line-height:1.4">
<style>table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #bbb;padding:8px 10px;text-align:left}}
th{{background:#eef}}tr.dim td{{color:#888}}</style>
<h1>&#128202; My Status</h1>
<p><b>{esc(str(me.get('name', 'participant')))}</b> &middot; Team {esc(str(me.get('team', '?')))} &middot; GitHub: {esc(str(me.get('github_user', '?')))}</p>
<p><b>Total: {tot_pts} points</b> &nbsp;({tot_xp} XP + 10 &times; {tot_pass} challenges passed of {tot_lab})</p>
<table><tr><th>Session</th><th>Topic</th><th>XP</th><th>Quiz</th><th>Challenges</th><th>Active min</th><th>Day End</th><th>Points</th></tr>{rows}</table>
<h2>Still to do</h2>{details}
<p style="font-size:16px;color:#555">Shows what is saved on your VM. Press <b>I completed the lab</b> on each lab page and <b>Day End</b> on the last page of the session. AhaSlides quiz scores are added by the trainer on the class leaderboard. <a href="/">Home</a></p>
</body>"""
        body = page.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _index(self):
        me = load_me() or {}
        cur = today_session()
        rows = "".join(
            f'<li><a href="/{v["html"]}">{k} · {v["title"]}</a> <small>{v["date"]}</small>{" ← today" if k == cur else ""}</li>'
            for k, v in SESSIONS.items() if (ROOT / v["html"]).exists()
        )
        html = f"""<!doctype html><meta charset="utf-8"><title>AskIT Portal</title>
<body style="font-family:Segoe UI,system-ui;max-width:700px;margin:40px auto;font-size:20px">
<h1>AskIT Program</h1><p>Welcome, <b>{me.get('name', 'participant')}</b> (Team {me.get('team', '?')})</p>
<ul>{rows}</ul><p><a href="/me">&#128202; My Status</a></p></body>"""
        body = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def heartbeat_pusher():
    while True:
        time.sleep(HEARTBEAT_PUSH_MIN * 60)
        for s in list(LIVE_SESSIONS):
            try:
                ok = push_heartbeat(s)
                print(time.strftime("%H:%M"), "progress synced" if ok else "progress sync will retry")
            except Exception as e:  # noqa: BLE001  never crash the portal
                print("sync error (will retry):", e)


if __name__ == "__main__":
    cur = today_session()
    try:
        srv = Server(("127.0.0.1", PORT), Handler)
    except OSError:
        print("Portal is already running - opening your browser.")
        webbrowser.open(f"http://localhost:{PORT}/{SESSIONS[cur]['html']}")
        sys.exit(0)
    threading.Thread(target=heartbeat_pusher, daemon=True).start()
    url = f"http://localhost:{PORT}/{SESSIONS[cur]['html']}"
    if not (ROOT / SESSIONS[cur]["html"]).exists():
        url = f"http://localhost:{PORT}/"
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    print(f"AskIT portal running at http://localhost:{PORT}  (keep this window open; close it to stop)")
    print(f"My Status page: http://localhost:{PORT}/me")
    srv.serve_forever()
