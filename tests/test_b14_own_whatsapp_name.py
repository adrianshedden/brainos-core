"""B14: the person importing WhatsApp is never listed as one of their own contacts.

Found in a clean-account test on 16 Oct 2026: one chat was imported, the importer could not tell which
name was the person's own, and listed them (by their own first name) as a contact until they said which name was theirs.
Now the importer needs the person's own WhatsApp name before it writes anything: from --me (remembered
in brain.yaml), from brain.yaml, or from the Name line in CLAUDE.md when it matches someone in the chats.
With none of those it stops, changes nothing, and asks."""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

import nonet

nonet.install()
CORE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CORE / "importers"))
sys.path.insert(0, str(CORE))
import whatsapp  # noqa: E402
from create_brain import create_brain  # noqa: E402

CHAT = ("[15/03/2024, 09:41:22] Jo: Morning, still on for Friday?\n"
        "[15/03/2024, 09:42:00] Sam Jones: Yes, see you at 10\n")
LATER = ("[20/03/2024, 18:00:00] Priya Demo: Thanks for today\n"
         "[20/03/2024, 18:05:00] Jo: Good to see you\n")


def jsonl(path):
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()] if path.is_file() else []


class OwnWhatsAppName(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.brain = create_brain(self.dir / "brain")
        self.chat = self.dir / "WhatsApp Chat with Sam Jones.txt"
        self.chat.write_text(CHAT, encoding="utf-8")

    def people(self):
        return [p["name"] for p in jsonl(self.brain / "network/people.jsonl")]

    def contacts_in_interactions(self):
        return [n for i in jsonl(self.brain / "network/interactions.jsonl") for n in i.get("with", [])]

    def test_one_chat_and_no_name_known_asks_and_changes_nothing(self):
        before = sorted(p.relative_to(self.brain).as_posix() for p in self.brain.rglob("*"))
        with self.assertRaises(whatsapp.NeedOwnName) as caught:
            whatsapp.run(self.chat, self.brain)
        self.assertEqual(sorted(caught.exception.names), ["Jo", "Sam Jones"])
        after = sorted(p.relative_to(self.brain).as_posix() for p in self.brain.rglob("*"))
        self.assertEqual(before, after, "nothing may be written before the person says which name is theirs")

    def test_the_command_line_asks_in_plain_words_and_names_the_choices(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(SystemExit) as caught:
            whatsapp.main(["whatsapp.py", str(self.chat), str(self.brain)])
        said = str(caught.exception.code)
        self.assertNotEqual(caught.exception.code, 0)
        for part in ("Which of these names is yours", "Jo", "Sam Jones", "--me"):
            self.assertIn(part, said)
        self.assertNotIn("Jo", self.people())

    def test_me_is_never_a_contact_and_is_remembered_for_the_next_import(self):
        whatsapp.run(self.chat, self.brain, me=["Jo"])
        self.assertEqual(self.people(), ["Sam Jones"])
        self.assertNotIn("Jo", self.contacts_in_interactions())
        self.assertIn('whatsapp_names: ["Jo"]', (self.brain / "brain.yaml").read_text(encoding="utf-8"))
        later = self.dir / "WhatsApp Chat with Priya Demo.txt"
        later.write_text(LATER, encoding="utf-8")
        whatsapp.run(later, self.brain)  # no --me: brain.yaml answers, nobody is asked twice
        self.assertEqual(sorted(self.people()), ["Priya Demo", "Sam Jones"])
        self.assertNotIn("Jo", self.contacts_in_interactions())

    def test_the_name_line_in_claude_md_is_used_when_it_is_in_the_chats(self):
        claude = self.brain / "CLAUDE.md"
        claude.write_text(claude.read_text(encoding="utf-8").replace(
            "- Name: not known yet.", "- Name: Jo (source: you said so on 2026-10-16; confidence: high)"), encoding="utf-8")
        whatsapp.run(self.chat, self.brain)
        self.assertEqual(self.people(), ["Sam Jones"])

    def test_a_claude_md_name_that_is_not_in_the_chats_still_asks(self):
        claude = self.brain / "CLAUDE.md"
        claude.write_text(claude.read_text(encoding="utf-8").replace(
            "- Name: not known yet.", "- Name: Kim Example"), encoding="utf-8")
        with self.assertRaises(whatsapp.NeedOwnName):
            whatsapp.run(self.chat, self.brain)

    def test_a_brain_made_before_this_fix_learns_the_name_too(self):
        y = self.brain / "brain.yaml"
        y.write_text("\n".join(l for l in y.read_text(encoding="utf-8").splitlines()
                               if not l.startswith("whatsapp_names")) + "\n", encoding="utf-8")
        whatsapp.run(self.chat, self.brain, me=["Jo"])
        self.assertIn('whatsapp_names: ["Jo"]', y.read_text(encoding="utf-8"))
        self.assertEqual(self.people(), ["Sam Jones"])

    def test_the_instructions_tell_the_ai_to_ask_once(self):
        for f in (CORE / "INSTRUCTIONS.md", CORE / "template" / "AGENTS.md"):
            text = f.read_text(encoding="utf-8")
            self.assertIn("their own name as it shows in their WhatsApp chats", text, f)
            self.assertIn("Ask once", text, f)
            self.assertIn("never listed as a contact", text, f)


if __name__ == "__main__":
    unittest.main()
