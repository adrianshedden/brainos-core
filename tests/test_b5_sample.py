import filecmp
import sys
import tempfile
import unittest
from pathlib import Path

import nonet

CORE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CORE / "sample"))
import build_sample  # noqa: E402
import check_brain  # noqa: E402
sys.path.insert(0, str(CORE / "importers"))
import calendar_ics  # noqa: E402

# On a Windows Python with no time-zone data, calendar times are kept as written (with a note saying so), so
# the two files built from the calendar differ from the committed sample. Everything else must still match.
NO_ZONE_DATA = calendar_ics._zone("Europe/London") is None
FROM_THE_CALENDAR = {"memory/calendar/events.yaml", "network/interactions.jsonl"}


def differences(a, b, at=""):
    """Files that differ between two folders, ignoring line endings (Windows writes CRLF, and a Windows
    checkout may too: the words are what must match)."""
    cmp = filecmp.dircmp(a, b)
    out = [f"{at}{n} (only in one)" for n in cmp.left_only + cmp.right_only + cmp.funny_files]
    for name in cmp.common_files:
        left, right = (Path(a) / name).read_bytes(), (Path(b) / name).read_bytes()
        if left.replace(b"\r\n", b"\n") != right.replace(b"\r\n", b"\n"):
            out.append(f"{at}{name}")
    for d in cmp.common_dirs:
        out += differences(Path(a) / d, Path(b) / d, f"{at}{d}/")
    return out


def same_tree(a, b):
    return not differences(a, b)


class Sample(unittest.TestCase):
    def test_committed_sample_matches_a_fresh_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            fresh = build_sample.build(Path(tmp) / "brain")
            differ = differences(fresh, CORE / "sample" / "brain")
            if NO_ZONE_DATA:
                differ = [d for d in differ if d not in FROM_THE_CALENDAR]
                self.assertIn("not converted", (fresh / "memory/calendar/events.yaml").read_text(encoding="utf-8"))
            self.assertEqual(differ, [], "sample/brain is stale: run python3 sample/build_sample.py")
            self.assertEqual(check_brain.check(fresh), [])

    def test_sample_has_imported_content(self):
        b = CORE / "sample" / "brain"
        for rel in ("network/people.jsonl", "network/interactions.jsonl", "memory/conversations/whatsapp/priya-demo.md",
                    "memory/conversations/whatsapp/allotment-group.md", "memory/calendar/events.yaml",
                    "memory/conversations/x-posts.yaml", "memory/profile/x-profile.md",
                    "memory/profile/linkedin-profile.md", "work/WORK.md"):
            self.assertTrue((b / rel).is_file(), rel)


if __name__ == "__main__":
    unittest.main()
