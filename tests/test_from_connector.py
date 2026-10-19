"""importers/from_connector.py: what an AI read through live connectors goes into the brain (kit 2.0).

It joins the one people list and interactions log through the same merge as the export importers, is
append-only, adds nothing when the same thing is read twice, keeps only a short summary of any message,
labels every line with its source and the day it was read, and refuses a bad file in one plain line
without changing anything. No network."""
import contextlib
import io
import json
import runpy
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

import nonet

nonet.install()
CORE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CORE / "importers"))
sys.path.insert(0, str(CORE))
import calendar_ics  # noqa: E402
import from_connector  # noqa: E402
from create_brain import create_brain  # noqa: E402

SCRIPT = CORE / "importers" / "from_connector.py"
EX = CORE / "sample" / "exports"

READ_1 = {
    "people": [
        {"name": "Priya Demo", "email": "PRIYA@example.com", "source": "gmail"},
        {"name": "Sam Lee", "email": "sam.lee@example.net", "phone": "+44 7700 900123", "source": "gmail"},
        {"name": "Sam Lee", "email": "sam.lee@example.net", "source": "gmail"},  # the same person, twice in one read
        {"name": "Jo Bloggs", "source": "whatsapp"},
    ],
    "interactions": [
        {"when": "2026-10-18T09:30", "with": ["Priya Demo"], "channel": "email", "summary": "Agreed the launch date",
         "source": "gmail"},
        {"when": "2026-10-17", "with": "Jo Bloggs", "channel": "whatsapp", "source": "whatsapp"},
        {"when": "2026-10-16 14:00", "with": ["Sam Lee", "Priya Demo"], "channel": "meeting", "source": "google-calendar"},
    ],
}
READ_2 = {  # a later read over a different window: none of READ_1 is in it
    "people": [{"name": "Ana New", "email": "ana@example.com", "source": "gmail"},
               {"name": "Sam Lee", "email": "sam.lee@example.net", "phone": "+44 7700 900999", "source": "gmail"}],
    "interactions": [{"when": "2026-10-19T08:00", "with": ["Ana New"], "channel": "email", "source": "gmail"}],
}


def jsonl(path):
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()] if path.is_file() else []


