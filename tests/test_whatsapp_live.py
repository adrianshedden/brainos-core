"""The optional live WhatsApp module (WHATSAPP-LIVE.md, whatsapp_live.py, whatsapp_send_guard.py).

Rian, sheet v8 (19 Oct 2026): attendees who want it can link WhatsApp live in the afternoon build session, to
read and to write. It stays out of setup, which only imports exported chats. Sheet v10: two routes, wacli (quick)
and Beeper (sustainable), kept short. The guide says the risks first and waits for a yes; reading comes first;
sending is a second yes, and the send guard makes Claude Code show every message, word for word, and ask before
it goes. It can be switched off and removed. Nothing of Rian's (names, numbers, paths, chat ids) is in it."""
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

    def bash(self, command, mode="read", cap=20):
        return self.judge({"tool_name": "Bash", "tool_input": {"command": command}}, mode, cap=cap)

    def test_wacli_reads_only_with_read_only(self):
        for mode in ("read", "write"):
            for command in ("wacli --read-only --json chats list", 'wacli --read-only messages search "invoice"',
                            "WACLI_READONLY=1 wacli --json doctor", "/opt/homebrew/bin/wacli --read-only chats list",
                            "wacli sync --once"):
                self.assertIsNone(self.bash(command, mode), f"{command} in {mode} mode")
            for command in ("wacli messages search invoice", "wacli sync", "wacli sync --follow", "wacli auth",
                            "wacli auth logout", "wacli chats archive Sam", "wacli --read-only chats list; rm -rf x",
                            "wacli --read-only chats list && wacli chats mute Sam", 'wacli --read-only "unclosed'):
                self.assertEqual(kind(self.bash(command, mode)), "deny", f"{command} in {mode} mode")
        for command in ("ls -la", "git status", "python3 kit/check_setup.py ."):
            self.assertIsNone(self.bash(command, "read"), "other commands are not its business")
        self.assertIsNone(self.judge({"tool_name": "Bash", "tool_input": {}}, "read"))

    def test_wacli_sends_only_plain_text_with_a_yes(self):
        send = 'wacli send text --to "Sam Sample" --message "See you at six."'
        self.assertEqual(kind(self.bash(send, "read")), "deny")
        answer = self.bash(send, "write")
        self.assertEqual(kind(answer), "ask")
        reason = answer["hookSpecificOutput"]["permissionDecisionReason"]
        self.assertIn("To: Sam Sample", reason)
        self.assertIn("Message: See you at six.", reason)
        self.assertEqual(kind(self.bash('wacli send text --to Sam --message="Hi there"', "write")), "ask")
        for command in ("wacli send text --to Sam", "wacli send file --to Sam --file x.pdf",
                        "wacli send react --to Sam --id 1", "wacli send status --message hi",
                        'wacli send text --to a --message b; wacli send text --to c --message d'):
            self.assertEqual(kind(self.bash(command, "write")), "deny", command)
        for _ in range(2):
            self.bash(send, "write")
        self.assertEqual(kind(self.bash(send, "write", cap=3)), "deny", "the daily cap covers wacli too")

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
        ours = self.ours(data)
        self.assertEqual([g["matcher"] for g in ours], ["mcp__beeper__.*", "Bash|PowerShell"])
        self.assertTrue(all(g["hooks"][0]["command"].endswith("--mode read") for g in ours))
        self.assertIn("Bash(wacli send *)", data["permissions"]["deny"])
        copied = self.brain / "scripts" / "whatsapp_send_guard.py"
        self.assertEqual(copied.read_bytes(), (CORE / "whatsapp_send_guard.py").read_bytes())
        self.assertIn(str(copied.resolve()), ours[0]["hooks"][0]["command"])
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
        self.assertEqual(data["permissions"]["ask"], ["mcp__beeper__send*", "Bash(wacli send *)", "Bash(wacli * send *)"])
        self.assertNotIn("mcp__beeper__send*", data["permissions"]["deny"])
        self.assertNotIn("Bash(wacli send *)", data["permissions"]["deny"])
        self.assertIn("mcp__beeper__*delete*", data["permissions"]["deny"])
        ours = self.ours(data)
        self.assertEqual(len(ours), 2)
        self.assertTrue(all(g["hooks"][0]["command"].endswith("--mode write") for g in ours))

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
        self.assertIn("Bash(wacli *)", data["permissions"]["deny"])
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
        for group, payload in zip(self.ours(self.data()), (
                call("send_message", chatID="c", text="hi"),
                {"tool_name": "Bash", "tool_input": {"command": "wacli send text --to c --message hi"}})):
            r = subprocess.run(group["hooks"][0]["command"], shell=True, capture_output=True, timeout=30,
                               input=json.dumps(payload).encode())
            self.assertEqual(json.loads(r.stdout)["hookSpecificOutput"]["permissionDecision"], "deny", r.stderr)


