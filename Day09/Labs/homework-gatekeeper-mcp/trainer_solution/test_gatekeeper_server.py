"""Starts the Gatekeeper MCP server, lists its tools and calls each one. Prints PASS or FAIL per check."""
import asyncio
import os
import subprocess
import sys
import time

from fastmcp import Client
from fastmcp.client.transports import StdioTransport

HERE = os.path.dirname(os.path.abspath(__file__))
SERVER = os.path.join(HERE, "gatekeeper_server.py")
results = []


def report(name, ok, detail=""):
    results.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"   <- {detail}" if not ok and detail else ""))


async def call(client, tool, args):
    """Return (is_error, data)."""
    r = await client.call_tool(tool, args, raise_on_error=False)
    return r.is_error, r.data


async def run_checks(client, label):
    tools = {t.name: t for t in await client.list_tools()}
    report(f"[{label}] lists exactly 2 tools", set(tools) == {"route_ticket", "needs_approval"}, str(sorted(tools)))
    report(f"[{label}] every tool has a description", all((t.description or "").strip() for t in tools.values()))

    for text, team in [("VPN error 809 since morning", "Network"),
                       ("Phishing email asked for my password", "Security"),
                       ("Cannot download files", "General")]:
        err, data = await call(client, "route_ticket", {"text": text})
        report(f"[{label}] route_ticket({text!r}) -> {team}", (not err) and data == team, f"got {data!r}")

    for args, exp in [(("reset_password", "EMP-1002", 10), {"approval": True, "approver": "service desk lead"}),
                      (("search_kb", "EMP-1002", 10), {"approval": False, "approver": "none"}),
                      (("update_ticket", "EMP-1001", 10), {"approval": True, "approver": "it manager"})]:
        err, data = await call(client, "needs_approval", dict(zip(("action", "user_id", "hour"), args)))
        report(f"[{label}] needs_approval{args} -> {exp['approval']}/{exp['approver']}", (not err) and data == exp, f"got {data!r}")

    err, _ = await call(client, "needs_approval", {"action": "delete_user", "user_id": "EMP-1002", "hour": 10})
    report(f"[{label}] unknown action -> clean error", err)
    err, _ = await call(client, "route_ticket", {"text": ""})
    report(f"[{label}] blank text -> clean error", err)


async def main():
    quiet = open(os.devnull, "w")  # hide the server's own log lines; we only want PASS/FAIL
    async with Client(StdioTransport(command=sys.executable, args=[SERVER], log_file=quiet)) as client:
        await run_checks(client, "stdio")

    proc = subprocess.Popen([sys.executable, SERVER, "--http"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        ok = False
        for _ in range(40):  # wait up to ~10 s for the port
            try:
                async with Client("http://127.0.0.1:8778/mcp") as client:
                    await run_checks(client, "http")
                    ok = True
                    break
            except Exception:
                await asyncio.sleep(0.25)
        if not ok:
            report("[http] server answers on port 8778", False, "could not connect")
    finally:
        proc.terminate()


asyncio.run(main())
passed = sum(results)
print(f"\n{passed}/{len(results)} passed")
sys.exit(0 if passed == len(results) else 1)
