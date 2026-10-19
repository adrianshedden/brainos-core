"""The kit 2.0 setup guide (approved 19 Oct 2026): one line in any AI app, then nine steps the AI follows,
saving progress after each. Checks the one line word for word, the nine headings in order, that each step
saves the next one, the repository's new name, and the level 1 wording on connections."""
import re
import sys
import tempfile
import unittest
from pathlib import Path

import nonet

nonet.install()
CORE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CORE))
import progress  # noqa: E402
from create_brain import create_brain  # noqa: E402

ONE_LINE = ("Set up my brain from the BrainOS kit at github.com/adrianshedden/brainos-core (read its SETUP.md first "
            "and follow it). Ask me before you change anything, work only in my brain folder, and never send my "
            "files anywhere.")
MAC = "curl -fsSL https://raw.githubusercontent.com/adrianshedden/brainos-core/main/start.sh | sh"
WINDOWS = "irm https://raw.githubusercontent.com/adrianshedden/brainos-core/main/start.ps1 | iex"
CONNECTIONS = "Connections live in your AI app or on your computer, never in this folder, and passwords never go in it."
PY_LINE = "`py`"
OWNED = ["SETUP.md", "README.md", "INSTRUCTIONS.md", "check_setup.py", "progress.py"]


def read(rel):
    return (CORE / rel).read_text(encoding="utf-8")


def flat(text):
    return re.sub(r"\s+", " ", text)


def sections(text):
    """{step number: the text under its heading}."""
    parts = re.split(r"^## (\d)\. .*$", text, flags=re.M)
    return {int(parts[i]): parts[i + 1] for i in range(1, len(parts), 2)}


class OneLine(unittest.TestCase):
    def test_the_one_line_is_word_for_word_in_the_guide_the_readme_and_the_instructions(self):
        for rel in ("SETUP.md", "README.md", "INSTRUCTIONS.md"):
            self.assertIn(ONE_LINE, read(rel), rel)

    def test_the_terminal_lines_are_word_for_word_in_the_readme_and_the_instructions(self):
        for rel in ("README.md", "INSTRUCTIONS.md"):
            for line in (MAC, WINDOWS):
                self.assertIn(line, read(rel), rel)

    def test_the_repository_is_called_brainos_core_everywhere(self):
        for rel in OWNED:
            self.assertNotIn("remyn-core", read(rel), rel)
        for rel in ("SETUP.md", "README.md", "INSTRUCTIONS.md"):
            self.assertIn("github.com/adrianshedden/brainos-core", read(rel), rel)

    def test_windows_people_are_told_to_type_py(self):
        for rel in ("SETUP.md", "README.md", "INSTRUCTIONS.md"):
            text = read(rel)
            self.assertIn(PY_LINE, text, rel)
            self.assertIn("Microsoft Store", text, rel)


