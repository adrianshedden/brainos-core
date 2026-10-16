import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

import nonet

nonet.install()
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "importers"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import whatsapp  # noqa: E402
from create_brain import create_brain  # noqa: E402

IPHONE = ("[15/03/2024, 09:41:22] Ann: Hello 😀\n"
          "[15/03/2024, 09:42:00] Bob: Second line follows\nstill Bob\n"
          "[16/03/2024, 18:05:10] Ann: Bye\n")
ANDROID_GROUP = ("13/03/2024, 09:00 - Ann created group \"Club\"\n"
                 "13/03/2024, 09:01 - Ann: hi all\n"
                 "13/03/2024, 09:02 - Bob: hello 🎉\n"
                 "Sender: line with no timestamp\n"
                 "13/03/2024, 09:03 - Cy: morning\n"
                 "31/02/2024, 09:04 - Cy: impossible date\n")
US_ANDROID = "3/15/24, 9:41 PM - Ann: evening\n3/16/24, 10:00 AM - Bob: morning\n"


class WhatsApp(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.brain = create_brain(self.dir / "brain")
        whatsapp.save_names(self.brain, ["Ann"])  # the person's own name, given once (see B14)

    def test_iphone_one_to_one(self):
        msgs, system = whatsapp.parse_chat(IPHONE)
        self.assertEqual(len(msgs), 3)
        self.assertEqual((msgs[0]["date"], msgs[0]["time"]), ("2024-03-15", "09:41"))
        self.assertIn("still Bob", msgs[1]["text"])

    def test_android_group_with_oddities(self):
        msgs, system = whatsapp.parse_chat(ANDROID_GROUP)
        self.assertEqual(len(msgs), 4)  # 3 normal + impossible date kept, undated
        self.assertEqual(system, 1)
        self.assertIsNone(msgs[-1]["date"])
        self.assertIn("line with no timestamp", msgs[1]["text"])

    def test_month_first_dates_and_am_pm(self):
        msgs, _ = whatsapp.parse_chat(US_ANDROID)
        self.assertEqual((msgs[0]["date"], msgs[0]["time"]), ("2024-03-15", "21:41"))
        self.assertEqual((msgs[1]["date"], msgs[1]["time"]), ("2024-03-16", "10:00"))

    def test_run_writes_both_kinds_from_folder_and_zip(self):
        ex = self.dir / "ex"
        ex.mkdir()
        (ex / "WhatsApp Chat with Ann.txt").write_text(IPHONE, encoding="utf-8")
        (ex / "WhatsApp Chat - Club.txt").write_text(ANDROID_GROUP, encoding="utf-8")
        r = whatsapp.run(ex, self.brain)
        self.assertEqual((r["chats"], r["messages"], r["groups"], r["one_to_one"], r["undated"]), (2, 7, 1, 1, 1))
        self.assertIn('kind: "group"', (self.brain / "memory/conversations/whatsapp/club.md").read_text())
        self.assertIn('kind: "one-to-one"', (self.brain / "memory/conversations/whatsapp/ann.md").read_text())
        zpath = self.dir / "chat.zip"
        with zipfile.ZipFile(zpath, "w") as zf:
            zf.writestr("_chat.txt", IPHONE)
        self.assertEqual(whatsapp.run(zpath, create_brain(self.dir / "b2"), me=["Ann"])["messages"], 3)

    def iphone_zip(self, folder, chat, text):
        """An iPhone export: the text is always _chat.txt; only the .zip's name says which chat it is."""
        folder.mkdir(exist_ok=True)
        z = folder / f"WhatsApp Chat - {chat}.zip"
        with zipfile.ZipFile(z, "w") as zf:
            zf.writestr("_chat.txt", text)
        return z

    def chats(self):
        return sorted(p.name for p in (self.brain / "memory/conversations/whatsapp").glob("*.md"))

    def test_iphone_zips_are_named_from_the_zip_and_never_overwrite_each_other(self):
        sam = self.iphone_zip(self.dir / "ex", "Sam Jones", IPHONE)
        priya = self.iphone_zip(self.dir / "ex", "Priya Demo", ANDROID_GROUP)
        whatsapp.run(sam, self.brain)
        whatsapp.run(priya, self.brain)
        self.assertEqual(self.chats(), ["priya-demo.md", "sam-jones.md"])
        self.assertIn('chat: "Sam Jones"', (self.brain / "memory/conversations/whatsapp/sam-jones.md").read_text())
        with zipfile.ZipFile(self.dir / "WhatsApp Chat with Ann.zip", "w") as zf:  # the "with" form too
            zf.writestr("_chat.txt", IPHONE)
        whatsapp.run(self.dir / "WhatsApp Chat with Ann.zip", self.brain)
        self.assertIn("ann.md", self.chats())

    def test_reimporting_the_same_export_keeps_one_file(self):
        sam = self.iphone_zip(self.dir / "ex", "Sam Jones", IPHONE)
        for _ in range(2):
            r = whatsapp.run(sam, self.brain)
            self.assertEqual(r["renamed"], [])
        self.assertEqual(self.chats(), ["sam-jones.md"])

    def test_a_folder_of_iphone_zips_and_an_unzipped_one(self):
        ex = self.dir / "ex"
        self.iphone_zip(ex, "Sam Jones", IPHONE)
        self.iphone_zip(ex, "Priya Demo", ANDROID_GROUP)
        (ex / "WhatsApp Chat - Club").mkdir()
        (ex / "WhatsApp Chat - Club" / "_chat.txt").write_text(US_ANDROID, encoding="utf-8")
        r = whatsapp.run(ex, self.brain)
        self.assertEqual(r["chats"], 3)
        self.assertEqual(self.chats(), ["club.md", "priya-demo.md", "sam-jones.md"])

    def test_two_different_chats_with_the_same_name_both_survive_and_are_reported(self):
        first = self.iphone_zip(self.dir / "a", "Sam", IPHONE)
        second = self.iphone_zip(self.dir / "b", "Sam", US_ANDROID)
        whatsapp.run(first, self.brain)
        r = whatsapp.run(second, self.brain)
        self.assertEqual(self.chats(), ["sam-2.md", "sam.md"])
        self.assertEqual(r["renamed"], [{"chat": "Sam", "file": "sam-2.md"}])
        self.assertIn("still Bob", (self.brain / "memory/conversations/whatsapp/sam.md").read_text())
        whatsapp.run(second, self.brain)  # and re-importing the second one finds its own file again
        whatsapp.run(first, self.brain)
        self.assertEqual(self.chats(), ["sam-2.md", "sam.md"])

    def test_junk_file_is_skipped_not_fatal(self):
        f = self.dir / "junk.txt"
        f.write_text("nothing like a chat\n\xff\n")
        r = whatsapp.run(f, self.brain)
        self.assertEqual((r["chats"], r["skipped"][0]["reason"]), (0, "no messages found"))


if __name__ == "__main__":
    unittest.main()
