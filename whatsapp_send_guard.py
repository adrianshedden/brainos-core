#!/usr/bin/env python3
"""The WhatsApp send guard: a check Claude Code runs before every WhatsApp action (live WhatsApp module).

Optional, and never part of setup: see WHATSAPP-LIVE.md. `whatsapp_live.py` copies this file into the brain's
`scripts/` folder and adds it to Claude Code's own settings as a PreToolUse hook, on the Beeper connection and
on commands (for wacli):

    python3 <brain>/scripts/whatsapp_send_guard.py --mode read|write [--cap 20]

What it decides:
- Reading goes ahead as normal: Beeper's search, list, get and read tools; wacli with --read-only (and
  `wacli sync --once`, which only refreshes the copy on the computer). Commands that do not use wacli are
  not its business and go ahead as normal.
- Sending, in read mode: refused.
- Sending, in write mode: Claude Code stops and shows the person the chat and the exact words, and asks.
  Nothing goes until they click yes. At most <cap> send requests a day (fewer sends, less risk of a ban).
  A send whose words it cannot show is refused. With wacli, only `send text` with --to and --message.
- Anything else (archive, edit, delete, reminders, pairing, or a tool it does not know): refused.
- If it cannot read what it was given, it refuses. It never fails open.

The daily count is kept in `whatsapp-send-requests.jsonl` beside this file: the date, the chat and the length of
each request, never the words. Standard library only; it never uses the network."""
import argparse
import json
import re
import shlex
import sys
from datetime import date
from pathlib import Path

LOG = Path(__file__).resolve().with_name("whatsapp-send-requests.jsonl")
DEFAULT_CAP = 20
# Words in a tool's name that mean it changes something, matched word by word (send_message, sendMessage). They
# are checked before the reading words, so a name such as get_and_send can never pass as a read.
CHANGES = ("edit", "delete", "remove", "archive", "unarchive", "remind", "reminder", "react", "reaction", "create",
           "update", "mark", "mute", "unmute", "pin", "unpin", "draft", "focus", "open", "upload", "forward",
           "post", "reply", "leave", "add", "set", "clear", "block", "invite", "join", "write", "save")
READS = ("search", "list", "get", "read", "find", "fetch", "download", "view", "show")
CHAT_KEYS = ("chatID", "chatId", "chat_id", "chat", "chatName", "to")
TEXT_KEYS = ("text", "message", "body", "content")
SHELL_TOOLS = ("Bash", "PowerShell")


def decision(kind, reason):
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": kind,
                                   "permissionDecisionReason": reason}}


def refuse(reason):
    return decision("deny", reason)


def short_name(tool):
    """`mcp__beeper__send_message` -> `send_message`. Other names are returned whole."""
    parts = tool.split("__", 2)
    return parts[2] if len(parts) == 3 and parts[0] == "mcp" else tool


def words(name):
    """`send_message` and `sendMessage` -> ["send", "message"]."""
    return [w.lower() for w in re.split(r"[_\-\s.]+|(?<=[a-z])(?=[A-Z])", name) if w]


def first(values, keys):
    for key in keys:
        value = values.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def requests_today(log, today):
    try:
        lines = log.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return 0
    count = 0
    for line in lines:
        try:
            if json.loads(line).get("date") == today:
                count += 1
        except (ValueError, AttributeError):
            continue
    return count


READ_ONLY_REASON = ("WhatsApp is read-only. Sending is a separate yes the person has to give (WHATSAPP-LIVE.md). "
                    "Show them the draft in the chat instead.")


def send_request(chat, text, mode, cap, log, today):
    """The answer for one send: refused in read mode; in write mode, Claude Code asks, showing every word."""
    if mode != "write":
        return refuse(READ_ONLY_REASON)
    if not text:
        return refuse("The WhatsApp guard cannot show the person the exact words, so this message is not sent.")
    try:
        sent_today = requests_today(log, today)
    except OSError:
        return refuse("The WhatsApp guard could not read its daily count, so this message is not sent.")
    if sent_today >= cap:
        return refuse(f"That is {cap} WhatsApp messages today, the most this brain allows in a day. "
                      "Sending a lot can get a number banned. Try again tomorrow, or send it yourself.")
    try:
        with open(log, "a", encoding="utf-8") as f:
            f.write(json.dumps({"date": today, "chat": chat or "", "length": len(text)}) + "\n")
    except OSError:
        return refuse("The WhatsApp guard could not keep its daily count, so this message is not sent.")
    return decision("ask", f"Send this WhatsApp message?\nTo: {chat or 'the chat named in the request'}\n"
                           f"Message: {text}\nCheck every word. Click yes only if it is right. "
                           "If not, say no and tell your AI what to change.")


