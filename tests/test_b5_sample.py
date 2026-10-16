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


def same_tree(a, b):
    cmp = filecmp.dircmp(a, b)
    if cmp.left_only or cmp.right_only or cmp.diff_files or cmp.funny_files:
        return False
    return all(same_tree(Path(a) / d, Path(b) / d) for d in cmp.common_dirs)


class Sample(unittest.TestCase):
    def test_committed_sample_matches_a_fresh_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            fresh = build_sample.build(Path(tmp) / "brain")
            self.assertTrue(same_tree(fresh, CORE / "sample" / "brain"),
                            "sample/brain is stale: run python3 sample/build_sample.py")
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
