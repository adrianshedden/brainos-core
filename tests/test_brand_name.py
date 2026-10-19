"""The product is written "BrainOS": one word, never with a space, hyphen or underscore between "Brain" and "OS",
in any mix of capitals (decided 16 Oct 2026).

Checks every file name and every text file in this kit. The only spelling allowed with a gap is the
all-lower-case identifier `brain-os` (an email stand-in, a folder name, a price key), which is code,
not the product's name."""
import re
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
WRONG = re.compile(r"\bbrain[ \-_]+o\s?s\b", re.IGNORECASE)
ALLOWED = {"brain-os"}


def wrong_spellings(root, skip=lambda rel: False):
    found = []
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root).as_posix()
        if ".git/" in f"{rel}/" or "__pycache__" in rel or skip(rel):
            continue
        for m in WRONG.finditer(rel):
            if m.group(0) not in ALLOWED:
                found.append(f"{rel} (file name): {m.group(0)}")
        if not p.is_file():
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for n, line in enumerate(text.splitlines(), 1):
            for m in WRONG.finditer(line):
                if m.group(0) not in ALLOWED:
                    found.append(f"{rel}:{n}: {m.group(0)}")
    return found


class BrandName(unittest.TestCase):
    def test_the_guard_catches_every_wrong_spelling(self):
        for bad in ("Brain" + gap + os for gap in (" ", "-", "_", "  ") for os in ("OS", "Os", "os")):
            self.assertTrue(WRONG.search(bad) and WRONG.search(bad).group(0) not in ALLOWED, bad)
        for good in ("BrainOS", "brain-os@localhost", "~/.brain-os/", "my brain, os"):
            hit = WRONG.search(good)
            self.assertTrue(hit is None or hit.group(0) in ALLOWED, good)

    def test_no_file_in_the_kit_spells_it_with_a_gap(self):
        self.assertEqual(wrong_spellings(KIT), [])

    def test_readme_names_the_product_the_brand_and_the_company(self):
        # Decided 16 Oct 2026 (final): AI Ops is the company, Remyn the brand, BrainOS the product.
        readme = (KIT / "README.md").read_text(encoding="utf-8")
        self.assertIn("BrainOS is the product, Remyn is the brand, and AI Ops is the company", readme)
        for wrong in ("the product is Remyn", "Remyn is the product", "AI Ops is the brand", "BrainOS is the brand"):
            self.assertNotIn(wrong, readme)


class NoWordKit(unittest.TestCase):
    """Rian, locked (dec_20261019_2300_no_word_kit): never "the kit" in anything a person reads. Say BrainOS.
    Folder and file names such as kit/ stay as they are."""

    KIT_WORDS = re.compile(r"\b(the|this|a|newest|older|old|new) kit\b|\bkit's\b|BrainOS kit", re.IGNORECASE)

    def test_people_never_read_the_word_kit(self):
        for name in ("README.md", "WHATSAPP-LIVE.md", "template/README.md"):
            text = (KIT / name).read_text(encoding="utf-8")
            self.assertIsNone(self.KIT_WORDS.search(text), f"{name}: {self.KIT_WORDS.search(text)}")
        for name in ("start.sh", "start.ps1"):
            for n, line in enumerate((KIT / name).read_text(encoding="utf-8").splitlines(), 1):
                if not line.lstrip().startswith("#"):
                    self.assertIsNone(self.KIT_WORDS.search(line), f"{name}:{n}: {line.strip()}")
        setup = (KIT / "SETUP.md").read_text(encoding="utf-8")
        self.assertIn('Never say "the kit" to the person: say BrainOS', setup)
        for quoted in re.findall(r'"[^"\n]{12,}"', setup):
            if "Never say" not in quoted:
                self.assertIsNone(self.KIT_WORDS.search(quoted), quoted)
        self.assertIn("Set up my brain with BrainOS from github.com/adrianshedden/brainos-core", setup)


if __name__ == "__main__":
    unittest.main()
