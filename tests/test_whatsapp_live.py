"""The optional live WhatsApp module (WHATSAPP-LIVE.md, whatsapp_live.py, whatsapp_send_guard.py).

Rian, sheet v8 (19 Oct 2026): attendees who want it can link WhatsApp live in the afternoon build session, to
read and to write. It stays out of setup, which only imports exported chats. The guide says the risks first and
waits for a yes; reading comes first; sending is a second yes, and the send guard makes Claude Code show every
message, word for word, and ask before it goes. It can be switched off and removed. Nothing of Rian's (names,
numbers, paths, chat ids) is in it. No network."""
import ast
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import nonet

nonet.install()
CORE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CORE))
import whatsapp_live  # noqa: E402
import whatsapp_send_guard as guard  # noqa: E402
from create_brain import create_brain  # noqa: E402

GUIDE = (CORE / "WHATSAPP-LIVE.md").read_text(encoding="utf-8")
TODAY = "2026-10-21"


def call(tool, **tool_input):
    return {"tool_name": f"mcp__beeper__{tool}", "tool_input": tool_input}


def kind(answer):
    return "allow" if answer is None else answer["hookSpecificOutput"]["permissionDecision"]


class SendGuard(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.log = Path(self.tmp.name) / "log.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    def judge(self, payload, mode="read", cap=20):
        return guard.judge(payload, mode, cap=cap, log=self.log, today=TODAY)

    def test_reading_goes_ahead_in_both_modes(self):
        for mode in ("read", "write"):
            for tool in ("search", "search_chats", "list_messages", "get_chat", "get_accounts", "download_asset",
                         "searchMessages"):
                self.assertIsNone(self.judge(call(tool), mode), f"{tool} in {mode} mode")
        self.assertFalse(self.log.exists(), "reading is not counted")

    def test_read_mode_refuses_every_send(self):
        for tool in ("send_message", "sendMessage", "send"):
            answer = self.judge(call(tool, chatID="c1", text="hello"), "read")
            self.assertEqual(kind(answer), "deny", tool)
            self.assertIn("read-only", answer["hookSpecificOutput"]["permissionDecisionReason"])
        self.assertFalse(self.log.exists())

    def test_write_mode_asks_and_shows_the_chat_and_every_word(self):
        words = "Running ten minutes late, sorry. See you at the cafe."
        answer = self.judge(call("send_message", chatID="chat-42", text=words), "write")
        self.assertEqual(kind(answer), "ask")
        reason = answer["hookSpecificOutput"]["permissionDecisionReason"]
        self.assertIn("To: chat-42", reason)
        self.assertIn(f"Message: {words}", reason)
        self.assertIn("Check every word", reason)
        logged = [json.loads(line) for line in self.log.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(logged, [{"date": TODAY, "chat": "chat-42", "length": len(words)}])
        self.assertNotIn("cafe", self.log.read_text(encoding="utf-8"), "the words are never kept")

    def test_a_send_it_cannot_show_is_refused(self):
        for tool_input in ({"chatID": "c1"}, {"chatID": "c1", "text": "   "}, {"chatID": "c1", "text": 7}):
            answer = self.judge({"tool_name": "mcp__beeper__send_message", "tool_input": tool_input}, "write")
            self.assertEqual(kind(answer), "deny", tool_input)
        self.assertEqual(kind(self.judge({"tool_name": "mcp__beeper__send_message", "tool_input": "x"}, "write")),
                         "deny")

    def test_the_daily_cap_counts_only_today(self):
        self.log.write_text("".join(json.dumps({"date": "2026-10-20", "chat": "c", "length": 1}) + "\n"
                                    for _ in range(5)) + "not json\n", encoding="utf-8")
        for _ in range(3):
            self.assertEqual(kind(self.judge(call("send_message", chatID="c", text="hi"), "write", cap=3)), "ask")
        answer = self.judge(call("send_message", chatID="c", text="hi"), "write", cap=3)
        self.assertEqual(kind(answer), "deny")
        self.assertIn("3 WhatsApp messages today", answer["hookSpecificOutput"]["permissionDecisionReason"])
        self.assertEqual(guard.requests_today(self.log, "2026-10-22"), 0)

    def test_a_count_it_cannot_keep_means_no_send(self):
        self.log.mkdir()
        self.assertEqual(kind(self.judge(call("send_message", chatID="c", text="hi"), "write")), "deny")

    def test_changes_and_unknown_tools_are_refused_in_both_modes(self):
        for mode in ("read", "write"):
            for tool in ("archive_chat", "set_chat_reminder", "clear_chat_reminder", "edit_message", "delete_message",
                         "focus_app", "add_reaction", "get_and_archive", "mark_read", "create_chat", "do_something",
                         "send_and_delete"):
                self.assertEqual(kind(self.judge(call(tool, chatID="c", text="x"), mode)), "deny", f"{tool} {mode}")

    def test_it_fails_closed_on_input_it_cannot_read(self):
        for payload in (None, [], "text", {}, {"tool_name": ""}, {"tool_name": 3}):
            self.assertEqual(kind(self.judge(payload, "write")), "deny", payload)
        out = io.StringIO()
        guard.main(["--mode", "write", "--log", str(self.log)], stdin=io.StringIO("not json"), out=out)
        self.assertEqual(json.loads(out.getvalue())["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_it_runs_as_claude_code_runs_it(self):
        def run(payload, mode):
            r = subprocess.run([sys.executable, str(CORE / "whatsapp_send_guard.py"), "--mode", mode,
                                "--log", str(self.log)], input=json.dumps(payload).encode(), capture_output=True,
                               timeout=30)
            self.assertEqual(r.returncode, 0, r.stderr)
            return r.stdout.decode().strip()
        self.assertEqual(run(call("list_messages", chatID="c"), "read"), "", "a read prints nothing and goes ahead")
        self.assertEqual(json.loads(run(call("send_message", chatID="c", text="hi"), "read"))
                         ["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertEqual(json.loads(run(call("send_message", chatID="c", text="hi"), "write"))
                         ["hookSpecificOutput"]["permissionDecision"], "ask")


class Switch(unittest.TestCase):
    """whatsapp_live.py changes only what it adds, in a settings file it is pointed at (never the real one here)."""

    BEFORE = {"model": "sonnet",
              "permissions": {"allow": ["Bash(ls *)"], "deny": ["Read(./.env)"]},
              "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "echo hi"}]}],
                        "Stop": [{"hooks": [{"type": "command", "command": "echo bye"}]}]}}

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.brain = create_brain(Path(self.tmp.name) / "brain")
        self.settings = Path(self.tmp.name) / "claude" / "settings.json"
        self.settings.parent.mkdir()
        self.settings.write_text(json.dumps(self.BEFORE), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def run_mode(self, mode, apply=True, windows=False):
        lines = []
        code = whatsapp_live.run(self.brain, mode, self.settings, apply=apply, windows=windows, out=lines.append,
                                 now=datetime(2026, 10, 21, 14, 0, len(list(self.settings.parent.iterdir()))))
        return code, lines

    def data(self):
        return json.loads(self.settings.read_text(encoding="utf-8"))

    def ours(self, data):
        return [g for g in data.get("hooks", {}).get("PreToolUse", []) if whatsapp_live.is_ours(g)]

    def test_without_apply_nothing_changes(self):
        before = self.settings.read_text(encoding="utf-8")
        code, lines = self.run_mode("read", apply=False)
        self.assertEqual(code, 0)
        self.assertEqual(self.settings.read_text(encoding="utf-8"), before)
        self.assertFalse((self.brain / "scripts" / "whatsapp_send_guard.py").exists())
        self.assertEqual(list(self.settings.parent.iterdir()), [self.settings], "no copy, no new file")
        self.assertIn("Nothing has been changed yet", lines[-1])
        self.assertTrue(any("mcp__beeper__send*" in line for line in lines), lines)

    def test_read_adds_the_guard_and_keeps_everything_else(self):
        code, lines = self.run_mode("read")
        self.assertEqual(code, 0, lines)
        data = self.data()
        self.assertEqual(data["model"], "sonnet")
        self.assertEqual(data["permissions"]["allow"], ["Bash(ls *)"])
        self.assertIn("Read(./.env)", data["permissions"]["deny"])
        self.assertIn("mcp__beeper__send*", data["permissions"]["deny"])
        self.assertIn("mcp__beeper__*archive*", data["permissions"]["deny"])
        self.assertNotIn("ask", data["permissions"])
        self.assertEqual(data["hooks"]["Stop"], self.BEFORE["hooks"]["Stop"])
        self.assertIn(self.BEFORE["hooks"]["PreToolUse"][0], data["hooks"]["PreToolUse"])
        [ours] = self.ours(data)
        self.assertEqual(ours["matcher"], "mcp__beeper__.*")
        self.assertTrue(ours["hooks"][0]["command"].endswith("--mode read"))
        copied = self.brain / "scripts" / "whatsapp_send_guard.py"
        self.assertEqual(copied.read_bytes(), (CORE / "whatsapp_send_guard.py").read_bytes())
        self.assertIn(str(copied), ours["hooks"][0]["command"])
        backups = [p for p in self.settings.parent.iterdir() if p.name.endswith(".bak")]
        self.assertEqual(len(backups), 1)
        self.assertEqual(json.loads(backups[0].read_text(encoding="utf-8")), self.BEFORE)
        self.assertIn("Restart Claude Code", lines[-1])

    def test_status_follows_each_mode(self):
        said = lambda: self.run_mode("status")[1][0]  # noqa: E731
        self.assertIn("not set up", said())
        self.run_mode("read")
        self.assertIn("reading only", said())
        self.run_mode("write")
        self.assertIn("sending with your yes", said())
        self.run_mode("off")
        self.assertIn("switched off", said())

    def test_write_asks_before_every_send_and_still_refuses_changes(self):
        self.run_mode("read")
        self.run_mode("write")
        data = self.data()
        self.assertEqual(data["permissions"]["ask"], ["mcp__beeper__send*"])
        self.assertNotIn("mcp__beeper__send*", data["permissions"]["deny"])
        self.assertIn("mcp__beeper__*delete*", data["permissions"]["deny"])
        [ours] = self.ours(data)
        self.assertTrue(ours["hooks"][0]["command"].endswith("--mode write"))

    def test_the_same_mode_twice_changes_nothing(self):
        self.run_mode("read")
        before = self.settings.read_text(encoding="utf-8")
        code, lines = self.run_mode("read")
        self.assertEqual((code, lines), (0, ["Nothing to change: live WhatsApp is already set to read."]))
        self.assertEqual(self.settings.read_text(encoding="utf-8"), before)

    def test_off_refuses_every_whatsapp_tool(self):
        self.run_mode("write")
        self.run_mode("off")
        data = self.data()
        self.assertIn("mcp__beeper", data["permissions"]["deny"])
        self.assertNotIn("ask", data["permissions"])
        self.assertEqual(self.ours(data), [])

    def test_remove_puts_the_settings_back_exactly(self):
        for mode in ("read", "write", "off", "remove"):
            self.run_mode(mode)
        self.assertEqual(self.data(), self.BEFORE)

    def test_a_new_settings_file_is_made_and_emptied_cleanly(self):
        self.settings.unlink()
        self.run_mode("read")
        self.assertIn("permissions", self.data())
        self.run_mode("remove")
        self.assertEqual(self.data(), {})

    def test_it_refuses_a_folder_that_is_not_a_brain_or_settings_it_cannot_read(self):
        lines = []
        self.assertEqual(whatsapp_live.run(self.tmp.name, "read", self.settings, apply=True, out=lines.append), 1)
        self.assertIn("not a brain folder", lines[0])
        self.settings.write_text("{not json", encoding="utf-8")
        code, lines = self.run_mode("read")
        self.assertEqual(code, 1)
        self.assertIn("Nothing was changed", lines[0])
        self.assertEqual(self.settings.read_text(encoding="utf-8"), "{not json")
        self.assertFalse((self.brain / "scripts" / "whatsapp_send_guard.py").exists())

    def test_windows_uses_py_and_forward_slashes(self):
        command = whatsapp_live.guard_command(Path("C:\\Users\\A B\\brain\\scripts\\whatsapp_send_guard.py"),
                                              "write", windows=True)
        self.assertTrue(command.startswith('py "'), command)
        self.assertNotIn("\\", command)
        self.assertTrue(command.endswith("--mode write"))

    @unittest.skipIf(os.name == "nt", "the shell line is checked on a Mac or Linux")
    def test_the_line_it_adds_refuses_a_send_when_run(self):
        self.run_mode("read")
        [ours] = self.ours(self.data())
        r = subprocess.run(ours["hooks"][0]["command"], shell=True, capture_output=True, timeout=30,
                           input=json.dumps(call("send_message", chatID="c", text="hi")).encode())
        self.assertEqual(json.loads(r.stdout)["hookSpecificOutput"]["permissionDecision"], "deny", r.stderr)


class Guide(unittest.TestCase):
    def test_the_risks_and_a_yes_come_before_anything_is_installed(self):
        risks = GUIDE.index("## 1. Say the risks first")
        for first_step in ("beeper.com/download", "whatsapp_live.py", "claude mcp"):
            self.assertLess(risks, GUIDE.index(first_step), first_step)
        said = GUIDE[risks:GUIDE.index("## 2.")]
        for must in ("no official way", "ban", "afford to lose access", "won't install anything until you say yes",
                     "Wait for a clear yes", "is a no"):
            self.assertIn(must, said)

    def test_reading_first_then_sending_with_a_second_yes(self):
        self.assertLess(GUIDE.index("## 3. Reading"), GUIDE.index("## 4. Sending (a second yes, Claude Code only)"))
        sending = GUIDE.split("## 4.", 1)[1].split("## 5.", 1)[0]
        for must in ("draft you approve", "nothing goes until you click yes", "write --apply", "One message per yes",
                     "wait for a clear yes"):
            self.assertIn(must.lower(), sending.lower(), must)
        reading = GUIDE.split("## 3.", 1)[1].split("## 4.", 1)[0]
        self.assertIn("read --apply", reading)
        self.assertIn("always deny sending", reading)

    def test_mac_and_windows_are_both_covered_and_limits_said_plainly(self):
        where = GUIDE.split("## 2.", 1)[1].split("## 3.", 1)[0]
        for must in ("Mac", "Windows", "have not yet been tried on Windows", "only in Claude Code", "reading only",
                     "not in this kit"):
            self.assertIn(must, where)
        self.assertIn("py", GUIDE.split("## 1.", 1)[0])

    def test_it_can_be_switched_off_and_removed(self):
        off = GUIDE.split("## 5. Switch it off", 1)[1].split("## 6.", 1)[0]
        self.assertIn("off --apply", off)
        self.assertIn("quit Beeper", off)
        gone = GUIDE.split("## 6. Remove it completely", 1)[1]
        for must in ("Linked devices", "Log out", "claude mcp remove beeper", "remove --apply", "Uninstall"):
            self.assertIn(must, gone)

    def test_nothing_of_rians_is_in_it(self):
        personal = re.compile(r"Rian|Adrian|Shedden|/Users/|/home/|beeper\.local|metanova|Becky|\+44|07\d{9}|"
                              r"[\w.]+@[\w-]+\.\w+|super-mcp|claudedanger", re.IGNORECASE)
        for name in ("WHATSAPP-LIVE.md", "whatsapp_live.py", "whatsapp_send_guard.py"):
            text = (CORE / name).read_text(encoding="utf-8")
            self.assertIsNone(personal.search(text), f"{name}: {personal.search(text)}")

    def test_setup_leaves_it_out(self):
        setup = (CORE / "SETUP.md").read_text(encoding="utf-8")
        before_later, later = setup.split("## Coming back later", 1)
        self.assertNotIn("WHATSAPP-LIVE.md", before_later)
        self.assertIn("WHATSAPP-LIVE.md", later.split("\n## ", 1)[0])
        self.assertIn("keep only its export routes", before_later)

    def test_the_scripts_never_use_the_network(self):
        forbidden = {"socket", "urllib", "http", "requests", "ssl", "asyncio", "webbrowser"}
        for name in ("whatsapp_live.py", "whatsapp_send_guard.py"):
            for node in ast.walk(ast.parse((CORE / name).read_text(encoding="utf-8"))):
                names = [a.name for a in node.names] if isinstance(node, ast.Import) else \
                    [node.module or ""] if isinstance(node, ast.ImportFrom) else []
                for n in names:
                    self.assertNotIn(n.split(".")[0], forbidden, f"{name} imports {n}")


if __name__ == "__main__":
    unittest.main()
