"""Starts the personal Outlook connection exactly as connections.yaml tells the AI to set it up (the Mac block on a
Mac, the Windows block on Windows), and checks it: it answers, it offers reading tools only, and its log-in opens
Microsoft's sign-in page with a one-time code. Nobody signs in: that last step needs a real Hotmail account.
Run by .github/workflows/kit.yml. Needs Node.js and the internet."""
import json
import os
import queue
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "tests"))
from test_connections_yaml import DATA  # noqa: E402

CHANGES = re.compile(r"(^|-)(send|create|update|delete|move|copy|forward|reply|add|accept|decline|cancel)(-|$)")


def blocks():
    """{"mac": {...}, "windows": {...}} from the notes of every personal Outlook route; they must all agree."""
    found = []
    for sid in ("outlook-calendar", "outlook-mail"):
        for r in DATA["sources"][sid]["routes"]:
            if r["type"] == "local":
                pair = {}
                for system in ("Mac", "Windows"):
                    at = r["notes"].index(f'{system}: "outlook": ') + len(f'{system}: "outlook": ')
                    pair[system.lower()] = json.JSONDecoder().raw_decode(r["notes"][at:])[0]
                found.append(pair)
    assert found and all(f == found[0] for f in found), "the Outlook routes disagree"
    return found[0]


def main():
    block = blocks()["windows" if os.name == "nt" else "mac"]
    assert "--read-only" in block["args"], block
    print("Starting:", block["command"], " ".join(block["args"]))
    p = subprocess.Popen([block["command"], *block["args"]], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, text=True, encoding="utf-8")
    lines = queue.Queue()
    threading.Thread(target=lambda: [lines.put(line) for line in p.stdout], daemon=True).start()
    threading.Thread(target=lambda: [None for _ in p.stderr], daemon=True).start()

    def ask(n, method, params=None, wait=240):
        p.stdin.write(json.dumps({"jsonrpc": "2.0", "id": n, "method": method, "params": params or {}}) + "\n")
        p.stdin.flush()
        end = time.time() + wait
        while time.time() < end:
            try:
                message = json.loads(lines.get(timeout=1))
            except (queue.Empty, ValueError):
                continue
            if message.get("id") == n:
                return message["result"]
        raise SystemExit(f"no answer to {method}")

    try:
        info = ask(1, "initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                     "clientInfo": {"name": "brainos-kit-check", "version": "1"}})
        print("It answers:", info["serverInfo"])
        p.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
        p.stdin.flush()
        tools = [t["name"] for t in ask(2, "tools/list")["tools"]]
        print(len(tools), "tools:", ", ".join(tools))
        for need in ("login", "verify-login", "list-calendar-events", "list-mail-messages", "get-mail-message"):
            assert need in tools, f"missing {need}"
        changing = [t for t in tools if CHANGES.search(t) and t not in ("remove-account",)]
        assert not changing, f"tools that change things: {changing}"
        text = json.dumps(ask(3, "tools/call", {"name": "login", "arguments": {}}, wait=90))
        assert "login.microsoft.com/device" in text, text
        assert re.search(r"enter the code [A-Z0-9]{6,}", text), text
        print("Log-in opens Microsoft's sign-in page with a one-time code.")
    finally:
        p.terminate()
    print("Outlook connection: OK up to the sign-in.")


if __name__ == "__main__":
    main()
