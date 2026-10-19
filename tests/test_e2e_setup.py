"""End to end, the way an attendee's AI runs the setup (kit 2.0, 21 Oct 2026), with no AI and no internet.

One sealed-off run: a made-up home folder, a kit zip built from this kit on disk (never downloaded),
stand-ins for curl, wget and the folder opener, and a dead web proxy. Then every command SETUP.md gives,
run from inside the brain folder exactly as written there:

  start.sh (BRAINOS_ZIP)            -> Documents/brain with only kit/ in it, and the one line printed
  kit/check_setup.py .              -> "empty and ready"
  kit/create_brain.py . --domains network
  kit/progress.py . app / step / pick / connected / pending / arrived
  kit/check_setup.py .              -> "Carry on from step 3: connect them (still to connect: whatsapp)."
  kit/importers/from_connector.py . exports/from-<source id>-<date>.json   (twice: nothing new the second time)
  kit/create_brain.py . --add family
  kit/check_setup.py .              -> "Carry on from step 6: review what it learned."
  start.sh again                    -> the same brain, a fresh kit, the person's files untouched

and at the end: level 1 is the same at every front door, the brain passes the kit's own brain check, and
all eleven skills are there and routed."""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import nonet

nonet.install()
CORE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CORE / "tests"))
import check_brain  # noqa: E402
from test_start_scripts import AI_APPS, DEAD_PROXY, LINE, SYSTEM_PATH, files_outside_kit, kit_zip, stand_in  # noqa: E402

TODAY = "2026-10-21"
SKILLS = ("mine-my-context", "whats-on-my-plate", "who-to-reply-to-first", "who-do-i-know-at", "draft-in-my-voice",
          "what-am-i-putting-off", "prep-my-next-meeting", "who-have-i-gone-quiet-with",
          "morning-brief", "weekly-review", "show-it-visually")
# What the AI saves after reading the calendar and WhatsApp through connections, in the shape SETUP.md
# step 4 gives: one person in each "with", "when" as YYYY-MM-DD, source = the connections.yaml id and the day.
LIVE_READ = {
    "people": [
        {"name": "Priya Demo", "email": "priya@example.com", "source": f"google-calendar, {TODAY}"},
        {"name": "Sam Sample", "email": "sam@example.com", "source": f"google-calendar, {TODAY}"},
        {"name": "Jo Placeholder", "phone": "+44 7700 900111", "source": f"whatsapp, {TODAY}"},
    ],
    "interactions": [
        {"when": "2026-10-19", "with": "Priya Demo", "channel": "calendar", "summary": "Weekly sync",
         "source": f"google-calendar, {TODAY}"},
        {"when": "2026-10-19", "with": "Sam Sample", "channel": "calendar", "summary": "Weekly sync",
         "source": f"google-calendar, {TODAY}"},
        {"when": "2026-10-20", "with": "Priya Demo", "channel": "calendar", "summary": "Launch plan",
         "source": f"google-calendar, {TODAY}"},
        {"when": "2026-10-18", "with": "Jo Placeholder", "channel": "whatsapp", "source": f"whatsapp, {TODAY}"},
    ],
}


