"""Saved progress (kit 2.0, 19 Oct 2026): progress.py writes <brain>/setup.yaml, the only thing that writes it,
so every AI app saves the setup the same way, and check_setup.py opens with "Carry on from step <n>: ..."
when the person pastes the line again. Plain Python 3, no internet, safe on Windows paths and consoles."""
import ast
import json
import os
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import nonet

nonet.install()
CORE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CORE))
import check_setup  # noqa: E402
import progress  # noqa: E402
from create_brain import create_brain  # noqa: E402

FORBIDDEN = {"socket", "urllib", "http", "https", "requests", "ftplib", "smtplib", "ssl", "asyncio",
             "httpx", "aiohttp", "telnetlib", "xmlrpc", "webbrowser", "subprocess"}


def cli(brain, *args, env=None):
    """Run progress.py as the person's AI would: its own process, its own console."""
    return subprocess.run([sys.executable, str(CORE / "progress.py"), str(brain), *args],
                          capture_output=True, text=True, env=env, encoding="utf-8", errors="replace")


def said(folder):
    lines = []
    check_setup.main([str(folder)], out=lines.append)
    return lines


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        # A space and a non-English letter, as on many real laptops (C:\Users\Zoë Smith\Documents\my brain).
        self.brain = create_brain(Path(self.tmp.name) / "Zoë Smith" / "my brain")
        self.file = self.brain / "setup.yaml"

    def run_cmd(self, *args, today="2026-10-21"):
        return progress.run(self.brain, args[0], list(args[1:]), today=today)

    def data(self):
        return progress.load(self.brain)


class Creates(Base):
    def test_the_first_command_creates_setup_yaml_with_the_contract_shape(self):
        self.assertFalse(self.file.exists())
        line = self.run_cmd("show")
        self.assertTrue(line.startswith("Started saving progress in setup.yaml."), line)
        self.assertEqual(self.data(), {"kit_version": "2.0.0", "app": None, "step": 1, "picks": [], "connected": {},
                                       "pending": [], "done": False})
        text = self.file.read_text(encoding="utf-8")
        keys = [l.split(":")[0] for l in text.splitlines() if l and not l.startswith(("#", " "))]
        self.assertEqual(keys, ["kit_version", "app", "step", "picks", "connected", "pending", "done"])
        self.assertIn('kit_version: "2.0.0"', text)

    def test_kit_version_comes_from_the_version_file(self):
        self.assertEqual((CORE / "VERSION").read_text(encoding="utf-8").strip(), "2.0")
        self.assertEqual(progress.kit_version(), "2.0.0")

    def test_a_folder_that_is_not_a_brain_gets_no_setup_yaml(self):
        for folder in (Path(self.tmp.name) / "nope", Path(self.tmp.name) / "empty"):
            if folder.name == "empty":
                folder.mkdir()
            r = cli(folder, "step", "2")
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("Not saved", r.stderr)
            self.assertFalse((folder / "setup.yaml").exists())

    def test_wrong_arguments_say_how_and_change_nothing(self):
        self.run_cmd("step", "3")
        before = self.file.read_bytes()
        for args in ([], ["fly"], ["step"], ["step", "0"], ["step", "10"], ["step", "two"], ["pick"],
                     ["pick", "Google Calendar"], ["connected", "gmail"], ["connected", "gmail", "magic"],
                     ["pending", "only one"], ["pending", "", "say"], ["app", "netscape"], ["arrived"],
                     ["show", "extra"], ["done", "now"]):
            r = cli(self.brain, *args)
            self.assertNotEqual(r.returncode, 0, args)
            self.assertTrue(r.stderr.strip(), args)
            self.assertEqual(self.file.read_bytes(), before, args)


