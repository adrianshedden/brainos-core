"""B12: what the kit tells an AI about where the data goes. An old rule ("nothing leaves their machine")
made Claude stop at import time and offer a menu of four work-arounds. The rule now says the truth once
and lets the AI go ahead; if the exports are out of sight, the AI offers exactly two choices."""
import re
import unittest
from pathlib import Path

import nonet

nonet.install()
CORE = Path(__file__).resolve().parents[1]
DOCS = ["README.md", "INSTRUCTIONS.md", "GITHUB.md", "template/CLAUDE.md", "template/AGENTS.md", "template/README.md",
        "template/exports/README.md", "template/tools/TOOLS.md", "template/tools/ai-tools/claude-desktop.md"]
# What the AI reads: the kit's own instructions, and in the brain the rules (CLAUDE.md) and importing (AGENTS.md).
AI_INSTRUCTIONS = ["INSTRUCTIONS.md", "template/CLAUDE.md"]
AI_IMPORTING = ["INSTRUCTIONS.md", "template/AGENTS.md"]
# Promises the kit cannot keep once an AI tool reads the brain, and which stopped Claude cold.
UNTRUE = [r"nothing leaves (their|your) (machine|computer)", r"everything stays on this machine",
          r"do not send any file from this folder to a website or service"]
# The approved privacy wording (16 Oct 2026), word for word, wherever the kit says where the data goes.
APPROVED = ("Your brain is stored as plain files on your laptop. When you use a cloud AI provider (Anthropic, "
            "OpenAI and others), whatever their agent reads is processed by that provider, like any chat. Run it "
            "with a local model in the future and it stays fully private on your machine. That is what we are "
            "working towards.")
SAYS_WHERE = ["README.md", "INSTRUCTIONS.md", "template/CLAUDE.md", "template/tools/TOOLS.md",
              "sample/brain/CLAUDE.md", "sample/brain/tools/TOOLS.md"]
# The wording it replaced, which must not come back.
OLD = ["stored as files on your own computer", "processed by that tool's provider", "processed by that AI's provider",
       "processed by the company behind the tool", "Anthropic's servers. It is the same"]


def read(rel):
    return (CORE / rel).read_text(encoding="utf-8")


def flat(text):
    return re.sub(r"\s+", " ", text)


class WhereDataGoes(unittest.TestCase):
    def test_no_doc_promises_the_files_never_leave_the_computer(self):
        for rel in DOCS:
            text = read(rel).lower()
            for pattern in UNTRUE:
                self.assertNotRegex(text, pattern, rel)

    def test_ai_says_it_once_then_goes_ahead(self):
        for rel in AI_INSTRUCTIONS:
            text = flat(read(rel))
            self.assertIn(APPROVED, text, rel)
            self.assertIn("The importers never use the internet.", text, rel)
            self.assertIn("Nothing is published unless you back up to your own private GitHub.", text, rel)
            self.assertIn("Do not stop to offer other ways of doing it.", text, rel)
            self.assertIn("Only the person's own data", text, rel)
            self.assertRegex(text, r"Never build a live connection here", rel)

    def test_every_place_that_says_where_data_goes_uses_the_approved_words(self):
        for rel in SAYS_WHERE:
            text = flat(read(rel))
            self.assertIn(APPROVED, text, rel)
            for old in OLD:
                self.assertNotIn(old, text, rel)

    def test_exports_out_of_sight_means_two_choices_in_one_message(self):
        for rel in AI_IMPORTING:
            text = flat(read(rel))
            self.assertIn("exports/", text, rel)
            self.assertRegex(text, r"one short message with (these )?two choices, and no others", rel)
            self.assertIn("Allow once", text, rel)
            self.assertIn("read and change everything in Downloads", text, rel)
        self.assertIn("check_setup.py", read("INSTRUCTIONS.md").split("1. Choose the personal domains")[0])

    def test_readme_explains_where_data_goes_and_free_versus_paid(self):
        readme = read("README.md")
        for heading in ("## Where your data goes", "## Free and paid"):
            self.assertIn(heading, readme)
        self.assertIn(APPROVED, flat(readme))


if __name__ == "__main__":
    unittest.main()