class FromConnector(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.brain = create_brain(self.dir / "brain")
        self.people = self.brain / "network" / "people.jsonl"
        self.talks = self.brain / "network" / "interactions.jsonl"

    def write(self, data, name="read.json"):
        path = self.dir / name
        path.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")
        return path

    def run_cli(self, *args):
        """The real command line, in this process (sockets blocked). Returns what it printed."""
        out, old = io.StringIO(), sys.argv
        sys.argv = [str(SCRIPT), *map(str, args)]
        try:
            with contextlib.redirect_stdout(out):
                runpy.run_path(str(SCRIPT), run_name="__main__")
        finally:
            sys.argv = old
        return out.getvalue()

    def snapshot(self):
        return {p: p.read_bytes() for p in (self.people, self.talks) if p.is_file()}

    def test_it_joins_the_people_the_export_importers_found(self):
        calendar_ics.run(EX / "calendar" / "calendar.ics", self.brain, me="alex@example.com")
        before = {p["id"] for p in jsonl(self.people)}
        self.run_cli(self.brain, self.write(READ_1))
        people = jsonl(self.people)
        priya = [p for p in people if p["name"] == "Priya Demo"]
        self.assertEqual(len(priya), 1, "the same email is the same person")
        self.assertEqual(priya[0]["source"], ["calendar", "gmail-live"])
        self.assertEqual(priya[0]["emails"], ["priya@example.com"])
        self.assertEqual(priya[0]["from"]["calendar"]["meetings"], 7, "what the calendar said is untouched")
        self.assertTrue(before <= {p["id"] for p in people})
        sam = [p for p in people if p["name"] == "Sam Lee"]
        self.assertEqual(len(sam), 1, "one person, read twice in one go, is one line")
        self.assertEqual(sam[0]["phones"], ["+44 7700 900123"])
        talks = [t for t in jsonl(self.talks) if t["source"].endswith("-live")]
        self.assertEqual({t["source"] for t in talks}, {"gmail-live", "whatsapp-live", "google-calendar-live"})
        email = next(t for t in talks if t["type"] == "email")
        self.assertEqual((email["date"], email["time"], email["with"]), ("2026-10-18", "09:30", ["Priya Demo"]))
        self.assertEqual(email["summary"], "Agreed the launch date")

    def test_reading_the_same_thing_twice_adds_nothing(self):
        f = self.write(READ_1)
        self.run_cli(self.brain, f)
        first = self.snapshot()
        line = self.run_cli(self.brain, f)
        self.assertEqual(self.snapshot(), first)
        self.assertIn("0 new to the brain", line)
        self.assertIn("0 new, 3 already there", line)
        g = self.write(READ_2, "read2.json")  # Sam gets a second phone: new information, folded in once
        self.run_cli(self.brain, g)
        second = self.snapshot()
        self.run_cli(self.brain, g)
        self.run_cli(self.brain, f)
        self.assertEqual(self.snapshot(), second)

    def test_it_only_ever_adds(self):
        calendar_ics.run(EX / "calendar" / "calendar.ics", self.brain, me="alex@example.com")
        self.run_cli(self.brain, self.write(READ_1))
        rows = jsonl(self.people)
        rows[0]["notes"] = "met at the allotment"
        self.people.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
        people_before = {p["id"]: p for p in jsonl(self.people)}
        talks_before = jsonl(self.talks)
        self.run_cli(self.brain, self.write(READ_2, "read2.json"))
        after = {p["id"]: p for p in jsonl(self.people)}
        for pid, p in people_before.items():
            self.assertIn(pid, after, "nobody is removed")
            for src, said in p["from"].items():
                for k, v in said.items():
                    if isinstance(v, list):
                        self.assertTrue(set(v) <= set(after[pid]["from"][src].get(k, [])), (pid, src, k))
                    else:
                        self.assertEqual(after[pid]["from"][src][k], v, (pid, src, k))
        self.assertEqual(after[rows[0]["id"]]["notes"], "met at the allotment")
        sam = next(p for p in after.values() if p["name"] == "Sam Lee")
        self.assertEqual(sam["phones"], ["+44 7700 900123", "+44 7700 900999"])
        talks_after = jsonl(self.talks)
        for row in talks_before:
            self.assertIn(row, talks_after, "no conversation or meeting is changed or removed")
        self.assertEqual(len(talks_after), len(talks_before) + 1)
        # an export importer running again later leaves the live lines alone
        calendar_ics.run(EX / "calendar" / "calendar.ics", self.brain, me="alex@example.com")
        self.assertEqual([t for t in jsonl(self.talks) if t["source"].endswith("-live")],
                         [t for t in talks_after if t["source"].endswith("-live")])
        self.assertEqual({p["id"] for p in jsonl(self.people)}, set(after))

    def test_it_never_keeps_whole_messages(self):
        body = "SECRET-BODY " * 300
        self.run_cli(self.brain, self.write({"interactions": [{
            "when": "2026-10-18", "with": ["Priya Demo"], "channel": "email", "source": "gmail",
            "summary": "Line one\nline two " + "x" * 500, "body": body, "subject": "Private subject",
            "attachments": ["a.pdf"]}]}))
        text = self.talks.read_text(encoding="utf-8")
        self.assertNotIn("SECRET-BODY", text)
        self.assertNotIn("Private subject", text)
        row = jsonl(self.talks)[0]
        self.assertLessEqual(len(row["summary"]), from_connector.SUMMARY_MAX)
        self.assertNotIn("\n", row["summary"])
        self.assertEqual(set(row), {"id", "type", "date", "with", "summary", "read_on", "source", "confidence"})

    def test_every_line_says_where_it_came_from_and_when(self):
        calendar_ics.run(EX / "calendar" / "calendar.ics", self.brain, me="alex@example.com")
        self.run_cli(self.brain, self.write(READ_1))
        today = date.today().isoformat()
        for f in (self.people, self.talks):
            for line in jsonl(f):
                self.assertTrue(line.get("source"), line)
                self.assertIn(line.get("confidence"), ("high", "medium", "low"), line)
        for p in jsonl(self.people):
            for src, said in p["from"].items():
                if src.endswith("-live"):
                    self.assertEqual(said["read_on"], today)
        for t in jsonl(self.talks):
            date.fromisoformat(t["date"])
            if t["source"].endswith("-live"):
                self.assertEqual(t["read_on"], today)

    def test_a_whatsapp_name_read_live_is_medium_confidence(self):
        self.run_cli(self.brain, self.write(READ_1))
        jo = next(p for p in jsonl(self.people) if p["name"] == "Jo Bloggs")
        self.assertEqual((jo["source"], jo["confidence"]), (["whatsapp-live"], "medium"))
        priya = next(p for p in jsonl(self.people) if p["name"] == "Priya Demo")
        self.assertEqual(priya["confidence"], "high")

    def test_source_names_are_tidied_to_one_id(self):
        self.run_cli(self.brain, self.write({"people": [
            {"name": "A One", "email": "a@example.com", "source": "Google Calendar"},
            {"name": "B Two", "email": "b@example.com", "source": "google-calendar-live"}]}))
        self.assertEqual({s for p in jsonl(self.people) for s in p["source"]}, {"google-calendar-live"})

    def test_bad_files_are_refused_in_one_plain_line_and_change_nothing(self):
        self.run_cli(self.brain, self.write(READ_1))
        good = READ_1["people"][0]
        cases = [
            ("{not json", "not valid JSON"),
            ('[{"name": "x"}]', "one JSON object"),
            ('{"contacts": []}', "one JSON object"),
            ('{"people": {"name": "x"}}', '"people" must be a list'),
            ({"people": [good, "Sam"]}, "Entry 2 in people is not an object"),
            ({"people": [good, {"name": "No Source"}]}, 'Entry 2 in people has no "source"'),
            ({"people": [{"phone": "123", "source": "gmail"}]}, 'neither a "name" nor an "email"'),
            ({"people": [{"name": "X", "email": 42, "source": "gmail"}]}, "not text"),
            ({"interactions": [{"when": "yesterday", "with": "X", "channel": "email", "source": "gmail"}]}, '"when"'),
            ({"interactions": [{"when": "2026-13-01", "with": "X", "channel": "email", "source": "gmail"}]}, '"when"'),
            ({"interactions": [{"when": "2026-10-01T25:00", "with": "X", "channel": "email", "source": "gmail"}]}, '"when"'),
            ({"interactions": [{"when": "2026-10-01", "with": [], "channel": "email", "source": "gmail"}]}, '"with"'),
            ({"interactions": [{"when": "2026-10-01", "with": "X", "source": "gmail"}]}, '"channel"'),
        ]
        before = self.snapshot()
        for data, phrase in cases:
            with self.subTest(phrase=phrase, data=data):
                with self.assertRaises(SystemExit) as stop:
                    self.run_cli(self.brain, self.write(data, "bad.json"))
                message = str(stop.exception.code)
                self.assertIn(phrase, message)
                self.assertIn("Nothing was changed.", message)
                self.assertEqual(len(message.splitlines()), 1)
                self.assertEqual(self.snapshot(), before)

    def test_a_missing_file_or_a_folder_that_is_not_a_brain_is_refused(self):
        with self.assertRaises(SystemExit) as stop:
            self.run_cli(self.brain, self.dir / "nowhere.json")
        self.assertIn("Nothing was changed.", str(stop.exception.code))
        with self.assertRaises(SystemExit) as stop:
            self.run_cli(self.dir / "not-a-brain", self.write(READ_1))
        self.assertIn("not a brain folder", str(stop.exception.code))
        with self.assertRaises(SystemExit) as stop:
            self.run_cli(self.brain)
        self.assertIn("Usage", str(stop.exception.code))

    def test_either_order_of_the_two_paths_works(self):
        self.run_cli(self.write(READ_1), self.brain)
        self.assertTrue(any(p["name"] == "Sam Lee" for p in jsonl(self.people)))

    def test_a_brain_without_a_network_area_keeps_people_in_memory(self):
        brain = create_brain(self.dir / "plain", domains=[])
        self.run_cli(brain, self.write(READ_1))
        self.assertTrue((brain / "memory" / "people" / "people.jsonl").is_file())
        self.assertTrue((brain / "memory" / "people" / "interactions.jsonl").is_file())
        self.assertFalse((brain / "network").exists())

    def test_the_command_prints_one_plain_line_and_a_bad_file_exits_without_a_traceback(self):
        ok = subprocess.run([sys.executable, str(SCRIPT), str(self.brain), str(self.write(READ_1))],
                            capture_output=True, text=True)
        self.assertEqual(ok.returncode, 0, ok.stderr)
        self.assertEqual(len(ok.stdout.strip().splitlines()), 1)
        self.assertIn("4 people read, 3 new to the brain; 3 conversations and meetings read, 3 new", ok.stdout)
        bad = subprocess.run([sys.executable, str(SCRIPT), str(self.brain), str(self.write("{oops", "bad.json"))],
                             capture_output=True, text=True)
        self.assertEqual(bad.returncode, 1)
        self.assertNotIn("Traceback", bad.stderr)
        self.assertIn("not valid JSON", bad.stderr)


if __name__ == "__main__":
    unittest.main()