class EachCommand(Base):
    def test_step(self):
        self.assertEqual(self.run_cmd("step", "4"), "Started saving progress in setup.yaml. "
                                                    "Saved: next is step 4 of 9, pull everything in.")
        self.assertEqual(self.data()["step"], 4)
        self.assertEqual(self.run_cmd("step", "2"), "Saved: next is step 2 of 9, choose what to connect.")
        self.assertEqual(self.data()["step"], 2, "going back a step is allowed (step 6 can send you to step 5)")

    def test_pick_adds_in_order_without_repeats(self):
        self.run_cmd("pick", "google-calendar", "gmail")
        self.run_cmd("pick", "whatsapp", "GOOGLE-CALENDAR")
        self.assertEqual(self.data()["picks"], ["google-calendar", "gmail", "whatsapp"])

    def test_connected_records_how_and_the_date_and_counts_as_picked(self):
        line = self.run_cmd("connected", "outlook-calendar", "builtin")
        self.assertIn("outlook-calendar is connected (builtin, 2026-10-21)", line)
        self.assertEqual(self.data()["connected"], {"outlook-calendar": {"how": "builtin", "at": "2026-10-21"}})
        self.assertEqual(self.data()["picks"], ["outlook-calendar"])
        self.run_cmd("connected", "outlook-calendar", "export", today="2026-10-22")
        self.assertEqual(self.data()["connected"]["outlook-calendar"], {"how": "export", "at": "2026-10-22"})
        self.assertIn('at: "2026-10-22"', self.file.read_text(encoding="utf-8"), "a date in quotes stays text")

    def test_pending_and_arrived(self):
        self.run_cmd("pending", "LinkedIn archive", "add my LinkedIn")
        self.run_cmd("pending", "linkedin archive", "add my LinkedIn when it comes")
        self.run_cmd("pending", "X archive", "add my X")
        self.assertEqual(self.data()["pending"], [{"what": "LinkedIn archive", "say_when_arrives": "add my LinkedIn when it comes"},
                                                  {"what": "X archive", "say_when_arrives": "add my X"}])
        self.assertIn("off the list", self.run_cmd("arrived", "LinkedIn archive"))
        self.assertEqual([p["what"] for p in self.data()["pending"]], ["X archive"])
        self.assertIn("was not on the list", self.run_cmd("arrived", "LinkedIn archive"))

    def test_app(self):
        for name in ("claude", "chatgpt", "cursor", "opencode", "orca", "terminal", "other"):
            self.run_cmd("app", name)
            self.assertEqual(self.data()["app"], name)
        self.assertEqual(self.run_cmd("app", "Claude"), "Saved: working in the Claude app.")

    def test_done_then_a_new_step_reopens_it(self):
        self.run_cmd("step", "8")
        self.assertIn("setup is finished", self.run_cmd("done"))
        self.assertEqual((self.data()["done"], self.data()["step"]), (True, 9))
        self.assertTrue(self.run_cmd("show").startswith("Setup is finished"))
        self.run_cmd("step", "3")
        self.assertEqual((self.data()["done"], self.data()["step"]), (False, 3))

    def test_show_names_everything_in_one_line_and_changes_nothing(self):
        self.run_cmd("app", "claude")
        self.run_cmd("step", "3")
        self.run_cmd("pick", "google-calendar", "whatsapp")
        self.run_cmd("connected", "google-calendar", "builtin")
        self.run_cmd("pending", "LinkedIn archive", "add my LinkedIn")
        before = self.file.read_bytes()
        line = self.run_cmd("show")
        self.assertEqual(line, "Next is step 3 of 9: connect them. App: the Claude app. Picked: google-calendar, "
                               "whatsapp. Connected: google-calendar (builtin). Still on its way: LinkedIn archive.")
        self.assertEqual(self.file.read_bytes(), before)

    def test_every_command_prints_exactly_one_line(self):
        for args in (["show"], ["app", "claude"], ["step", "2"], ["pick", "gmail", "whatsapp"],
                     ["connected", "gmail", "builtin"], ["pending", "Two\nlines", "say\nthis"],
                     ["arrived", "Two lines"], ["done"]):
            r = cli(self.brain, *args)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(len(r.stdout.splitlines()), 1, (args, r.stdout))
            self.assertEqual(r.stderr, "")


class Idempotent(Base):
    def test_running_the_same_command_twice_gives_the_same_file(self):
        commands = [["app", "chatgpt"], ["step", "3"], ["pick", "gmail", "google-calendar"],
                    ["connected", "gmail", "builtin"], ["pending", "LinkedIn archive", "add my LinkedIn"],
                    ["arrived", "LinkedIn archive"], ["done"], ["show"]]
        for args in commands:
            self.run_cmd(*args)
            first = self.file.read_bytes()
            self.run_cmd(*args, today="2026-12-25")  # another day: nothing should move
            self.assertEqual(self.file.read_bytes(), first, args)

    def test_reading_back_and_writing_again_changes_nothing(self):
        for args in (["app", "orca"], ["pick", "notion", "slack"], ["connected", "slack", "custom"],
                     ["pending", 'Quotes "and" a: colon # hash', "say 'this'"]):
            self.run_cmd(*args)
        text = self.file.read_text(encoding="utf-8")
        self.assertEqual(progress.dump(progress.parse(text)), text)
        self.assertEqual(self.data()["pending"][0]["what"], 'Quotes "and" a: colon # hash')


