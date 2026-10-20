"""SETUP offers the sample brain to people who cannot use their own files (Rian, 20 Oct 2026, Tu34),
and every file it names exists, so the offer always works."""
import re
import unittest
from pathlib import Path

CORE = Path(__file__).resolve().parents[1]


class SampleOffer(unittest.TestCase):
    def test_setup_offers_the_sample_and_its_files_exist(self):
        setup = (CORE / "SETUP.md").read_text()
        self.assertIn("No files of their own today?", setup)
        for rel in ("calendar/calendar.ics", "apple/contacts.vcf"):
            self.assertIn(rel, setup)
            self.assertTrue((CORE / "sample" / "exports" / rel).is_file(), rel)
        chats = list((CORE / "sample" / "exports" / "whatsapp").glob("*.txt"))
        self.assertEqual(len(chats), 2)
        self.assertIn("Alex Example", setup)


if __name__ == "__main__":
    unittest.main()