class Guide(unittest.TestCase):
    def section(self, n):
        return GUIDE.split(f"## {n}.", 1)[1].split("\n## ", 1)[0]

    def test_the_risks_and_a_yes_come_before_anything_is_installed(self):
        risks = GUIDE.index("## 1. The risks, and a yes")
        for first_step in ("brew install", "beeper.com/download", "whatsapp_live.py", "wacli auth"):
            self.assertLess(risks, GUIDE.index(first_step), first_step)
        said = self.section(1)
        for must in ("no official way", "ban", "afford to lose access", "It's up to you",
                     "won't install anything until you say yes", "Wait for a clear yes", "is a no"):
            self.assertIn(must, said)

    def test_two_routes_quick_wacli_and_sustainable_beeper(self):
        routes = self.section(2)
        self.assertIn("**Quick route: wacli.**", routes)
        self.assertIn("**Sustainable route: Beeper.**", routes)
        self.assertLess(routes.index("Quick route"), routes.index("Sustainable route"))
        for must in ("Mac", "Windows", "have not yet been tried", "only in Claude Code", "reading only",
                     "do not arrive by themselves"):
            self.assertIn(must, routes)
        read = self.section(3)
        for must in ("wacli auth", "--read-only", "Linked devices", "Desktop API", "read --apply", "always deny sending"):
            self.assertIn(must, read)

    def test_sending_is_a_second_yes_with_every_word_shown(self):
        sending = self.section(4).lower()
        for must in ("second yes", "draft you approve", "nothing goes until you click yes", "write --apply",
                     "one message per yes", "wait for a clear yes", 'wacli send text --to "<chat>"'):
            self.assertIn(must, sending, must)

    def test_it_can_be_switched_off_and_removed(self):
        gone = self.section(5)
        for must in ("off --apply", "quit Beeper", "Linked devices", "Log out", "claude mcp remove beeper",
                     "remove --apply", "Uninstall", ".wacli"):
            self.assertIn(must, gone)

    def test_it_is_short(self):
        self.assertLess(len(GUIDE.split()), 1200, "Rian, sheet v10: keep it short")

    def test_the_always_on_server_answer_names_waha_and_nothing_private(self):
        answer = GUIDE.split("## How does it work on an always-on server?", 1)[1]
        self.assertIn("WAHA", answer)
        self.assertIn("ready-made WhatsApp Web server", answer)

    def test_the_guide_opens_with_the_line_to_tell_your_ai(self):
        # Rian's slide review: people reach this page from a QR code and need a line to hand their AI.
        top = GUIDE.split("## 1.", 1)[0]
        self.assertIn("**Tell your AI:** Connect my WhatsApp using WHATSAPP-LIVE.md from the BrainOS kit at "
                      "github.com/adrianshedden/brainos-core.", top)
        self.assertIn("follow it from section 1", top)
        self.assertIn("wait for a clear yes before you install or change anything", top)
        agents = (CORE / "template" / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("connect my WhatsApp using WHATSAPP-LIVE.md | Follow `kit/WHATSAPP-LIVE.md`", agents)

    def test_nothing_of_rians_is_in_it(self):
        personal = re.compile(r"Rian|Adrian|Shedden|/Users/|/home/|beeper\.local|metanova|Becky|\+44|07\d{9}|"
                              r"[\w.]+@[\w-]+\.\w+|super-mcp|claudedanger", re.IGNORECASE)
        for name in ("WHATSAPP-LIVE.md", "whatsapp_live.py", "whatsapp_send_guard.py"):
            # The kit's own public address is allowed: it is where people get the kit.
            text = (CORE / name).read_text(encoding="utf-8").replace("github.com/adrianshedden/brainos-core", "")
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