class WindowsSafe(Base):
    def test_works_on_a_path_with_spaces_and_accents_and_leaves_no_temp_file(self):
        r = cli(self.brain, "step", "2")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(sorted(p.name for p in self.brain.glob("*setup*")), ["setup.yaml"])

    def test_the_file_uses_plain_line_ends_and_reads_back_after_a_windows_editor(self):
        self.run_cmd("pick", "gmail")
        raw = self.file.read_bytes()
        self.assertNotIn(b"\r", raw)
        # Notepad may add a byte-order mark and Windows line ends: it must still read.
        self.file.write_bytes(b"\xef\xbb\xbf" + raw.replace(b"\n", b"\r\n"))
        self.assertEqual(self.data()["picks"], ["gmail"])
        self.run_cmd("pick", "whatsapp")
        self.assertEqual(self.data()["picks"], ["gmail", "whatsapp"])

    def test_a_windows_console_that_cannot_show_a_letter_does_not_stop_it(self):
        env = dict(os.environ, PYTHONIOENCODING="ascii")
        r = cli(self.brain, "pending", "Zoë's café chats", "add my WhatsApp", env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.data()["pending"][0]["what"], "Zoë's café chats")

    def test_the_lines_it_prints_are_plain_ascii(self):
        for args in (["app", "chatgpt"], ["step", "5"], ["pick", "gmail"], ["connected", "gmail", "builtin"],
                     ["pending", "LinkedIn archive", "add my LinkedIn"], ["done"], ["show"]):
            line = self.run_cmd(*args)
            self.assertTrue(line.isascii(), line)

    def test_a_hand_edited_file_that_cannot_be_read_is_left_alone(self):
        self.file.write_text("step: lots\n", encoding="utf-8")
        r = cli(self.brain, "step", "4")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("could not be read", r.stderr)
        self.assertIn("Rename it", r.stderr)
        self.assertEqual(self.file.read_text(encoding="utf-8"), "step: lots\n")

    def test_another_yaml_reader_sees_the_same_values(self):
        try:
            import yaml  # not part of the kit; only checked where it happens to be installed
        except ImportError:
            self.skipTest("PyYAML is not installed")
        self.run_cmd("app", "claude")
        self.run_cmd("connected", "google-calendar", "builtin")
        self.run_cmd("pending", "Outlook: waiting for IT", "connect my Outlook")
        self.assertEqual(yaml.safe_load(self.file.read_text(encoding="utf-8")), self.data())


class NoNetwork(unittest.TestCase):
    def test_progress_py_imports_nothing_that_can_reach_the_internet(self):
        tree = ast.parse((CORE / "progress.py").read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else \
                [node.module or ""] if isinstance(node, ast.ImportFrom) else []
            for n in names:
                self.assertNotIn(n.split(".")[0], FORBIDDEN, n)


class CarryOn(Base):
    def test_no_setup_yaml_means_no_carry_on_line(self):
        lines = said(self.brain)
        self.assertEqual(lines[0], "BrainOS setup check. Nothing is changed by this check.")
        self.assertFalse(self.file.exists(), "the check must not create setup.yaml")

    def test_the_first_line_says_where_to_carry_on_then_what_is_pending(self):
        self.run_cmd("app", "claude")
        self.run_cmd("step", "3")
        self.run_cmd("pick", "google-calendar", "whatsapp")
        self.run_cmd("connected", "google-calendar", "builtin")
        self.run_cmd("pending", "LinkedIn archive", "add my LinkedIn")
        before = self.file.read_bytes()
        lines = said(self.brain)
        self.assertEqual(lines[0], "Carry on from step 3: connect them (still to connect: whatsapp).")
        self.assertEqual(lines[1], "Still on its way: LinkedIn archive. When it arrives, say: add my LinkedIn.")
        self.assertIn("BrainOS setup check. Nothing is changed by this check.", lines)
        self.assertTrue(lines[-1].startswith("Next step: "), lines[-1])
        self.assertEqual(self.file.read_bytes(), before, "the check changed setup.yaml")

    def test_every_step_has_a_plain_carry_on_line(self):
        for n in range(1, 10):
            self.run_cmd("step", str(n))
            name = progress.STEPS[n][1]
            self.assertEqual(said(self.brain)[0], f"Carry on from step {n}: {name[0].lower() + name[1:]}.")

    def test_finished_and_broken_files_each_get_a_plain_first_line(self):
        self.run_cmd("done")
        self.assertTrue(said(self.brain)[0].startswith("Setup is finished"))
        self.file.write_text("step: [\n", encoding="utf-8")
        first = said(self.brain)[0]
        self.assertTrue(first.startswith("Saved progress: setup.yaml could not be read"), first)
        r = subprocess.run([sys.executable, str(CORE / "check_setup.py"), str(self.brain)], capture_output=True,
                           text=True)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_a_connector_file_in_exports_is_recognised_with_the_brain_first(self):
        f = self.brain / "exports" / "from-google-calendar-2026-10-21.json"
        f.write_text(json.dumps({"people": [{"name": "Priya Demo", "source": "google-calendar, 2026-10-21"}],
                                 "interactions": []}), encoding="utf-8")
        self.assertEqual(check_setup.kind_of(f), ("connector", ""))
        line = check_setup.importer_line("connector", f, self.brain)
        self.assertIn("from_connector.py", line)
        self.assertEqual(shlex.split(line)[-2:], [str(self.brain), str(f)], "from_connector.py takes the brain first")
        win = check_setup.command("C:\\kit\\importers\\from_connector.py", "C:\\Users\\A B\\brain", "x.json",
                                  windows=True)
        self.assertTrue(win.startswith("py "), win)
        self.assertTrue(any(l.startswith(f"- {f.name}: looks like what your AI read through a connector")
                            for l in said(self.brain)))

    def test_progress_py_is_a_file_the_check_needs(self):
        self.assertIn("progress.py", check_setup.NEEDED)


if __name__ == "__main__":
    unittest.main()