@unittest.skipIf(os.name == "nt", "start.sh is the Mac and Linux line")
class EndToEnd(unittest.TestCase):
    def setUp(self):
        for app in AI_APPS:
            if shutil.which(app, path=SYSTEM_PATH):
                self.skipTest(f"{app} is installed in {SYSTEM_PATH}, so 'no AI app' cannot be tested here")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.home = root / "home"
        (self.home / "Documents").mkdir(parents=True)
        self.bin = root / "bin"
        self.bin.mkdir()
        self.calls = root / "calls.txt"
        self.scratch = root / "scratch"
        self.scratch.mkdir()
        for name in ("curl", "wget", "open", "xdg-open"):
            stand_in(self.bin, name, f'echo "{name} $*" >> "$CALLS"; ' + ("exit 1" if name in ("curl", "wget") else ""))
        os.symlink(sys.executable, self.bin / "python3")
        self.zip = kit_zip(root / "kit.zip", top="brainos-core-kit-2.0")
        self.root = root
        self.brain = self.home / "Documents" / "brain"

    def env(self):
        return {"HOME": str(self.home), "PATH": f"{self.bin}:{SYSTEM_PATH}", "BRAINOS_ZIP": str(self.zip),
                "CALLS": str(self.calls), "TMPDIR": str(self.scratch), "LANG": "C", "PYTHONDONTWRITEBYTECODE": "1",
                "http_proxy": DEAD_PROXY, "https_proxy": DEAD_PROXY, "HTTP_PROXY": DEAD_PROXY,
                "HTTPS_PROXY": DEAD_PROXY, "ALL_PROXY": DEAD_PROXY}

    def start_sh(self):
        r = subprocess.run(["/bin/sh"], input=(CORE / "start.sh").read_bytes(), env=self.env(), cwd=self.root,
                           capture_output=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr.decode())
        return r.stdout.decode()

    def kit(self, *args):
        """One command from SETUP.md, run from inside the brain folder: `python3 kit/<script> . ...`."""
        r = subprocess.run(["python3", *map(str, args)], env=self.env(), cwd=self.brain, capture_output=True,
                           text=True, timeout=120)
        self.assertEqual(r.returncode, 0, f"{args}: {r.stdout}{r.stderr}")
        return r.stdout

    def progress(self, *args):
        out = self.kit("kit/progress.py", ".", *args).strip().splitlines()
        self.assertEqual(len(out), 1, f"progress.py prints one plain line: {out}")
        return out[0]

    def check(self):
        return self.kit("kit/check_setup.py", ".").splitlines()

    def jsonl(self, name):
        path = self.brain / "network" / name
        return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]

    def test_the_whole_setup_from_the_terminal_line_to_step_six(self):
        # Step 1: the terminal line. Documents/brain, with only the kit in it, and the one line printed.
        said = self.start_sh()
        self.assertIn(LINE, said.splitlines(), "the AI-app line, word for word, on a line of its own")
        self.assertIn(f"Your brain folder is {self.brain}", said)
        self.assertEqual(sorted(p.name for p in self.brain.iterdir()), ["kit"])
        self.assertEqual((self.brain / "kit" / "VERSION").read_text(encoding="utf-8").strip(), "2.0")
        self.assertEqual(list(self.scratch.iterdir()), [], "the temporary download folder is deleted")
        calls = self.calls.read_text(encoding="utf-8").splitlines() if self.calls.exists() else []
        self.assertFalse([c for c in calls if c.startswith(("curl", "wget"))], "the kit came from the zip, not the web")
        self.assertIn("is empty and ready for create_brain.py", "\n".join(self.check()))

        self.assertIn("Created an empty brain", self.kit("kit/create_brain.py", ".", "--domains", "network"))
        self.assertIn("Level 1 is the same", self.kit("scripts/level1.py", "check", "."))
        self.assertIn("Started saving progress in setup.yaml.", self.progress("app", "claude"))
        self.progress("step", "2")

        # Steps 2 and 3: pick two sources; one connects, the other is still to do.
        self.assertEqual(self.progress("pick", "google-calendar", "whatsapp"),
                         "Saved: picked google-calendar, whatsapp (2 picked in all).")
        self.progress("step", "3")
        self.assertEqual(self.progress("connected", "google-calendar", "builtin"),
                         f"Saved: google-calendar is connected (builtin, {self._today()}).")
        lines = self.check()
        self.assertEqual(lines[0], "Carry on from step 3: connect them (still to connect: whatsapp).")
        self.progress("connected", "whatsapp", "local")
        self.progress("pending", "LinkedIn archive", "add my LinkedIn")
        self.progress("step", "4")
        lines = self.check()
        self.assertEqual(lines[:2], ["Carry on from step 4: pull everything in.",
                                     "Still on its way: LinkedIn archive. When it arrives, say: add my LinkedIn."])

        # Step 4: what the AI read through the connections, saved and brought in as SETUP.md says.
        read = self.brain / "exports" / f"from-google-calendar-{TODAY}.json"
        read.write_text(json.dumps(LIVE_READ, indent=1), encoding="utf-8")
        listed = self.check()
        at = next(i for i, l in enumerate(listed) if l.startswith(f"- {read.name}: "))
        self.assertIn("what your AI read through a connector", listed[at])
        line = listed[at + 1]
        self.assertIn("importers/from_connector.py", line)
        brain, export = str(self.brain.resolve()), str(read.resolve())
        self.assertLess(line.index(brain + " "), line.index(export), "the brain first, then the file")
        out = self.kit("kit/importers/from_connector.py", ".", f"exports/{read.name}")
        self.assertEqual(out.strip(), "From live connections (google-calendar-live, whatsapp-live): 3 people read, "
                                      "3 new to the brain; 4 conversations and meetings read, 4 new, 0 already there.")
        again = self.kit("kit/importers/from_connector.py", ".", f"exports/{read.name}")
        self.assertIn("0 new to the brain; 4 conversations and meetings read, 0 new, 4 already there.", again)
        people, talks = self.jsonl("people.jsonl"), self.jsonl("interactions.jsonl")
        self.assertEqual(sorted(p["name"] for p in people), ["Jo Placeholder", "Priya Demo", "Sam Sample"])
        self.assertEqual(len(talks), 4)
        self.assertEqual({t["source"] for t in talks}, {"google-calendar-live", "whatsapp-live"})
        jo = next(p for p in people if p["name"] == "Jo Placeholder")
        self.assertEqual(jo["confidence"], "medium", "a WhatsApp name read live is medium, like an export")
        for row in people + talks:
            self.assertTrue(row.get("source") and row.get("confidence"), row)
        self.progress("step", "5")

        # Step 5: one more area, added to the brain that is already there.
        self.assertIn("Added family", self.kit("kit/create_brain.py", ".", "--add", "family"))
        self.assertTrue((self.brain / "family" / "FAMILY.md").is_file())
        self.assertIn("domains: [network, family]", (self.brain / "brain.yaml").read_text(encoding="utf-8"))
        self.assertIn("Level 1 is the same", self.kit("scripts/level1.py", "check", "."))
        self.progress("step", "6")
        lines = self.check()
        self.assertEqual(lines[0], "Carry on from step 6: review what it learned.")
        self.assertIn("is a brain. Level 1 is the same in CLAUDE.md, GEMINI.md and the top of AGENTS.md.",
                      "\n".join(lines))

        setup = (self.brain / "setup.yaml").read_text(encoding="utf-8")
        for must in ('kit_version: "2.0.0"', "app: claude", "step: 6", "  - google-calendar", "  - whatsapp",
                     "    how: builtin", "    how: local", '  - what: "LinkedIn archive"', "done: false"):
            self.assertIn(must, setup)
        self.assertIn("Saved: LinkedIn archive has arrived and is off the list.",
                      self.progress("arrived", "LinkedIn archive"))

        # The brain: level 1 the same at every front door, the kit's own brain check, eleven skills routed.
        self.assertEqual(check_brain.check(self.brain), [])
        agents = (self.brain / "AGENTS.md").read_text(encoding="utf-8")
        found = sorted(p.parent.name for p in (self.brain / "skills").glob("*/SKILL.md"))
        self.assertEqual(found, sorted(SKILLS))
        self.assertEqual(len(found), 11)
        for name in SKILLS:
            self.assertIn(f"skills/{name}/SKILL.md", agents, name)
        self.assertIn("Eleven skills ship with the brain", (self.brain / "skills/SKILLS.md").read_text(encoding="utf-8"))
        self.assertEqual(sorted(p.name for p in self.home.iterdir()), ["Documents"], "nothing made outside the brain")
        self.assertEqual(sorted(p.name for p in (self.home / "Documents").iterdir()), ["brain"])

        # Paste the line again later: the same brain, a fresh kit, and the person's files exactly as they were.
        before = files_outside_kit(self.brain)
        said = self.start_sh()
        self.assertIn(f"Your brain folder is {self.brain}", said)
        self.assertIn(LINE, said.splitlines())
        self.assertEqual(files_outside_kit(self.brain), before)
        self.assertTrue((self.brain / "kit" / "SETUP.md").is_file())
        self.assertEqual(self.check()[0], "Carry on from step 6: review what it learned.")

    @staticmethod
    def _today():
        from datetime import date
        return date.today().isoformat()


if __name__ == "__main__":
    unittest.main()
