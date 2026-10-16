import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

import nonet

nonet.install()
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "importers"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import linkedin  # noqa: E402
from create_brain import create_brain  # noqa: E402

CONNECTIONS = (
    'Notes:\n"Some emails are missing."\n\n'
    "First Name,Last Name,URL,Email Address,Company,Position,Connected On\n"
    "Ann,One,https://x.test/a,,Acme,Chair,01 Jan 2024\n"
    'Bob,Two,https://x.test/b,b@example.com,Bolt,"Lead, Ops",02 Jan 2024\n'
    "Cy,Three,https://x.test/c,,Cog,Dev,03 Jan 2024\n"
)
PROFILE = "First Name,Last Name,Headline,Summary,Industry,Geo Location\nDee,Demo,Maker,Makes things,Retail,Leeds\n"
POSITIONS = "Company Name,Title,Description,Location,Started On,Finished On\nAcme,Chair,,Leeds,Jan 2020,\nBolt,Dev,,York,Jan 2018,Dec 2019\n"
MESSAGES = ("CONVERSATION ID,CONVERSATION TITLE,FROM,SENDER PROFILE URL,TO,RECIPIENT PROFILE URLS,DATE,SUBJECT,CONTENT,FOLDER\n"
            'c1,,Ann One,,Dee Demo,,2024-01-01 10:00:00 UTC,,"Hi\nthere",INBOX\n'
            "c1,,Dee Demo,,Ann One,,2024-01-01 10:05:00 UTC,,Hello,SENT\n")


def make_zip(path, files):
    with zipfile.ZipFile(path, "w") as zf:
        for name, text in files.items():
            zf.writestr(name, text)


class LinkedIn(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.brain = create_brain(Path(self.tmp.name) / "brain")
        self.zip = Path(self.tmp.name) / "a.zip"

    def test_counts_and_preamble(self):
        make_zip(self.zip, {"Connections.csv": CONNECTIONS, "Profile.csv": PROFILE,
                            "Positions.csv": POSITIONS, "messages.csv": MESSAGES})
        r = linkedin.run(self.zip, self.brain)
        self.assertEqual((r["connections"], r["positions"], r["messages"], r["profile"]), (3, 2, 2, True))
        self.assertEqual(r["skipped"], [])
        text = (self.brain / "network/people.jsonl").read_text()
        people = [json.loads(line) for line in text.splitlines()]
        self.assertEqual([p["name"] for p in people], ["Ann One", "Bob Two", "Cy Three"])
        self.assertEqual(people[1]["position"], "Lead, Ops")
        self.assertEqual(people[1]["emails"], ["b@example.com"])
        self.assertNotIn("Notes:", text)
        self.assertIn("Makes things", (self.brain / "memory/profile/linkedin-profile.md").read_text())
        msgs = [json.loads(line) for line in (self.brain / "network/interactions.jsonl").read_text().splitlines()]
        self.assertEqual([(m["type"], m["from"], m["date"], m["time"]) for m in msgs],
                         [("linkedin_message", "Ann One", "2024-01-01", "10:00"),
                          ("linkedin_message", "Dee Demo", "2024-01-01", "10:05")])
        self.assertEqual(msgs[0]["content"], "Hi\nthere")
        for line in people + msgs:
            self.assertTrue(line["source"] and line["confidence"], line)

    def test_missing_file_reported_and_skipped(self):
        make_zip(self.zip, {"nested/Connections.csv": CONNECTIONS})
        r = linkedin.run(self.zip, self.brain)
        self.assertEqual(r["connections"], 3)
        self.assertEqual(sorted(s["file"] for s in r["skipped"]), ["messages.csv", "positions.csv", "profile.csv"])
        self.assertFalse((self.brain / "memory/profile/linkedin-positions.yaml").exists())

    def test_garbage_file_does_not_crash(self):
        make_zip(self.zip, {"Connections.csv": "this is not a csv header\nfoo"})
        r = linkedin.run(self.zip, self.brain)
        self.assertEqual(r["skipped"][0], {"file": "connections.csv", "reason": "header row not found"})


if __name__ == "__main__":
    unittest.main()
