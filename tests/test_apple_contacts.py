"""The Apple Contacts drop: a .vcf export from a Mac's Contacts app puts one entry per person in
the brain's people list (network/people.jsonl). Checked against the made-up export the sample brain is built from, plus the vCard
shapes a real address book writes: folded lines, grouped properties, 2.1 quoted-printable, photos."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

import nonet

nonet.install()
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "importers"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import apple_contacts  # noqa: E402
from create_brain import create_brain  # noqa: E402

CORE = Path(__file__).resolve().parents[1]
SAMPLE_VCF = CORE / "sample" / "exports" / "apple" / "contacts.vcf"


def card(*lines):
    return "\n".join(["BEGIN:VCARD", "VERSION:3.0", *lines, "END:VCARD"]) + "\n"


class AppleContacts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.brain = create_brain(Path(self.tmp.name) / "brain")

    def people(self, text, name="contacts.vcf"):
        path = Path(self.tmp.name) / name
        path.write_text(text, encoding="utf-8")
        result = apple_contacts.run(path, self.brain)
        return result, apple_contacts.parse_cards(text)

    def path(self):
        return self.brain / "network/people.jsonl"

    def records(self):
        """Each person the contacts import gave the brain: the merged line, plus what Contacts said."""
        rows = [json.loads(line) for line in self.path().read_text(encoding="utf-8").splitlines()]
        return [dict(r["from"]["apple-contacts"], emails=r["emails"], phones=r["phones"], line=r) for r in rows]

    def one(self):
        recs = self.records()
        self.assertEqual(len(recs), 1)
        return recs[0]

    def test_the_sample_export_reads_every_card_that_has_a_name(self):
        r = apple_contacts.run(SAMPLE_VCF, self.brain)
        self.assertEqual((r["people"], r["with_email"], r["with_phone"], r["nameless"]), (5, 3, 4, 1))
        self.assertEqual(r["skipped"], [])
        # Filed by name, so the file reads the same way twice; every line says where it came from.
        self.assertEqual([r["name"] for r in self.records()],
                         ["Dani Dummy", "Jo Placeholder", "Priya Demo", "Sam Sample", "Tomás Testerman"])
        for r in self.records():
            self.assertEqual((r["line"]["source"], r["line"]["confidence"]), (["apple-contacts"], "high"))

    def test_a_folded_line_is_one_value(self):
        """Contacts wraps a long note at 75 characters, wherever that falls, by starting the next
        line with a space. Read line by line the second half would be lost; the fold's own space is
        not part of the text, so putting one back would corrupt a word split across the break."""
        r, _ = self.people(card("FN:Long Note", "NOTE:the first half and the second ha", " lf"))
        self.assertEqual(r["people"], 1)
        self.assertEqual(self.one()["note"], "the first half and the second half")

    def test_grouped_properties_and_preferred_values_come_first(self):
        r, _ = self.people(card("FN:Group Person", "item1.EMAIL;type=INTERNET:second@example.com",
                                "item1.X-ABLabel:_$!<Work>!$_",
                                "item2.EMAIL;type=INTERNET;type=pref:first@example.com",
                                "TEL;type=HOME:+44 117 496 0003",
                                "TEL;type=CELL;type=pref:+44 7700 900444"))
        self.assertEqual(r["people"], 1)
        r = self.one()
        self.assertEqual(r["emails"], ["first@example.com", "second@example.com"])  # the preferred one first
        self.assertEqual(r["phones"][0], "+44 7700 900444")

    def test_vcard_4_marks_the_preferred_value_with_pref_1(self):
        r, _ = self.people("BEGIN:VCARD\nVERSION:4.0\nFN:Four Oh\n"
                           "EMAIL:later@example.com\nEMAIL;PREF=1:main@example.com\nEND:VCARD\n")
        self.assertEqual(r["people"], 1)
        self.assertEqual(self.one()["emails"][0], "main@example.com")

    def test_quoted_printable_note_keeps_its_accents_and_its_second_line(self):
        """vCard 2.1 wraps with a trailing '=' and no leading space, and writes one accented
        character as several =XX bytes. Decoding them one at a time turns café into mojibake."""
        r, _ = self.people("BEGIN:VCARD\nVERSION:2.1\nFN:Quoted Printable\n"
                           "NOTE;ENCODING=QUOTED-PRINTABLE;CHARSET=UTF-8:caf=C3=A9 rota. Pays =\n"
                           "by bank transfer.\nEND:VCARD\n")
        self.assertEqual(r["people"], 1)
        self.assertEqual(self.one()["note"], "café rota. Pays by bank transfer.")

    def test_bare_types_of_vcard_2_1_still_pick_the_preferred_number(self):
        r, _ = self.people("BEGIN:VCARD\nVERSION:2.1\nFN:Bare Types\n"
                           "TEL;WORK;VOICE:+44 117 496 0004\nTEL;CELL;VOICE;PREF:+44 7700 900555\nEND:VCARD\n")
        self.assertEqual(r["people"], 1)
        self.assertEqual(self.one()["phones"][0], "+44 7700 900555")

    def test_a_photo_never_reaches_the_brain(self):
        """A card's photo is megabytes of base64 and says nothing. Its folded continuation lines must
        not be read as values either."""
        r, _ = self.people(card("FN:Has Photo", "PHOTO;ENCODING=b;TYPE=JPEG:/9j/4AAQSkZJRgABAQEA",
                                " YABgAAD/2wBDAAgGBgoKDQ0=", "NOTE:after the photo"))
        self.assertEqual(r["people"], 1)
        self.assertNotIn("9j/4AAQ", self.path().read_text(encoding="utf-8"))
        self.assertEqual(self.one()["note"], "after the photo")

    def test_escapes_become_the_characters_they_stand_for(self):
        r, _ = self.people(card("FN:Escaped", "TITLE:Buyer\\, North", "NOTE:one\\ntwo"))
        self.assertEqual(r["people"], 1)
        r = self.one()
        self.assertEqual(r["position"], "Buyer, North")
        self.assertEqual(r["note"], "one\ntwo")  # a real line break

    def test_a_card_with_only_a_structured_name_is_still_filed(self):
        r, _ = self.people(card("N:Lastly;Firstly;Middle;Dr;"))
        self.assertEqual(r["people"], 1)
        self.assertEqual(self.one()["name"], "Dr Firstly Middle Lastly")

    def test_a_card_with_no_name_is_counted_and_left_out(self):
        r, _ = self.people(card("TEL:+44 7700 900666") + card("FN:Named Person"))
        self.assertEqual((r["people"], r["nameless"]), (1, 1))
        self.assertNotIn("900666", self.path().read_text(encoding="utf-8"))

    def test_windows_line_endings_and_a_byte_order_mark(self):
        path = Path(self.tmp.name) / "crlf.vcf"
        path.write_bytes("﻿".encode() + card("FN:Crlf Person", "EMAIL:crlf@example.com")
                         .replace("\n", "\r\n").encode())
        r = apple_contacts.run(path, self.brain)
        self.assertEqual(r["people"], 1)
        self.assertEqual(self.one()["name"], "Crlf Person")

    def test_a_folder_of_exports_is_read_once_per_person(self):
        folder = Path(self.tmp.name) / "exports"
        folder.mkdir()
        (folder / "a.vcf").write_text(card("FN:Twice Over", "EMAIL:twice@example.com"))
        (folder / "b.vcf").write_text(card("FN:Twice Over", "EMAIL:twice@example.com")
                                      + card("FN:Only In B"))
        r = apple_contacts.run(folder, self.brain)
        self.assertEqual(r["people"], 2)
        self.assertEqual([r["name"] for r in self.records()].count("Twice Over"), 1)

    def test_a_file_that_is_not_a_vcard_is_reported_not_fatal(self):
        r, _ = self.people("this is not a vCard at all\n", name="notes.vcf")
        self.assertEqual(r["people"], 0)
        self.assertEqual(r["skipped"], [{"file": "notes.vcf", "reason": "no vCard found in it"}])
        self.assertEqual(self.path().read_text(encoding="utf-8"), "")  # the list is still written, and is empty

    def test_it_writes_nowhere_but_the_people_list(self):
        before = {p for p in self.brain.rglob("*") if p.is_file()}
        apple_contacts.run(SAMPLE_VCF, self.brain)
        after = {p for p in self.brain.rglob("*") if p.is_file()}
        self.assertEqual({str(p.relative_to(self.brain)) for p in after - before},
                         {"network/people.jsonl"})

    def test_it_refuses_a_folder_that_is_not_a_brain(self):
        with self.assertRaises(SystemExit):
            apple_contacts.run(SAMPLE_VCF, Path(self.tmp.name) / "not-a-brain")


if __name__ == "__main__":
    unittest.main()
