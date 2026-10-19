"""Every place that says how many skills ship with the brain says the right number.

Found 16 Oct 2026: README and INSTRUCTIONS said "seven starter skills" while the brain ships eight skill
folders (its own SKILLS.md correctly said eight). The number is now checked against the folders."""
import re
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
WORDS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve".split())}
COUNT = re.compile(r"\b(\d+|" + "|".join(WORDS) + r") (?:starter |first |week-one )?skills\b", re.IGNORECASE)
# Places a person or an AI reads the count. sample/brain is a build of the template, so it is checked too.
FILES = ["README.md", "INSTRUCTIONS.md", "template/skills/SKILLS.md", "template/AGENTS.md", "template/LEVEL1.md",
         "template/README.md", "sample/brain/skills/SKILLS.md", "sample/brain/README.md"]


def shipped():
    return sorted(p.name for p in (KIT / "template" / "skills").iterdir() if (p / "SKILL.md").is_file())


class SkillCount(unittest.TestCase):
    def test_every_stated_count_matches_the_skill_folders(self):
        n = len(shipped())
        self.assertGreater(n, 0)
        stated = []
        for rel in FILES:
            f = KIT / rel
            if not f.is_file():
                continue
            for m in COUNT.finditer(f.read_text(encoding="utf-8")):
                word = m.group(1).lower()
                stated.append((rel, m.group(0), int(word) if word.isdigit() else WORDS[word]))
        self.assertTrue(stated, "no skill count found: the guard would pass by accident")
        wrong = [(rel, said) for rel, said, k in stated if k != n]
        self.assertEqual(wrong, [], f"{n} skills ship: {', '.join(shipped())}")


if __name__ == "__main__":
    unittest.main()
