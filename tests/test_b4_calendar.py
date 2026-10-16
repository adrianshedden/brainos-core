import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

import nonet

nonet.install()
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "importers"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import calendar_ics  # noqa: E402
from create_brain import create_brain  # noqa: E402


def ev(uid, start, extra="", who=(), summary="Meeting", allday=False):
    dt = f"DTSTART;VALUE=DATE:{start}" if allday else f"DTSTART:{start}T100000Z"
    lines = ["BEGIN:VEVENT", f"UID:{uid}", f"SUMMARY:{summary}", dt, extra]
    lines += [f"ATTENDEE;CN={n}:mailto:{e}" for n, e in who]
    lines.append("ORGANIZER;CN=Me Owner:mailto:me@example.com")
    lines.append("END:VEVENT")
    return "\n".join(l for l in lines if l)


def cal(*events):
    return "BEGIN:VCALENDAR\nVERSION:2.0\n" + "\n".join(events) + "\nEND:VCALENDAR\n"


A, B, C = ("Ann A", "ann@example.com"), ("Bob B", "bob@example.com"), ("Cy C", "cy@example.com")


class Calendar(unittest.TestCase):
    def test_recurrence_counted_per_occurrence(self):
        a = calendar_ics.analyse(cal(ev("w", "20240101", "RRULE:FREQ=WEEKLY;COUNT=5", [A])))
        self.assertEqual(len(a["occurrences"]), 5)
        self.assertEqual(a["top"], [{"name": "Ann A", "email": "ann@example.com", "meetings": 5}])

    def test_exdate_until_and_byday(self):
        a = calendar_ics.analyse(cal(
            ev("x", "20240101", "RRULE:FREQ=DAILY;COUNT=4\nEXDATE:20240102T100000Z", [A]),
            ev("y", "20240101", "RRULE:FREQ=WEEKLY;BYDAY=MO,WE;UNTIL=20240110T235959Z", [B])))
        by = {p["email"]: p["meetings"] for p in a["top"]}
        self.assertEqual(by, {"ann@example.com": 3, "bob@example.com": 4})  # Mon 1, Wed 3, Mon 8, Wed 10

    def test_cancelled_and_cancelled_occurrence_skipped(self):
        cancelled = ev("c", "20240105", "STATUS:CANCELLED", [C])
        series = ev("s", "20240101", "RRULE:FREQ=WEEKLY;COUNT=3", [A])
        one_off = ("BEGIN:VEVENT\nUID:s\nSTATUS:CANCELLED\nRECURRENCE-ID:20240108T100000Z\n"
                   "DTSTART:20240108T100000Z\nEND:VEVENT")
        a = calendar_ics.analyse(cal(cancelled, series, one_off))
        self.assertEqual(len(a["occurrences"]), 2)
        self.assertNotIn("cy@example.com", [p["email"] for p in a["top"]])
        self.assertEqual(a["cancelled"], 2)

    def test_all_day_and_ranking_top_ten_with_owner_removed(self):
        people = [(f"P{i:02d}", f"p{i:02d}@example.com") for i in range(12)]
        events = []
        for i, p in enumerate(people):  # person i is in 12-i meetings
            for k in range(12 - i):
                events.append(ev(f"e{i}-{k}", f"2024{1 + k:02d}{10 + i:02d}", who=[p], allday=(k == 0)))
        a = calendar_ics.analyse(cal(*events))
        self.assertEqual(a["me"], "me@example.com")
        self.assertEqual([p["email"] for p in a["top"]], [p[1] for p in people[:10]])
        self.assertEqual([p["meetings"] for p in a["top"]], list(range(12, 2, -1)))
        self.assertNotIn("me@example.com", [p["email"] for p in a["top"]])
        self.assertTrue(any(o["all_day"] for o in a["occurrences"]))

    def test_run_writes_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            brain = create_brain(Path(tmp) / "b")
            f = Path(tmp) / "c.ics"
            f.write_text(cal(ev("w", "20240101", "RRULE:FREQ=WEEKLY;COUNT=2", [A])))
            r = calendar_ics.run(f, brain, me="me@example.com")
            self.assertEqual(r["occurrences"], 2)
            people = (brain / "network/people.jsonl").read_text()
            self.assertIn("ann@example.com", people)
            self.assertNotIn("me@example.com", people)
            meetings = (brain / "network/interactions.jsonl").read_text()
            self.assertEqual(meetings.count('"type": "meeting"'), 2)  # one line per occurrence with someone

    def test_robots_rooms_and_every_owner_address_are_not_people(self):
        robots = [("Luma", "calendar-invite@lu.ma"), ("", "noreply@example.com"), ("", "Do-Not-Reply@example.com"),
                  ("Room 1", "c_123@resource.calendar.google.com"), ("Team", "abc@group.calendar.google.com"),
                  ("", "x@calendar.luma-mail.com"), ("", "notifications@example.com")]
        mine = ("Me Too", "me.personal@example.org")
        events = [ev(f"r{i}", f"202401{10 + i:02d}", who=[A, mine, *robots]) for i in range(3)]
        events.append(ev("b", "20240120", who=[B]))
        with tempfile.TemporaryDirectory() as tmp:
            brain = create_brain(Path(tmp) / "b")
            f = Path(tmp) / "c.ics"
            f.write_text(cal(*events))
            r = calendar_ics.run(f, brain, me=["me@example.com", "ME.Personal@example.org"])
            self.assertEqual([p["email"] for p in r["top"]], ["ann@example.com", "bob@example.com"])
            self.assertEqual(r["occurrences"], 4)  # the meetings themselves are all kept
            events_yaml = (brain / "memory/calendar/events.yaml").read_text()
            for gone in ("lu.ma", "noreply", "resource.calendar", "group.calendar", "luma-mail", "Me Too", "Room 1"):
                self.assertNotIn(gone, events_yaml)
            self.assertIn("Ann A", events_yaml)

    def test_me_can_be_given_more_than_once_on_the_command_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            brain = create_brain(Path(tmp) / "b")
            f = Path(tmp) / "c.ics"
            f.write_text(cal(ev("w", "20240101", who=[A, ("Me Too", "me2@example.org")])))
            subprocess.run([sys.executable, str(Path(calendar_ics.__file__)), str(f), str(brain),
                            "--me", "me@example.com", "--me", "me2@example.org"], check=True, capture_output=True)
            top = (brain / "network/people.jsonl").read_text()
            self.assertIn("ann@example.com", top)
            self.assertNotIn("me2@example.org", top)
            r = subprocess.run([sys.executable, str(Path(calendar_ics.__file__)), str(f), str(brain), "--me"],
                               capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("one --me per address", r.stderr)


class CalendarContainers(unittest.TestCase):
    """Google Calendar exports a .zip with one .ics per calendar; a folder of .ics files works too.
    A file holding no calendar is refused by name and the brain is left as it was."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.brain = self.root / "brain"
        create_brain(self.brain)

    def tearDown(self):
        self.tmp.cleanup()

    def test_google_zip_of_two_calendars(self):
        import zipfile
        z = self.root / "alex@gmail.com.ical.zip"
        with zipfile.ZipFile(z, "w") as zf:
            zf.writestr("alex@gmail.com.ics", cal(ev("g1", "20240101", "RRULE:FREQ=WEEKLY;COUNT=3", [A])))
            zf.writestr("Work_abc@group.calendar.google.com.ics", cal(ev("g2", "20240102", who=[B])))
            zf.writestr("__MACOSX/._alex@gmail.com.ics", "junk")
        r = calendar_ics.run(z, self.brain)
        self.assertEqual(r["occurrences"], 4)
        self.assertTrue((self.brain / "memory/calendar/events.yaml").read_text().count("date:") == 4)

    def test_folder_of_ics(self):
        d = self.root / "cals"
        d.mkdir()
        (d / "one.ics").write_text(cal(ev("f1", "20240101", who=[A])))
        (d / "two.ics").write_text(cal(ev("f2", "20240103", who=[C])))
        self.assertEqual(calendar_ics.run(d, self.brain)["occurrences"], 2)

    def test_not_a_calendar_is_refused_and_brain_unchanged(self):
        before = (self.brain / "memory/calendar/events.yaml").read_bytes() if (self.brain / "memory/calendar/events.yaml").exists() else None
        pdf = self.root / "notes.pdf"
        pdf.write_bytes(b"%PDF-1.4 not a calendar")
        with self.assertRaises(SystemExit) as cm:
            calendar_ics.run(pdf, self.brain)
        self.assertIn("holds no calendar", str(cm.exception))
        after = (self.brain / "memory/calendar/events.yaml").read_bytes() if (self.brain / "memory/calendar/events.yaml").exists() else None
        self.assertEqual(before, after)

    def test_zip_with_no_calendar_is_refused(self):
        import zipfile
        z = self.root / "photos.zip"
        with zipfile.ZipFile(z, "w") as zf:
            zf.writestr("a.txt", "hello")
        with self.assertRaises(SystemExit):
            calendar_ics.run(z, self.brain)


@contextmanager
def patched(obj, name, value):
    """Swap obj.name for value inside the block. (unittest.mock imports ssl, which the no-network guard breaks.)"""
    old = getattr(obj, name)
    setattr(obj, name, value)
    try:
        yield
    finally:
        setattr(obj, name, old)


def tev(uid, start, extra="", summary="Meeting"):
    """An event whose DTSTART line is given whole after "DTSTART", e.g. ':20260827T123000Z'."""
    return "\n".join(l for l in ["BEGIN:VEVENT", f"UID:{uid}", f"SUMMARY:{summary}", f"DTSTART{start}", extra,
                                  "ATTENDEE;CN=Ann A:mailto:ann@example.com", "END:VEVENT"] if l)


def zcal(*events, zone=None):
    head = "BEGIN:VCALENDAR\nVERSION:2.0\n" + (f"X-WR-TIMEZONE:{zone}\n" if zone else "")
    return head + "\n".join(events) + "\nEND:VCALENDAR\n"


def when(a, title=None):
    """[(date, time)] of the occurrences, optionally only those with <title>."""
    return [(o["date"].isoformat(), o["time"]) for o in a["occurrences"] if title is None or o["title"] == title]


@unittest.skipUnless(calendar_ics.have_zone_data(), "this Python has no time-zone data")
class CalendarTimeZones(unittest.TestCase):
    """Every timed meeting is shown in one zone: --tz, else the calendar's X-WR-TIMEZONE, else the computer's."""

    def test_utc_to_london_summer_and_winter(self):
        a = calendar_ics.analyse(zcal(tev("s", ":20260827T123000Z", summary="Summer"),
                                      tev("w", ":20261210T123000Z", summary="Winter"), zone="Europe/London"))
        self.assertEqual(when(a, "Summer"), [("2026-08-27", "13:30")])  # BST, UTC+1
        self.assertEqual(when(a, "Winter"), [("2026-12-10", "12:30")])  # GMT, UTC+0

    def test_tzid_in_display_zone_kept_and_other_tzid_converted(self):
        a = calendar_ics.analyse(zcal(tev("l", ";TZID=Europe/London:20260915T120000", summary="London"),
                                      tev("n", ";TZID=America/New_York:20260915T090000", summary="NY"),
                                      zone="Europe/London"))
        self.assertEqual(when(a, "London"), [("2026-09-15", "12:00")])
        self.assertEqual(when(a, "NY"), [("2026-09-15", "14:00")])

    def test_floating_time_kept_while_utc_moves(self):
        a = calendar_ics.analyse(zcal(tev("f", ":20260915T120000", summary="Floating"),
                                      tev("u", ":20260915T120000Z", summary="UTC"), zone="Europe/Madrid"))
        self.assertEqual(when(a, "Floating"), [("2026-09-15", "12:00")])
        self.assertEqual(when(a, "UTC"), [("2026-09-15", "14:00")])

    def test_all_day_untouched(self):
        a = calendar_ics.analyse(zcal(tev("d", ";VALUE=DATE:20261025", summary="Day"),
                                      tev("u", ":20261025T020000Z", summary="UTC"), zone="America/Los_Angeles"))
        self.assertEqual(when(a, "Day"), [("2026-10-25", None)])
        self.assertEqual([o["all_day"] for o in a["occurrences"] if o["title"] == "Day"], [True])
        self.assertEqual(when(a, "UTC"), [("2026-10-24", "19:00")])

    def test_x_wr_timezone_used_and_written_and_printed(self):
        text = zcal(tev("s", ":20260827T123000Z", summary="Second Brain Bootcamp - Speaker Sync"), zone="Europe/Madrid")
        a = calendar_ics.analyse(text)
        self.assertEqual(a["zone"], "Europe/Madrid")
        self.assertEqual(when(a), [("2026-08-27", "14:30")])
        with tempfile.TemporaryDirectory() as tmp:
            brain = create_brain(Path(tmp) / "b")
            f = Path(tmp) / "c.ics"
            f.write_text(text)
            r = subprocess.run([sys.executable, str(Path(calendar_ics.__file__)), str(f), str(brain)],
                               capture_output=True, text=True, check=True)
            self.assertIn("Times are in Europe/Madrid.", r.stdout)
            events = (brain / "memory/calendar/events.yaml").read_text()
            self.assertIn("# Times are in Europe/Madrid.", events.split("\n- ")[0])
            self.assertIn('time: "14:30"', events)

    def test_tz_option_overrides_calendar_zone(self):
        text = zcal(tev("s", ":20260827T123000Z"), zone="Europe/Madrid")
        a = calendar_ics.analyse(text, tz="Europe/London")
        self.assertEqual((a["zone"], when(a)), ("Europe/London", [("2026-08-27", "13:30")]))
        with tempfile.TemporaryDirectory() as tmp:
            brain = create_brain(Path(tmp) / "b")
            f = Path(tmp) / "c.ics"
            f.write_text(text)
            r = subprocess.run([sys.executable, str(Path(calendar_ics.__file__)), str(f), str(brain),
                                "--tz", "Europe/London"], capture_output=True, text=True, check=True)
            self.assertIn("Times are in Europe/London.", r.stdout)
            self.assertIn('time: "13:30"', (brain / "memory/calendar/events.yaml").read_text())
            before = (brain / "memory/calendar/events.yaml").read_text()
            bad = subprocess.run([sys.executable, str(Path(calendar_ics.__file__)), str(f), str(brain),
                                  "--tz", "Mars/Olympus"], capture_output=True, text=True)
            self.assertNotEqual(bad.returncode, 0)
            self.assertIn("not a time zone", bad.stderr)
            self.assertNotIn("Traceback", bad.stderr)
            self.assertEqual(before, (brain / "memory/calendar/events.yaml").read_text())

    def test_no_calendar_zone_uses_the_computers(self):
        with patched(calendar_ics, "_local_zone_name", lambda: "Asia/Tokyo"):
            a = calendar_ics.analyse(zcal(tev("s", ":20260827T000000Z")))
        self.assertEqual((a["zone"], when(a)), ("Asia/Tokyo", [("2026-08-27", "09:00")]))

    def test_recurring_across_25_oct_2026_dst_change(self):
        london = tev("l", ";TZID=Europe/London:20261020T090000", "RRULE:FREQ=WEEKLY;COUNT=2", summary="London")
        utc = tev("u", ":20261020T080000Z", "RRULE:FREQ=WEEKLY;COUNT=2", summary="UTC")
        a = calendar_ics.analyse(zcal(london, utc, zone="Europe/London"))
        self.assertEqual(when(a, "London"), [("2026-10-20", "09:00"), ("2026-10-27", "09:00")])  # wall time kept
        self.assertEqual(when(a, "UTC"), [("2026-10-20", "09:00"), ("2026-10-27", "08:00")])  # the UTC one moves
        # Each occurrence is converted on its own day: New York changes clock a week later (1 Nov).
        a = calendar_ics.analyse(zcal(london, zone="America/New_York"))
        self.assertEqual(when(a), [("2026-10-20", "04:00"), ("2026-10-27", "05:00")])

    def test_conversion_moves_the_date_across_midnight_and_exdate_still_matches(self):
        a = calendar_ics.analyse(zcal(tev("e", ":20261020T233000Z"), zone="Europe/Madrid"))
        self.assertEqual(when(a), [("2026-10-21", "01:30")])
        a = calendar_ics.analyse(zcal(tev("w", ":20261021T013000Z"), zone="America/New_York"))
        self.assertEqual(when(a), [("2026-10-20", "21:30")])
        series = tev("d", ":20261020T233000Z", "RRULE:FREQ=DAILY;COUNT=3\nEXDATE:20261021T233000Z")
        a = calendar_ics.analyse(zcal(series, zone="Europe/Madrid"))
        self.assertEqual(when(a), [("2026-10-21", "01:30"), ("2026-10-23", "01:30")])
        # EXDATE and RECURRENCE-ID written in UTC for a London series still hit the right London day.
        series = tev("x", ";TZID=Europe/London:20261015T003000", "RRULE:FREQ=DAILY;COUNT=3\nEXDATE:20261015T233000Z")
        moved = ("BEGIN:VEVENT\nUID:x\nSUMMARY:Moved\nRECURRENCE-ID:20261016T233000Z\n"
                 "DTSTART;TZID=Europe/London:20261017T100000\nEND:VEVENT")
        a = calendar_ics.analyse(zcal(series, moved, zone="Europe/London"))
        self.assertEqual(when(a), [("2026-10-15", "00:30"), ("2026-10-17", "10:00")])

    def test_windows_zone_names_mapped_and_unknown_kept_with_warning(self):
        cases = [("GMT Standard Time", "12:00", "13:00"), ("Romance Standard Time", "12:00", "12:00"),
                 ("W. Europe Standard Time", "12:00", "12:00"), ("Central European Standard Time", "12:00", "12:00"),
                 ("Eastern Standard Time", "09:00", "15:00"), ("Pacific Standard Time", "09:00", "18:00")]
        events = [tev(f"w{i}", f';TZID="{name}":20260827T{t[:2]}{t[3:]}00', summary=name)
                  for i, (name, t, _) in enumerate(cases)]
        events.append(tev("u", ";TZID=Mars Standard Time:20260827T120000", summary="Mars"))
        a = calendar_ics.analyse(zcal(*events, zone="Europe/Madrid"))
        for name, _, shown in cases:
            self.assertEqual(when(a, name), [("2026-08-27", shown)], name)
        self.assertEqual(when(a, "Mars"), [("2026-08-27", "12:00")])
        self.assertTrue(any("Mars Standard Time" in w and "Europe/Madrid" in w for w in a["warnings"]), a["warnings"])


class CalendarNoZoneData(unittest.TestCase):
    """Some Windows Pythons have no zone data: times are then kept as written, with a clear note. Never crash."""

    TEXT = zcal(tev("s", ":20260827T123000Z", summary="UTC"), tev("l", ";TZID=Europe/London:20261020T090000",
                "RRULE:FREQ=WEEKLY;COUNT=2", summary="London"), zone="Europe/Madrid")

    def check(self, a):
        self.assertIsNone(a["zone"])
        self.assertIn("not converted", a["zone_note"])
        self.assertEqual(when(a, "UTC"), [("2026-08-27", "12:30")])
        self.assertEqual(when(a, "London"), [("2026-10-20", "09:00"), ("2026-10-27", "09:00")])

    def test_no_zoneinfo_module(self):
        with patched(calendar_ics, "zoneinfo", None):
            self.check(calendar_ics.analyse(self.TEXT, tz="Europe/London"))

    def test_zoneinfo_without_data(self):
        import zoneinfo

        def missing(key):
            raise zoneinfo.ZoneInfoNotFoundError(f"No time zone found with key {key}")
        with patched(zoneinfo, "ZoneInfo", missing):
            self.check(calendar_ics.analyse(self.TEXT))
            with tempfile.TemporaryDirectory() as tmp:
                brain = create_brain(Path(tmp) / "b")
                f = Path(tmp) / "c.ics"
                f.write_text(self.TEXT)
                r = calendar_ics.run(f, brain, tz="Europe/London")
                self.assertIn("not converted", r["zone_note"])
                self.assertIn("not converted", (brain / "memory/calendar/events.yaml").read_text().split("\n- ")[0])

    def test_command_line_without_zoneinfo_prints_the_note(self):
        with tempfile.TemporaryDirectory() as tmp:
            brain = create_brain(Path(tmp) / "b")
            f = Path(tmp) / "c.ics"
            f.write_text(self.TEXT)
            code = ("import runpy, sys; sys.modules['zoneinfo'] = None; sys.argv = sys.argv[1:]; "
                    "runpy.run_path(sys.argv[0], run_name='__main__')")
            r = subprocess.run([sys.executable, "-c", code, str(Path(calendar_ics.__file__)), str(f), str(brain),
                                "--tz", "Europe/London"], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("not converted", r.stdout)
            self.assertIn('time: "12:30"', (brain / "memory/calendar/events.yaml").read_text())


if __name__ == "__main__":
    unittest.main()
