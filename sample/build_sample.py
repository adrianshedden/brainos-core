#!/usr/bin/env python3
"""Regenerate the sample brain: python3 sample/build_sample.py [output-folder]

The sample is built ONLY by creating an empty brain and running every importer on the made-up
exports in sample/exports/. If an importer breaks, this breaks."""
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
CORE = HERE.parent
EXPORTS = HERE / "exports"


def run(*args):
    subprocess.run([sys.executable, *map(str, args)], check=True, stdout=subprocess.DEVNULL)


def build(dest):
    dest = Path(dest)
    if dest.exists():
        shutil.rmtree(dest)
    run(CORE / "create_brain.py", dest, "--domains", "network,work")
    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / "linkedin.zip"
        with zipfile.ZipFile(archive, "w") as zf:
            for f in sorted((EXPORTS / "linkedin").glob("*.csv")):
                zf.write(f, f.name)
        run(CORE / "importers" / "linkedin.py", archive, dest)
    run(CORE / "importers" / "whatsapp.py", EXPORTS / "whatsapp", dest, "--me", "Alex Example")
    run(CORE / "importers" / "calendar_ics.py", EXPORTS / "calendar" / "calendar.ics", dest, "--me", "alex@example.com")
    run(CORE / "importers" / "apple_contacts.py", EXPORTS / "apple" / "contacts.vcf", dest)
    run(CORE / "importers" / "x_export.py", EXPORTS / "x", dest)
    return dest


if __name__ == "__main__":
    out = build(sys.argv[1] if len(sys.argv) > 1 else HERE / "brain")
    print(f"Sample brain built in {out}")
