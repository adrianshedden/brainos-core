"""B16: level 1 is written once and is at every AI's front door, word for word.

Each AI opens a different file by itself: Claude reads CLAUDE.md, Gemini (Antigravity) reads GEMINI.md,
and Codex (in the ChatGPT app), Cursor and most others read AGENTS.md. So level 1 lives once in the kit
(template/LEVEL1.md) and create_brain.py copies it to CLAUDE.md, GEMINI.md and a marked block at the top
of AGENTS.md, with level 2 below it. level1.py fails when the copies drift and puts them right with sync.
Level 2 and level 3 are unchanged."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import nonet

nonet.install()
CORE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CORE))
import check_brain  # noqa: E402
import level1  # noqa: E402
from create_brain import create_brain  # noqa: E402

SOURCE = (CORE / "template" / "LEVEL1.md").read_text(encoding="utf-8")


def read(path):
    return Path(path).read_text(encoding="utf-8")


class WrittenOnce(unittest.TestCase):
    def test_the_kit_holds_one_level_1_and_no_front_door_copies(self):
        self.assertFalse((CORE / "template" / "CLAUDE.md").exists())
        self.assertFalse((CORE / "template" / "GEMINI.md").exists())
        self.assertFalse(read(CORE / "template" / "AGENTS.md").startswith(level1.START))
        self.assertIn("(level 2)", read(CORE / "template" / "AGENTS.md").splitlines()[0])
        self.assertIn("(level 1)", SOURCE.splitlines()[0])

    def test_level_1_names_every_front_door_and_is_small_enough_for_codex(self):
        for door in ("`CLAUDE.md`", "`GEMINI.md`", "`AGENTS.md`"):
            self.assertIn(door, SOURCE)
        for must in ("## Who this is for", "## How to start a session", "## Rules", "scripts/level1.py sync"):
            self.assertIn(must, SOURCE)
        # Codex stops reading instruction files at 32 KiB in all; level 1 plus level 2 must fit well inside.
        with tempfile.TemporaryDirectory() as tmp:
            brain = create_brain(Path(tmp) / "b")
            self.assertLess(len((brain / "AGENTS.md").read_bytes()), 16 * 1024)


class EveryDoor(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.brain = create_brain(Path(self.tmp.name) / "b", ["network", "work"])

    def test_claude_gemini_and_the_top_of_agents_say_the_same_words(self):
        claude, gemini, agents = (read(self.brain / n) for n in ("CLAUDE.md", "GEMINI.md", "AGENTS.md"))
        self.assertEqual(claude, SOURCE)
        self.assertEqual(gemini, SOURCE)
        self.assertTrue(agents.startswith(level1.START), "AGENTS.md must open with level 1")
        inner, level2 = level1.split(agents)
        self.assertEqual(inner, SOURCE.strip())
        self.assertTrue(level2.startswith("# How this brain works (level 2)"))
        self.assertIn("## Routing table", level2)
        self.assertEqual(level1.check(self.brain), [])
        self.assertEqual(check_brain.check(self.brain), [])

    def test_the_check_fails_when_a_copy_drifts(self):
        gemini = self.brain / "GEMINI.md"
        gemini.write_text(read(gemini).replace("Name: not known yet.", "Name: Sam."), encoding="utf-8")
        self.assertEqual(level1.check(self.brain), ["GEMINI.md does not match CLAUDE.md"])
        self.assertIn("GEMINI.md does not match CLAUDE.md", check_brain.check(self.brain))
        r = subprocess.run([sys.executable, str(self.brain / "scripts" / "level1.py"), "check", str(self.brain)],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)
        self.assertIn("GEMINI.md does not match CLAUDE.md", r.stdout)

    def test_the_check_fails_when_the_agents_block_drifts_or_is_gone(self):
        agents = self.brain / "AGENTS.md"
        original = read(agents)
        agents.write_text(original.replace("## Goals this quarter", "## Goals"), encoding="utf-8")
        self.assertEqual(level1.check(self.brain),
                         ["the level 1 block at the top of AGENTS.md does not match CLAUDE.md"])
        agents.write_text(level1.split(original)[1], encoding="utf-8")
        self.assertEqual(level1.check(self.brain), ["AGENTS.md does not start with the level 1 block"])

    def test_sync_copies_claude_md_out_and_keeps_level_2(self):
        claude = self.brain / "CLAUDE.md"
        level2_before = level1.split(read(self.brain / "AGENTS.md"))[1]
        claude.write_text(read(claude).replace("- Name: not known yet.", "- Name: Sam Example (you said so)"),
                          encoding="utf-8")
        self.assertTrue(level1.check(self.brain))
        r = subprocess.run([sys.executable, str(self.brain / "scripts" / "level1.py"), "sync", str(self.brain)],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(level1.check(self.brain), [])
        self.assertIn("Sam Example", read(self.brain / "GEMINI.md"))
        inner, level2 = level1.split(read(self.brain / "AGENTS.md"))
        self.assertIn("Sam Example", inner)
        self.assertEqual(level2, level2_before)

    def test_the_sample_brain_matches_too(self):
        self.assertEqual(level1.check(CORE / "sample" / "brain"), [])


class KitInsideTheBrain(unittest.TestCase):
    """The setup downloads the kit into <brain>/kit first. The brain is still made, and the kit is left alone."""

    def test_a_folder_holding_only_kit_is_ready_and_the_kit_is_untouched_and_not_backed_up(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "b"
            (dest / "kit" / "template").mkdir(parents=True)
            marker = dest / "kit" / "template" / "AGENTS.md"
            marker.write_text("Each {{PEOPLE}} stays as it is. Rian Shedden wrote this kit.\n", encoding="utf-8")
            brain = create_brain(dest)
            self.assertEqual(read(marker), "Each {{PEOPLE}} stays as it is. Rian Shedden wrote this kit.\n")
            self.assertEqual(check_brain.check(brain), [])
            self.assertIn("kit/", read(brain / ".gitignore").splitlines())

    def test_a_folder_orca_made_a_git_repository_is_still_ready_for_a_brain(self):
        # Orca (Rian's test, 19 Oct 2026) makes every new folder a git repository: its .git must not block the brain.
        import check_setup
        from create_brain import create_brain
        with tempfile.TemporaryDirectory() as tmp:
            brain = Path(tmp) / "brain"
            (brain / ".git").mkdir(parents=True)
            (brain / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
            self.assertEqual(check_setup.brain_state(brain), "empty")
            create_brain(brain)
            self.assertTrue((brain / "brain.yaml").is_file())
            self.assertEqual((brain / ".git" / "HEAD").read_text(encoding="utf-8"), "ref: refs/heads/main\n")
        self.assertIn("In Orca, opening a new folder also sets it up for saving versions", read(CORE / "SETUP.md"))
        for script in ("start.sh", "start.ps1"):
            self.assertIn(".git", read(CORE / script).split("refuse" if script == "start.sh" else "$Allowed", 1)[1][:600])

    def test_setup_guide_is_versioned_and_asks_before_creating(self):
        setup = read(CORE / "SETUP.md")
        self.assertIn(f"kit version {read(CORE / 'VERSION').strip()}", setup)
        # The nine headings, in order, are checked in test_flow_setup_guide.py.
        for must in ("Desktop, Documents, or somewhere else", "I'll create it once you say", "Never delete",
                     "Never send, upload or post", "Give steps only for what they picked",
                     "WhatsApp, then the rest", "add my LinkedIn", "kit/create_brain.py",
                     "scripts/level1.py check"):
            self.assertIn(must, setup)
        # the fallback connect list (no connections.yaml): most popular first, each with one line on why it fills the brain.
        # Drummond call, 19 Oct 2026: calendar first (connected, not exported), notes as a source, LinkedIn optional and last.
        menu = setup.split("## 2. Choose what to connect", 1)[1].split("\n## ", 1)[0]
        menu = menu.split("use this list instead", 1)[1]
        names = ["Calendar", "Email", "Documents", "Notion or Slack", "Your existing notes", "WhatsApp", "LinkedIn (optional",
                 "Something else"]
        at = [menu.index(f"**{n}") for n in names]
        self.assertEqual(at, sorted(at))
        for line in [l for l in menu.splitlines() if l[:2] in {f"{i}." for i in range(1, 10)}]:
            self.assertRegex(line, r"\*\*: .{20,}", line)

if __name__ == "__main__":
    unittest.main()