def flag(args, name):
    """The value of --name VALUE or --name=VALUE in <args>, or None."""
    for i, arg in enumerate(args):
        if arg == name and i + 1 < len(args):
            return args[i + 1]
        if arg.startswith(name + "="):
            return arg[len(name) + 1:]
    return None


def judge_wacli(command, mode, cap, log, today):
    """For a command line (the Bash or PowerShell tool): None when it does not use wacli, or when it only reads
    (with --read-only, or `sync --once`, which refreshes the copy on the computer). One `send text` with --to and
    --message is a send. Anything else that uses wacli is refused."""
    if "wacli" not in command.lower():
        return None
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        return refuse("The WhatsApp guard could not read this command, so it is refused.")
    at = [i for i, tok in enumerate(tokens) if re.split(r"[\\/]", tok)[-1].lower() in ("wacli", "wacli.exe")]
    if len(at) != 1 or re.search(r"[;&|`]|\$\(", command):
        return refuse("Use wacli once per command, on its own, so the guard can check it.")
    before, args = tokens[:at[0]], tokens[at[0] + 1:]
    words_ = [a for a in args if not a.startswith("-")]
    if "send" in words_:
        if words_[words_.index("send"):][1:2] != ["text"]:
            return refuse("Only plain text messages can be sent from your brain (wacli send text).")
        return send_request(flag(args, "--to"), flag(args, "--message"), mode, cap, log, today)
    if "--read-only" in args or "WACLI_READONLY=1" in before or "WACLI_READONLY=1" in command:
        return None
    if words_[:1] == ["sync"] and "--once" in args and "--follow" not in args:
        return None
    return refuse("Use wacli with --read-only to read. Anything that changes WhatsApp is refused, and pairing "
                  "(wacli auth) is for the person to run themselves.")


def judge(payload, mode, cap=DEFAULT_CAP, log=LOG, today=None):
    """The hook's answer for one call: None to let it go ahead as normal, otherwise the decision to print."""
    today = today or date.today().isoformat()
    if not isinstance(payload, dict):
        return refuse("The WhatsApp guard could not read this request, so it is refused.")
    tool = payload.get("tool_name")
    if not isinstance(tool, str) or not tool:
        return refuse("The WhatsApp guard could not read this request, so it is refused.")
    args = payload.get("tool_input") if isinstance(payload.get("tool_input"), dict) else {}
    if tool in SHELL_TOOLS:
        command = args.get("command")
        if not isinstance(command, str):
            return None
        return judge_wacli(command, mode, cap, log, today)
    parts = words(short_name(tool))
    sends = any(w.startswith("send") for w in parts)
    changes = any(w in CHANGES for w in parts)
    if sends and not changes:
        return send_request(first(args, CHAT_KEYS), first(args, TEXT_KEYS), mode, cap, log, today)
    if sends or changes:
        return refuse("This WhatsApp action changes something (for example archives, edits or deletes). "
                      "Your brain only reads WhatsApp, and sends only with your yes.")
    if parts and parts[0] in READS:
        return None
    return refuse(f"The WhatsApp guard does not know '{short_name(tool)}', so it is refused. Only reading and "
                  "approved sending are allowed.")


def main(argv=None, stdin=None, out=None):
    parser = argparse.ArgumentParser(description="The WhatsApp send guard for Claude Code (WHATSAPP-LIVE.md).")
    parser.add_argument("--mode", choices=("read", "write"), default="read")
    parser.add_argument("--cap", type=int, default=DEFAULT_CAP)
    parser.add_argument("--log", type=Path, default=LOG)
    args = parser.parse_args(argv)
    stdin = stdin or sys.stdin
    out = out or sys.stdout
    try:
        payload = json.load(stdin)
    except (ValueError, OSError):
        payload = None
    answer = judge(payload, args.mode, cap=args.cap, log=args.log)
    if answer is not None:
        out.write(json.dumps(answer) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
