"""The X (Twitter) archive drop: your own posts become memory/conversations/x-posts.yaml and your
profile becomes memory/profile/x-profile.md. Checked against the made-up archive the sample brain is built
from, and against the shapes a real archive has: a split posts file, the older names, a damaged part."""
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
import x_export  # noqa: E402
from create_brain import create_brain  # noqa: E402

CORE = Path(__file__).resolve().parents[1]
SAMPLE_X = CORE / "sample" / "exports" / "x"


def js(kind, records, part=0):
    return f"window.YTD.{kind}.part{part} = " + json.dumps(records, indent=2)


def tweet(ident, created="Fri Mar 15 09:41:22 +0000 2024", text="hello", **extra):
    return {"tweet": {"id_str": ident, "created_at": created, "full_text": text, **extra}}


class XExport(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.brain = create_brain(Path(self.tmp.name) / "brain")

    def archive(self, files, name="archive"):
        """An unzipped archive folder holding the given data/*.js files."""
        folder = Path(self.tmp.name) / name / "data"
        folder.mkdir(parents=True)
        for filename, text in files.items():
            (folder / filename).write_text(text, encoding="utf-8")
        return folder.parent

    def posts(self):
        return (self.brain / "memory/conversations/x-posts.yaml").read_text(encoding="utf-8")

    def profile(self):
        return (self.brain / "memory/profile/x-profile.md").read_text(encoding="utf-8")

    def test_the_sample_archive_reads_my_posts_my_profile_and_skips_reposts(self):
        r = x_export.run(SAMPLE_X, self.brain)
        self.assertEqual((r["posts"], r["reposts"], r["handle"], r["undated"]), (3, 1, "alexexample", 0))
        self.assertEqual(r["skipped"], [])
        posts = self.posts()
        self.assertEqual(posts.count("- date:"), 3)
        self.assertNotIn("RT @", posts)  # a repost is someone else's words
        self.assertIn('link: "https://x.com/alexexample/status/1700000000000000001"', posts)
        self.assertIn("# Alex Example (@alexexample)", self.profile())
        self.assertIn("- Joined: 2015-03-02", self.profile())

    def test_posts_split_across_parts_are_all_read(self):
        """X splits a big account's posts into tweets.js, tweets-part1.js and so on. Reading only the
        first file would silently drop most of the person's writing."""
        folder = self.archive({"tweets.js": js("tweets", [tweet("1")]),
                               "tweets-part1.js": js("tweets", [tweet("2")], part=1),
                               "tweets-part2.js": js("tweets", [tweet("3")], part=2)})
        self.assertEqual(x_export.run(folder, self.brain)["posts"], 3)

    def test_the_older_archive_names_still_work(self):
        """Archives downloaded years ago call the file tweet.js and the field text."""
        folder = self.archive({"tweet.js": "window.YTD.tweet.part0 = " + json.dumps(
            [{"tweet": {"id_str": "9", "created_at": "Mon Apr 08 19:30:11 +0000 2024",
                        "text": "written before full_text existed"}}])})
        r = x_export.run(folder, self.brain)
        self.assertEqual(r["posts"], 1)
        self.assertIn("written before full_text existed", self.posts())

    def test_a_zip_and_the_unzipped_folder_give_the_same_posts(self):
        archive = Path(self.tmp.name) / "twitter.zip"
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("Your archive.html", "<html>not data</html>")
            for p in sorted(SAMPLE_X.rglob("*")):
                if p.is_file():
                    zf.write(p, str(p.relative_to(SAMPLE_X)))
        from_zip = x_export.run(archive, self.brain)
        zipped_posts = self.posts()
        from_folder = x_export.run(SAMPLE_X, self.brain)
        self.assertEqual(from_zip, from_folder)
        self.assertEqual(zipped_posts, self.posts())

    def test_dates_are_read_in_both_formats_x_writes(self):
        self.assertEqual(x_export.when("Fri Mar 15 09:41:22 +0000 2024"), ("2024-03-15", "09:41"))
        self.assertEqual(x_export.when("Tue Mar 5 08:15:03 +0000 2024"), ("2024-03-05", "08:15"))
        self.assertEqual(x_export.when("2015-03-02T10:00:00.000Z"), ("2015-03-02", "10:00"))
        self.assertEqual(x_export.when("Fri Zzz 15 09:41:22 +0000 2024"), (None, None))
        self.assertEqual(x_export.when(""), (None, None))
        self.assertEqual(x_export.when(None), (None, None))

    def test_a_post_with_an_unreadable_date_is_kept_and_counted(self):
        folder = self.archive({"tweets.js": js("tweets", [tweet("1", created="sometime last spring")])})
        r = x_export.run(folder, self.brain)
        self.assertEqual((r["posts"], r["undated"]), (1, 1))
        self.assertIn("date: null", self.posts())

    def test_a_damaged_part_is_reported_and_the_rest_still_imports(self):
        folder = self.archive({"tweets.js": js("tweets", [tweet("1")]),
                               "tweets-part1.js": "window.YTD.tweets.part1 = [ {broken"})
        r = x_export.run(folder, self.brain)
        self.assertEqual(r["posts"], 1)
        self.assertEqual([s["file"] for s in r["skipped"]], ["tweets-part1.js"])
        self.assertIn("damaged", r["skipped"][0]["reason"])

    def test_a_file_that_is_not_from_an_archive_is_reported_not_fatal(self):
        folder = self.archive({"tweets.js": "[{\"tweet\": {}}]"})
        r = x_export.run(folder, self.brain)
        self.assertEqual(r["posts"], 0)
        self.assertIn("window.YTD", r["skipped"][0]["reason"])

    def test_something_that_is_not_an_x_archive_is_refused_in_plain_words(self):
        folder = Path(self.tmp.name) / "holiday-photos"
        (folder / "data").mkdir(parents=True)
        (folder / "data" / "notes.txt").write_text("nothing to do with X")
        with self.assertRaises(ValueError) as caught:
            x_export.run(folder, self.brain)
        self.assertIn("does not look like an X archive", str(caught.exception))
        self.assertFalse((self.brain / "memory/conversations/x-posts.yaml").exists())

    def test_posts_work_without_the_account_file(self):
        """An archive can arrive without account.js. Posts are still the person's writing; there is
        just no handle to build a link from, so no link is invented."""
        folder = self.archive({"tweets.js": js("tweets", [tweet("1")])})
        r = x_export.run(folder, self.brain)
        self.assertEqual((r["posts"], r["handle"]), (1, ""))
        self.assertIn('link: ""', self.posts())
        self.assertIn("# My X profile", self.profile())

    def test_like_and_repost_counts_arrive_as_text_and_become_numbers(self):
        folder = self.archive({"tweets.js": js("tweets", [
            tweet("1", favorite_count="7", retweet_count="2"),
            tweet("2", favorite_count="not a number")])})
        x_export.run(folder, self.brain)
        self.assertIn("likes: 7", self.posts())
        self.assertIn("likes: 0", self.posts())

    def test_it_writes_only_the_posts_file_and_the_profile_page(self):
        before = {p for p in self.brain.rglob("*") if p.is_file()}
        x_export.run(SAMPLE_X, self.brain)
        after = {p for p in self.brain.rglob("*") if p.is_file()}
        self.assertEqual({p.relative_to(self.brain).as_posix() for p in after - before},
                         {"memory/conversations/x-posts.yaml", "memory/profile/x-profile.md"})

    def test_it_refuses_a_folder_that_is_not_a_brain(self):
        with self.assertRaises(SystemExit):
            x_export.run(SAMPLE_X, Path(self.tmp.name) / "not-a-brain")


if __name__ == "__main__":
    unittest.main()
