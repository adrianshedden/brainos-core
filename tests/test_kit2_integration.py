"""Kit 2.0 integration (19 Oct 2026): the shared bits settled when the flow, skills, domains and connections
work came together. Each test pins one decision, so a later edit cannot quietly undo it."""
import re
import unittest
from pathlib import Path

import nonet

nonet.install()
CORE = Path(__file__).resolve().parents[1]


def read(rel):
    return (CORE / rel).read_text(encoding="utf-8")


def flat(text):
    return re.sub(r"\s+", " ", text)


def step(n):
    parts = re.split(r"^## (\d)\. .*$", read("SETUP.md"), flags=re.M)
    return flat({int(parts[i]): parts[i + 1] for i in range(1, len(parts), 2)}[n])


class SetupGuide(unittest.TestCase):
    def test_the_ai_never_writes_people_lines_by_hand(self):
        """Kit 1.0 told the AI to add people to the people list by hand when an importer was missing."""
        four = step(4)
        self.assertIn("Never write lines in the people list or the interactions log by hand", four)
        self.assertNotIn('"confidence": "medium"', read("SETUP.md"))
        self.assertNotIn("by hand, each with", read("SETUP.md"))
        self.assertIn("python3 kit/importers/from_connector.py . exports/from-<source id>-<YYYY-MM-DD>.json", four)

    def test_one_exception_to_working_only_in_the_brain_folder(self):
        rules = flat(read("SETUP.md").split("## 1.", 1)[0])
        self.assertIn("the one exception to \"work only in my brain folder\"", rules)
        self.assertIn("with the person's yes, you may add a connection in the AI app's own settings", rules)
        for app in ("Cursor", "OpenCode", "Codex", "Claude Code"):
            self.assertIn(app, rules)
        self.assertIn("Never put a connection's settings inside the brain folder", rules)

    def test_adding_domains_uses_add_in_the_guide_and_the_instructions(self):
        line = "python3 kit/create_brain.py . --add work,family"
        self.assertIn(line, step(5))
        self.assertIn('"Adding a domain" in `DOMAINS.md`', step(5))
        self.assertIn(line, read("INSTRUCTIONS.md"))
        self.assertIn(line, read("template/DOMAINS.md"))
        self.assertIn("--add", read("README.md"))

    def test_step_one_chooses_the_folder_like_the_start_scripts(self):
        one = step(1)
        self.assertIn("the same way the terminal line does", one)
        self.assertIn("or one holding a `kit` folder", one)
        self.assertIn("use it; never download a second copy", one)
        for word in ("`Documents/brain`", "`brain` in their home folder", "iCloud", "OneDrive"):
            self.assertIn(word, one)
        for script in ("start.sh", "start.ps1"):
            text = read(script)
            self.assertIn("brain.yaml", text)
            self.assertRegex(text, r"BRAINOS_REF[^\n]*main", f"{script}: the kit branch defaults to main")

    def test_the_live_read_source_is_the_connections_id(self):
        four = step(4)
        self.assertIn("`source` is the source id from `connections.yaml` (never the name of an app or tool in between)", four)
        self.assertIn('"google-calendar, 2026-10-21"', four)
        self.assertIn("one entry per person", four)


class Template(unittest.TestCase):
    def test_agents_md_says_paste_the_one_line_again(self):
        text = read("template/AGENTS.md")
        self.assertNotIn("Remyn setup instruction", text)
        self.assertIn("ask the person to paste the one line again", text)
        self.assertIn("python3 kit/importers/from_connector.py . exports/", text)

    def test_views_has_a_line_in_the_file_index_and_stays_in_the_backup(self):
        text = read("template/AGENTS.md")
        self.assertIn("\nviews/             pages made by show-it-visually, views/<YYYY-MM-DD>-<name>.html "
                      "(made the first time one is saved)\n", text)
        self.assertNotIn("views", read("template/.gitignore"), "views/ is part of the private backup (decided)")

    def test_suggested_scheduled_jobs_lead_with_the_brief_and_the_review(self):
        self.assertIn("Daily: `morning-brief` (each morning). Weekly: `weekly-review` (Friday afternoon).",
                      read("template/automations/AUTOMATIONS.md"))

    def test_the_network_domain_describes_live_reads(self):
        text = flat(read("template/domains/network.md"))
        for must in ("`summary`", "`read_on`", "`calendar`", "`email`", "-live"):
            self.assertIn(must, text)


class Readme(unittest.TestCase):
    def test_the_paid_line_stays_as_locked(self):
        self.assertIn("- Paid: Remyn, the guided set-up website, with templates and support, on top of this same BrainOS core.",
                      read("README.md"))

    def test_the_kit_version_is_two(self):
        self.assertEqual(read("VERSION").strip(), "2.0")


if __name__ == "__main__":
    unittest.main()
