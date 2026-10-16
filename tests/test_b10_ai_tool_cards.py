"""B10: one card per AI tool. Every claim on every card names its source and the date it was checked;
a claim that could not be checked says so in its own words rather than being left off."""
import re
import sys
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

import nonet

nonet.install()
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_brain  # noqa: E402
from create_brain import create_brain  # noqa: E402

TOOLS = {"claude-desktop.md", "claude-ai.md", "claude-code.md", "chatgpt.md", "codex.md", "opencode.md",
         "cursor.md", "orca.md"}
CARDS = TOOLS | {"other-ai-tools.md"}
SECTIONS = ("## How to point it at your brain", "## What it can do", "## What it cannot do")
SOURCED = re.compile(r"\(Source: (https://\S+), checked (\d{1,2} [A-Z][a-z]+ \d{4})\)$")
# A claim seen first-hand in the tool itself, when no help page says it yet: where it was seen, and when.
SEEN = re.compile(r"\(Source: ([A-Z][^()]*? on an? [A-Z][^(),]*), seen (\d{1,2} [A-Z][a-z]+ \d{4})\)$")
UNCHECKED = re.compile(r"\(Not checked: [^()]+\.\)$")
# The latest date a card may claim to have been checked. Move it forward when a card is re-checked.
LAST_CHECK = date(2026, 10, 15)


def when(text):
    for fmt in ("%d %B %Y", "%d %b %Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"not a date: {text}")


TEMPLATE = Path(__file__).resolve().parents[1] / "template"


def cards():
    """The cards, and their index (tools/TOOLS.md) as README.md."""
    found = {p.name: p.read_text(encoding="utf-8") for p in (TEMPLATE / "tools" / "ai-tools").glob("*.md")}
    return dict(found, **{"README.md": (TEMPLATE / "tools" / "TOOLS.md").read_text(encoding="utf-8")})


class AiToolCards(unittest.TestCase):
    def test_one_card_per_ai_tool_is_declared_and_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            brain = create_brain(Path(tmp) / "b")
            self.assertEqual({p.name for p in (brain / "tools" / "ai-tools").glob("*.md")}, CARDS)
            self.assertEqual(check_brain.check(brain), [])

    def test_the_index_lists_every_card(self):
        index = cards()["README.md"]
        for name in CARDS:
            self.assertIn(f"`{name}`", index)

    def test_no_card_claims_automatic_reading(self):
        for name, text in cards().items():
            text = text.lower()
            self.assertNotIn("automatically read", text, name)
            self.assertNotIn("reads itself", text.replace("does not read itself", ""), name)

    def test_every_claim_names_its_source_and_check_date_or_says_it_was_not_checked(self):
        for name, text in cards().items():
            if name == "README.md":
                continue  # the index in tools/TOOLS.md
            claims = [line for line in text.splitlines() if line.startswith("- ")]
            self.assertTrue(claims, name)
            for line in claims:
                sourced = SOURCED.search(line) or SEEN.search(line)
                unchecked = UNCHECKED.search(line)
                self.assertTrue(sourced or unchecked, f"{name}: no source or 'Not checked' on: {line}")
                if sourced:
                    self.assertLessEqual(when(sourced.group(2)), LAST_CHECK, f"{name}: {line}")
            # Prose outside the bullets would be an unsourced claim: one plain instruction line at most.
            prose = [line for line in text.splitlines()
                     if line.strip() and not line.startswith(("#", "- "))]
            self.assertLessEqual(len(prose), 1, f"{name}: unsourced prose {prose}")

    def test_each_named_tool_says_how_to_connect_and_what_it_can_and_cannot_do(self):
        for name in TOOLS:
            text = cards()[name]
            for heading in SECTIONS:
                self.assertIn(heading, text, name)
                body = text.split(heading, 1)[1].split("\n## ", 1)[0]
                self.assertRegex(body, r"(?m)^- ", f"{name}: nothing under {heading}")
            self.assertRegex(text, SOURCED.pattern.rstrip("$"), f"{name}: no checked source at all")


if __name__ == "__main__":
    unittest.main()
