"""B15: a connector is written into tools/TOOLS.md the first time it is used, without asking.

Found in a clean-account test on 16 Oct 2026: Google Calendar was used, tools/TOOLS.md still said
"(none yet)", and the AI asked the person whether to list it. The guidance now says: record it, then
tell the person once. It must be in the kit's instructions and in every new brain."""
import sys
import tempfile
import unittest
from pathlib import Path

import nonet

nonet.install()
CORE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CORE))
from create_brain import create_brain  # noqa: E402

RECORD = "the first time you use a connector"
NO_ASK = "without asking"
TELL = "tell the person once"


class ConnectorsRecorded(unittest.TestCase):
    def check(self, text, where):
        for phrase in (RECORD, "tools/TOOLS.md", NO_ASK, TELL):
            self.assertIn(phrase, text, f"{where} is missing: {phrase}")

    def test_the_kit_instructions_say_record_it_and_tell_once(self):
        self.check((CORE / "INSTRUCTIONS.md").read_text(encoding="utf-8"), "INSTRUCTIONS.md")

    def test_every_new_brain_carries_the_rule_at_level_one_and_two(self):
        with tempfile.TemporaryDirectory() as tmp:
            brain = create_brain(Path(tmp) / "b")
            self.check((brain / "CLAUDE.md").read_text(encoding="utf-8"), "CLAUDE.md (level 1)")
            self.check((brain / "AGENTS.md").read_text(encoding="utf-8"), "AGENTS.md (level 2)")
            tools = (brain / "tools" / "TOOLS.md").read_text(encoding="utf-8")
            self.assertIn(RECORD, tools)
            self.assertIn(NO_ASK, tools)
            self.assertNotIn("Add a line when you turn one on", tools,
                             "the old wording left it to the person, so the AI asked")


if __name__ == "__main__":
    unittest.main()
