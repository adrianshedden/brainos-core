#!/usr/bin/env python3
"""Switch the live WhatsApp guard in Claude Code on, up, off, or out (optional module: WHATSAPP-LIVE.md).

    python3 kit/whatsapp_live.py <brain> status
    python3 kit/whatsapp_live.py <brain> read   [--apply]   reading only; sending is refused
    python3 kit/whatsapp_live.py <brain> write  [--apply]   sending allowed, each message asked for, word for word
    python3 kit/whatsapp_live.py <brain> off    [--apply]   no WhatsApp tool can be used at all
    python3 kit/whatsapp_live.py <brain> remove [--apply]   take out everything this script added

Without --apply it only says what it would change, and changes nothing. With --apply it first saves a copy of
the settings file beside it, then writes. It changes only what it added itself, in Claude Code's own settings
(`~/.claude/settings.json`, or --settings), never anything else in that file, and copies the guard
(`whatsapp_send_guard.py`) into the brain's `scripts/` folder. It does not install Beeper or add the Beeper
connection: WHATSAPP-LIVE.md does those, with the person's yes. Standard library only; no network.

What it adds, for the Beeper connection (called beeper, or --server) and for wacli commands:
- read:   the guard (a check before each WhatsApp action) in read mode, and rules that refuse sending and
          changes (archive, edit, delete, reminders).
- write:  the guard in write mode, a rule that makes Claude Code ask before every send (it asks in every
          permission mode), and the same refusals for changes.
- off:    one rule that refuses every WhatsApp tool. The guard comes out.
- remove: nothing of its own is left. Remove the connection itself as WHATSAPP-LIVE.md says."""
import argparse
import json
import os
import shlex
import shutil
import sys
from datetime import datetime
from pathlib import Path, PureWindowsPath

KIT = Path(__file__).resolve().parent
GUARD = "whatsapp_send_guard.py"
MODES = ("read", "write", "off", "remove")


def rules(server):
    always = [f"mcp__{server}__*{verb}*" for verb in ("archive", "delete", "edit", "remind")]
    sends = [f"mcp__{server}__send*", "Bash(wacli send *)", "Bash(wacli * send *)"]
    return {
        "read": {"deny": always + sends, "ask": []},
        "write": {"deny": always, "ask": sends},
        "off": {"deny": [f"mcp__{server}", "Bash(wacli *)"], "ask": []},
        "remove": {"deny": [], "ask": []},
    }


def every_rule(server):
    out = set()
    for mode in rules(server).values():
        out.update(mode["deny"] + mode["ask"])
    return out


def guard_command(guard, mode, windows):
    if windows:
        return f'py "{PureWindowsPath(str(guard)).as_posix()}" --mode {mode}'
    return f"python3 {shlex.quote(str(guard))} --mode {mode}"


def is_ours(hook_group):
    return isinstance(hook_group, dict) and any(
        isinstance(h, dict) and GUARD in str(h.get("command", "")) for h in hook_group.get("hooks", []) or [])