class NineSteps(unittest.TestCase):
    def setUp(self):
        self.setup = read("SETUP.md")

    def test_nine_headings_in_order_matching_progress_py(self):
        heads = re.findall(r"^## (\d)\. (.+)$", self.setup, flags=re.M)
        self.assertEqual([int(n) for n, _ in heads], list(range(1, 10)))
        for (n, title), (k, (step_id, name)) in zip(heads, sorted(progress.STEPS.items())):
            self.assertEqual(title, f"{name} ({step_id})", n)
        self.assertEqual([i for i, _ in progress.STEPS.values()],
                         ["one-line", "choose", "connect", "pull-in", "domains", "review", "skills", "schedule", "done"])

    def test_each_step_saves_the_next_one_and_the_last_saves_done(self):
        body = sections(self.setup)
        for n in range(1, 9):
            self.assertIn(f"python3 kit/progress.py . step {n + 1}`", body[n], f"step {n} must save step {n + 1}")
        self.assertIn("python3 kit/progress.py . done", body[9])

    def test_step_one_finds_or_makes_the_brain_and_refreshes_only_the_kit(self):
        one = flat(sections(self.setup)[1])
        for must in ("progress.py . app", "Documents/brain", "iCloud", "OneDrive", "home folder", "setup.yaml",
                     "kit/check_setup.py .", "Carry on from step", "kit/VERSION", "Never touch anything outside `kit`",
                     "kit/create_brain.py . --domains network", "scripts/level1.py check ."):
            self.assertIn(must, one)

    def test_steps_two_and_three_use_connections_yaml_in_the_agreed_order(self):
        body = sections(self.setup)
        two, three = flat(body[2]), flat(body[3])
        self.assertIn("kit/connections.yaml", two)
        order = [two.index(f"(`{t}`)") for t in ("builtin", "custom", "local", "cli", "export")]
        self.assertEqual(order, sorted(order), "routes are offered builtin, custom, local, cli, then export")
        self.assertIn("technical_only: true", two)
        self.assertIn("`any`", two)
        for must in ("proof_read", "progress.py . connected", "progress.py . pending", "tools/TOOLS.md",
                     "without asking", "read-only", "new chat", "export"):
            self.assertIn(must, three)
        self.assertIn("progress.py . pick", two)

    def test_step_four_says_where_the_data_goes_before_anything_is_brought_in(self):
        four = flat(sections(self.setup)[4])
        said = four.index("Your brain's files stay in your folder.")
        for later in ("kit/check_setup.py", "importers/from_connector.py"):
            self.assertLess(said, four.index(later), later)
        self.assertIn("python3 kit/importers/from_connector.py . exports/", four, "the brain first, then the file")
        for must in ("90 days", "who and when only", "Never the message text", "never whole mailboxes",
                     '"people"', '"interactions"', '"when"', '"with"', '"channel"', '"source"'):
            self.assertIn(must, four)

    def test_steps_five_to_nine_use_the_kit_parts_they_need(self):
        body = {n: flat(t) for n, t in sections(self.setup).items()}
        self.assertIn("kit/create_brain.py . --add", body[5])
        self.assertIn("skills/mine-my-context/SKILL.md", body[6])
        self.assertIn("at most five short questions", body[6])
        for skill in ("morning-brief", "weekly-review", "show-it-visually"):
            self.assertIn(skill, body[7])
        self.assertIn("`schedulers`", body[8])
        self.assertIn("automations/AUTOMATIONS.md", body[8])
        self.assertIn("never sends", body[8].lower())
        self.assertIn("skills/show-it-visually/SKILL.md", body[9])
        self.assertIn("name the file behind each point", body[9])
        self.assertIn("Each morning", body[9])
        # Examples may be read on another day: no "today", "this week" or "tomorrow" in them.
        for word in ("this week", "Tomorrow", "today?"):
            self.assertNotIn(word, body[9])

    def test_the_rules_for_a_non_technical_person_are_stated(self):
        rules = flat(self.setup.split("## 1.", 1)[0])
        for must in ("not technical", "Plain British English", "No jargon", "Ask before you change anything",
                     "Never delete anything", "Never send, upload or post", "never in the brain folder",
                     "Passwords, keys and sign-in codes never go in the brain", "technical people only",
                     "fall back to an export file"):
            self.assertIn(must, rules)


class LevelOneWording(unittest.TestCase):
    def test_the_template_says_where_connections_live(self):
        text = read("template/LEVEL1.md")
        self.assertIn(CONNECTIONS, text)
        self.assertNotIn("Never build a live connection", text)
        self.assertIn(CONNECTIONS, read("INSTRUCTIONS.md"))

    def test_every_new_brain_and_the_sample_carry_it_at_every_front_door(self):
        with tempfile.TemporaryDirectory() as tmp:
            brain = create_brain(Path(tmp) / "b")
            for root in (brain, CORE / "sample" / "brain"):
                for door in ("CLAUDE.md", "GEMINI.md", "AGENTS.md"):
                    text = (root / door).read_text(encoding="utf-8")
                    self.assertIn(CONNECTIONS, text, f"{root.name}/{door}")
                    self.assertNotIn("Never build a live connection", text, f"{root.name}/{door}")


if __name__ == "__main__":
    unittest.main()