def load(settings):
    if not settings.exists():
        return {}
    data = json.loads(settings.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("it is not a settings object")
    return data


def current_mode(data, server):
    """read, write, off or none, from what this script left in the settings."""
    for group in (data.get("hooks", {}) or {}).get("PreToolUse", []) or []:
        if is_ours(group):
            command = " ".join(str(h.get("command", "")) for h in group["hooks"])
            return "write" if "--mode write" in command else "read"
    if f"mcp__{server}" in ((data.get("permissions", {}) or {}).get("deny", []) or []):
        return "off"
    return "none"


def updated(data, mode, server, guard, windows):
    """A new settings object with this script's parts set for <mode>, and everything else exactly as it was."""
    new = json.loads(json.dumps(data))
    ours = every_rule(server)
    perms = new.setdefault("permissions", {})
    for key in ("deny", "ask"):
        kept = [r for r in perms.get(key, []) or [] if r not in ours]
        kept += [r for r in rules(server)[mode][key] if r not in kept]
        if kept:
            perms[key] = kept
        else:
            perms.pop(key, None)
    if not perms:
        new.pop("permissions")
    hooks = new.setdefault("hooks", {})
    pre = [g for g in hooks.get("PreToolUse", []) or [] if not is_ours(g)]
    if mode in ("read", "write"):
        for matcher in (f"mcp__{server}__.*", "Bash|PowerShell"):
            pre.append({"matcher": matcher,
                        "hooks": [{"type": "command", "command": guard_command(guard, mode, windows)}]})
    if pre:
        hooks["PreToolUse"] = pre
    else:
        hooks.pop("PreToolUse", None)
    if not hooks:
        new.pop("hooks")
    return new


def changes(old, new, server):
    """Plain lines saying what differs, for the person."""
    lines = []
    old_perms, new_perms = old.get("permissions", {}) or {}, new.get("permissions", {}) or {}
    for key, verb in (("deny", "refuse"), ("ask", "always ask before")):
        before, after = set(old_perms.get(key, []) or []), set(new_perms.get(key, []) or [])
        for rule in sorted(after - before):
            lines.append(f"Add a rule to {verb}: {rule}")
        for rule in sorted(before - after):
            lines.append(f"Take out the rule to {verb}: {rule}")
    old_mode, new_mode = current_mode(old, server), current_mode(new, server)
    old_guard = [g for g in (old.get("hooks", {}) or {}).get("PreToolUse", []) or [] if is_ours(g)]
    new_guard = [g for g in (new.get("hooks", {}) or {}).get("PreToolUse", []) or [] if is_ours(g)]
    if old_guard != new_guard:
        if new_guard:
            lines.append(f"Set the WhatsApp guard to {new_mode} mode: {new_guard[0]['hooks'][0]['command']}")
        else:
            lines.append("Take out the WhatsApp guard.")
    return lines


def run(brain, mode, settings, server="beeper", apply=False, windows=None, out=print, now=None):
    windows = os.name == "nt" if windows is None else windows
    brain = Path(brain).expanduser().resolve()
    if not (brain / "brain.yaml").is_file():
        out(f"{brain} is not a brain folder (no brain.yaml). Nothing was changed.")
        return 1
    settings = Path(settings).expanduser()
    try:
        data = load(settings)
    except (ValueError, OSError) as e:
        out(f"Claude Code's settings file ({settings}) could not be read ({e}). Nothing was changed.")
        return 1
    if mode == "status":
        out({"none": "Live WhatsApp is not set up in Claude Code.",
             "read": "Live WhatsApp in Claude Code: reading only. Sending is refused.",
             "write": "Live WhatsApp in Claude Code: reading, and sending with your yes for each message.",
             "off": "Live WhatsApp in Claude Code is switched off: no WhatsApp tool can be used.",
             }[current_mode(data, server)])
        return 0
    guard = brain / "scripts" / GUARD
    new = updated(data, mode, server, guard, windows)
    lines = changes(data, new, server)
    copy_guard = mode in ("read", "write") and (
        not guard.exists() or guard.read_bytes() != (KIT / GUARD).read_bytes())
    if copy_guard:
        lines.insert(0, f"Copy the WhatsApp guard into your brain: {guard}")
    if not lines:
        out(f"Nothing to change: live WhatsApp is already set to {mode}.")
        return 0
    if not apply:
        out(f"This would change Claude Code's settings ({settings}):")
        for line in lines:
            out(f"- {line}")
        out("Nothing has been changed yet. To make these changes, run the same line with --apply.")
        return 0
    if copy_guard:
        guard.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(KIT / GUARD, guard)
    if settings.exists():
        stamp = (now or datetime.now()).strftime("%Y%m%d-%H%M%S")
        backup = settings.with_name(f"{settings.name}.brainos-{stamp}.bak")
        shutil.copyfile(settings, backup)
        out(f"Saved a copy of the settings first: {backup}")
    settings.parent.mkdir(parents=True, exist_ok=True)
    settings.write_text(json.dumps(new, indent=2) + "\n", encoding="utf-8")
    for line in lines:
        out(f"- Done: {line[0].lower() + line[1:]}")
    out("Restart Claude Code (quit it and open it again) so it uses the new settings.")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Switch the live WhatsApp guard in Claude Code (WHATSAPP-LIVE.md).")
    parser.add_argument("brain")
    parser.add_argument("mode", choices=("status",) + MODES)
    parser.add_argument("--apply", action="store_true", help="make the changes (without it, only show them)")
    parser.add_argument("--settings", default="~/.claude/settings.json", help="Claude Code's settings file")
    parser.add_argument("--server", default="beeper", help="the name the Beeper connection has in Claude Code")
    args = parser.parse_args(argv)
    return run(args.brain, args.mode, args.settings, server=args.server, apply=args.apply)


if __name__ == "__main__":
    sys.exit(main())
