#!/usr/bin/env python3
"""Import a calendar file: python3 importers/calendar_ics.py <file.ics> <brain> [--me <your-email>]... [--tz <zone>]

<file.ics> is one .ics file, a .zip of them (Google Calendar's export), or a folder of them.
Give --me once for each of your own addresses (work, personal): none of them is listed as a contact.
Booking and invitation robots (noreply, calendar-invite and the like) and room or shared-calendar
addresses are left out of the people lists; the meetings themselves are all kept.

Expands recurring meetings (each occurrence counts once), skips cancelled ones, and ranks the ten
people you meet most. Recurrences with no end are counted for one year from their start. No network.

Meetings go to memory/calendar/events.yaml. Everyone you met joins the brain's one people list
(people.jsonl, with how many meetings), and each meeting with someone joins interactions.jsonl: both in
network/, or in memory/people/ when the brain has no network domain.

Every timed meeting is shown in ONE time zone: the calendar's own (X-WR-TIMEZONE, the first calendar's
when a zip holds several), else this computer's. --tz <zone> (e.g. Europe/London) chooses another. The
zone used is printed and written at the top of events.yaml. All-day events are never shifted. If this
computer's Python has no time-zone data, times are kept as written in the file, and a note says so."""
import calendar as _cal
import os
import re
import sys
import zipfile
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

try:
    import zoneinfo
except ImportError:  # Python older than 3.9
    zoneinfo = None

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import merge_people, replace_interactions, require_brain, slugify, write_yaml  # noqa: E402

DAYS = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]
OPEN_ENDED_DAYS = 365
MAX_OCCURRENCES = 5000
# Addresses that are robots, rooms or shared calendars, never people you met.
NOT_PEOPLE_LOCAL = {"calendar-invite", "invite", "noreply", "no-reply", "donotreply", "do-not-reply",
                    "notifications", "notification", "calendar", "mailer-daemon"}
NOT_PEOPLE_DOMAINS = ("resource.calendar.google.com", "group.calendar.google.com", "calendar.luma-mail.com")


def is_person(email):
    local, _, domain = email.lower().partition("@")
    return local not in NOT_PEOPLE_LOCAL and not any(
        domain == d or domain.endswith("." + d) for d in NOT_PEOPLE_DOMAINS)


def _split_unquoted(s, sep, maxsplit=-1):
    parts, cur, q = [], "", False
    for ch in s:
        if ch == '"':
            q = not q
        if ch == sep and not q and (maxsplit < 0 or len(parts) < maxsplit):
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    return parts + [cur]


def parse_ics(text):
    """Return a list of VEVENT dicts: {prop_name: [(params, value), ...]}."""
    lines = []
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if line[:1] in (" ", "\t") and lines:
            lines[-1] += line[1:]
        else:
            lines.append(line)
    events, cur = [], None
    for line in lines:
        if line.upper() == "BEGIN:VEVENT":
            cur = {}
        elif line.upper() == "END:VEVENT":
            if cur is not None:
                events.append(cur)
            cur = None
        elif cur is not None and ":" in line:
            head, value = _split_unquoted(line, ":", 1)
            bits = _split_unquoted(head, ";")
            params = {}
            for b in bits[1:]:
                if "=" in b:
                    k, v = b.split("=", 1)
                    params[k.upper()] = v.strip('"')
            value = value.replace("\\n", " ").replace("\\N", " ").replace("\\,", ",").replace("\\;", ";").replace("\\\\", "\\")
            cur.setdefault(bits[0].upper(), []).append((params, value))
    return events


def _first(ev, name):
    return ev[name][0] if name in ev else ({}, "")


# Windows (Outlook / Exchange) zone names for the common zones, mapped to the IANA names zoneinfo knows.
WINDOWS_ZONES = {
    "gmt standard time": "Europe/London", "greenwich standard time": "Atlantic/Reykjavik",
    "romance standard time": "Europe/Paris", "w. europe standard time": "Europe/Berlin",
    "central europe standard time": "Europe/Budapest", "central european standard time": "Europe/Warsaw",
    "e. europe standard time": "Europe/Chisinau", "fle standard time": "Europe/Helsinki",
    "gtb standard time": "Europe/Bucharest", "turkey standard time": "Europe/Istanbul",
    "russian standard time": "Europe/Moscow", "israel standard time": "Asia/Jerusalem",
    "egypt standard time": "Africa/Cairo", "south africa standard time": "Africa/Johannesburg",
    "w. central africa standard time": "Africa/Lagos", "morocco standard time": "Africa/Casablanca",
    "arabian standard time": "Asia/Dubai", "india standard time": "Asia/Kolkata",
    "singapore standard time": "Asia/Singapore", "china standard time": "Asia/Shanghai",
    "tokyo standard time": "Asia/Tokyo", "korea standard time": "Asia/Seoul",
    "w. australia standard time": "Australia/Perth", "aus eastern standard time": "Australia/Sydney",
    "new zealand standard time": "Pacific/Auckland", "eastern standard time": "America/New_York",
    "central standard time": "America/Chicago", "mountain standard time": "America/Denver",
    "us mountain standard time": "America/Phoenix", "pacific standard time": "America/Los_Angeles",
    "alaskan standard time": "America/Anchorage", "hawaiian standard time": "Pacific/Honolulu",
    "atlantic standard time": "America/Halifax", "canada central standard time": "America/Regina",
    "sa pacific standard time": "America/Bogota", "e. south america standard time": "America/Sao_Paulo",
    "argentina standard time": "America/Argentina/Buenos_Aires", "utc": "UTC",
    "coordinated universal time": "UTC",
}


def _zone(name):
    """The zoneinfo zone for an IANA or common Windows name, or None if unknown or there is no zone data."""
    name = (name or "").strip().strip('"')
    if zoneinfo is None or not name:
        return None
    tries = [WINDOWS_ZONES.get(name.lower()), name]
    m = re.search(r"([A-Za-z_]+/[A-Za-z_+-]+(?:/[A-Za-z_+-]+)?)$", name)  # e.g. /mozilla.org/.../Europe/London
    if m:
        tries.append(m.group(1))
    for key in tries:
        if not key:
            continue
        try:
            return zoneinfo.ZoneInfo(key)
        except (zoneinfo.ZoneInfoNotFoundError, ValueError, OSError):
            continue
    return None


def have_zone_data():
    return _zone("UTC") is not None


def _local_zone_name():
    """This computer's IANA zone name, or None when it cannot be told."""
    tz = os.environ.get("TZ", "").lstrip(":")
    if tz and _zone(tz):
        return tz
    try:
        target = os.path.realpath("/etc/localtime")
    except OSError:
        return None
    if "zoneinfo/" in target:
        return target.split("zoneinfo/", 1)[1]
    return None


class Display:
    """Turns a parsed start into (date, 'HH:MM' or None, all_day) in the one display zone.
    zone is a zoneinfo zone, or None for this computer's local time. When there is no zone data,
    convert is False and every time is kept as written (the old behaviour)."""

    def __init__(self, zone=None, name="", convert=True):
        self.zone, self.name, self.convert = zone, name, convert

    def frame(self, stamp, warnings):
        """The zone a start is written in: 'utc', a zoneinfo zone, or None (already local, keep)."""
        kind, tzid = stamp[1], stamp[2]
        if not self.convert or kind in ("date", "floating"):
            return None
        if kind == "utc":
            return "utc"
        z = _zone(tzid)
        if z is None:
            warnings.append(f"time zone {tzid!r} not recognised; its times are taken as already in {self.name}")
        return z

    def show(self, dt, frame):
        """dt is a wall time (naive) written in <frame>; return it in the display zone."""
        if frame is None:
            return dt
        aware = dt.replace(tzinfo=timezone.utc if frame == "utc" else frame)
        return (aware.astimezone(self.zone) if self.zone is not None else aware.astimezone()).replace(tzinfo=None)


def _parse_stamp(params, value):
    """Return (date or naive datetime as written, kind, tzid). kind: 'date' (all day), 'utc' (ends in Z),
    'tzid' (TZID= given) or 'floating' (neither: already local)."""
    v = value.strip()
    m = re.match(r"(\d{4})(\d{2})(\d{2})(?:T(\d{2})(\d{2})(\d{2})?)?(Z)?", v)
    if not m:
        return None
    try:
        d = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if params.get("VALUE", "").upper() == "DATE" or m.group(4) is None:
            return d, "date", None
        dt = datetime(d.year, d.month, d.day, int(m.group(4)), int(m.group(5)), int(m.group(6) or 0))
    except ValueError:
        return None
    if m.group(7):
        return dt, "utc", None
    if params.get("TZID"):
        return dt, "tzid", params["TZID"]
    return dt, "floating", None


def _parse_dt(params, value):
    """Return (date, 'HH:MM' or None, all_day) as written, with no zone change."""
    s = _parse_stamp(params, value)
    if not s:
        return None
    if s[1] == "date":
        return s[0], None, True
    return s[0].date(), s[0].strftime("%H:%M"), False


def _in_frame(stamp, frame, warnings, display):
    """The date of <stamp> (an EXDATE or RECURRENCE-ID) seen in <frame>, the zone its series is written in."""
    when, kind = stamp[0], stamp[1]
    if kind == "date" or frame is None:
        return when if kind == "date" else when.date()
    own = display.frame(stamp, warnings)
    if own is None:
        return when.date()
    aware = when.replace(tzinfo=timezone.utc if own == "utc" else own)
    return aware.astimezone(timezone.utc if frame == "utc" else frame).date()


def _add_months(d, n):
    y, mo = divmod(d.month - 1 + n, 12)
    return y + d.year, mo + 1


def expand(start, rrule, warnings):
    """Yield occurrence dates for an RRULE (dates only)."""
    rule = dict(p.split("=", 1) for p in rrule.split(";") if "=" in p)
    freq = rule.get("FREQ", "").upper()
    interval = max(int(rule.get("INTERVAL", "1") or 1), 1)
    count = int(rule["COUNT"]) if rule.get("COUNT") else None
    until = None
    if rule.get("UNTIL"):
        u = _parse_dt({}, rule["UNTIL"])
        until = u[0] if u else None
    limit = until or (start + timedelta(days=OPEN_ENDED_DAYS))
    if count is not None:
        limit = date.max
    byday = [b[-2:] for b in rule.get("BYDAY", "").split(",") if b]
    if freq == "MONTHLY" and byday:
        warnings.append("monthly BYDAY rule counted by day of month")

    def gen():
        if freq == "DAILY":
            d = start
            while True:
                yield d
                d += timedelta(days=interval)
        elif freq == "WEEKLY":
            wds = sorted(DAYS.index(b) for b in byday if b in DAYS) or [start.weekday()]
            week0 = start - timedelta(days=start.weekday())
            k = 0
            while True:
                for wd in wds:
                    d = week0 + timedelta(days=7 * k * interval + wd)
                    if d >= start:
                        yield d
                k += 1
        elif freq == "MONTHLY":
            k = 0
            while True:
                y, m = _add_months(start, k * interval)
                if start.day <= _cal.monthrange(y, m)[1]:
                    yield date(y, m, start.day)
                k += 1
        elif freq == "YEARLY":
            k = 0
            while True:
                y = start.year + k * interval
                if start.month != 2 or start.day != 29 or _cal.isleap(y):
                    yield date(y, start.month, start.day)
                k += 1
        else:
            warnings.append(f"unsupported repeat rule {freq or rrule!r}; counted once")
            yield start

    n = 0
    for d in gen():
        if d > limit or n >= MAX_OCCURRENCES or (count is not None and n >= count):
            return
        n += 1
        yield d
        if freq not in ("DAILY", "WEEKLY", "MONTHLY", "YEARLY"):
            return


def _people(ev):
    out = {}
    for name in ("ORGANIZER", "ATTENDEE"):
        for params, value in ev.get(name, []):
            email = re.sub(r"^mailto:", "", value.strip(), flags=re.I).lower()
            cn = params.get("CN", "")
            if email:
                out.setdefault(email, cn or out.get(email, ""))
    return out


def display_zone(text, tz=None):
    """Pick the one display zone: --tz, else the calendar's X-WR-TIMEZONE, else this computer's.
    Returns (Display, warnings). A --tz this computer does not know is refused before anything is written."""
    warnings = []
    if not have_zone_data():
        return Display(convert=False), warnings
    if tz:
        z = _zone(tz)
        if z is None:
            raise SystemExit(f"--tz {tz!r} is not a time zone this computer knows. Use a name like "
                             "Europe/London or America/New_York. Nothing was changed.")
        return Display(z, tz), warnings
    m = re.search(r"^X-WR-TIMEZONE[^:\n]*:(.+)$", text, re.M | re.I)
    if m:
        name = m.group(1).strip()
        z = _zone(name)
        if z is not None:
            return Display(z, name), warnings
        warnings.append(f"the calendar's time zone {name!r} is not recognised; used this computer's instead")
    name = _local_zone_name()
    z = _zone(name)
    if z is not None:
        return Display(z, name), warnings
    return Display(None, f"this computer's local time ({datetime.now().astimezone().tzname()})"), warnings


def analyse(text, me=None, tz=None):
    """<me> is the owner's address, or a list of them. If none is given, the owner is guessed: the one
    address in (nearly) every meeting. <tz> overrides the display zone (see display_zone)."""
    events = parse_ics(text)
    display, warnings = display_zone(text, tz)
    masters, overrides, cancelled = [], [], 0
    for ev in events:
        if _first(ev, "STATUS")[1].upper() == "CANCELLED":
            cancelled += 1
            # a cancelled single occurrence of a series must still hide that occurrence
            if "RECURRENCE-ID" not in ev:
                continue
        (overrides if "RECURRENCE-ID" in ev else masters).append(ev)
    frames = {}  # uid -> the zone its series is written in, so EXDATE / RECURRENCE-ID match in that zone
    for ev in masters:
        s = _parse_stamp(*_first(ev, "DTSTART"))
        if s:
            frames.setdefault(_first(ev, "UID")[1], display.frame(s, []))
    skip = set()  # (uid, date) occurrences replaced or removed by an override
    for ev in overrides:
        r = _parse_stamp(*_first(ev, "RECURRENCE-ID"))
        if r:
            uid = _first(ev, "UID")[1]
            skip.add((uid, _in_frame(r, frames.get(uid), warnings, display)))

    occurrences = []  # dict(date, time, title, all_day, recurring, people)

    def add(ev, d, wall, frame, recurring):
        """d: the occurrence's date as written; wall: its start time as written (None = all day)."""
        time = None
        if wall is not None:
            shown = display.show(datetime.combine(d, wall), frame)  # each occurrence on its own: DST moves
            d, time = shown.date(), shown.strftime("%H:%M")
        occurrences.append({"date": d, "time": time, "title": _first(ev, "SUMMARY")[1] or "(no title)",
                            "all_day": wall is None, "recurring": recurring, "people": _people(ev)})

    def start_of(ev):
        s = _parse_stamp(*_first(ev, "DTSTART"))
        if not s:
            return None
        if s[1] == "date":
            return s[0], None, None
        return s[0].date(), s[0].time(), display.frame(s, warnings)

    for ev in masters:
        s = start_of(ev)
        if not s:
            warnings.append("event without a readable start date skipped")
            continue
        start, wall, frame = s
        uid = _first(ev, "UID")[1]
        rrule = _first(ev, "RRULE")[1]
        if rrule:
            ex = set()
            for params, value in ev.get("EXDATE", []):
                for v in value.split(","):
                    p = _parse_stamp(params, v)
                    if p:
                        ex.add(_in_frame(p, frame, warnings, display))
            for d in expand(start, rrule, warnings):
                if d not in ex and (uid, d) not in skip:
                    add(ev, d, wall, frame, True)
        else:
            add(ev, start, wall, frame, False)
    for ev in overrides:
        if _first(ev, "STATUS")[1].upper() == "CANCELLED":
            continue
        s = start_of(ev)
        if s:
            add(ev, s[0], s[1], s[2], True)

    counts, names = Counter(), {}
    for o in occurrences:
        for email, cn in o["people"].items():
            if not is_person(email):
                continue
            counts[email] += 1
            names.setdefault(email, cn)
            if cn and not names[email]:
                names[email] = cn
    mine = [m.strip().lower() for m in ([me] if isinstance(me, str) else me or []) if m and m.strip()]
    if not mine and occurrences and counts:
        top, n = counts.most_common(1)[0]
        if n >= 0.9 * len(occurrences) and len(occurrences) >= 3:
            mine = [top]  # the calendar's owner is in (nearly) every meeting
    ranked = sorted(((e, c) for e, c in counts.items() if e not in mine), key=lambda x: (-x[1], (names[x[0]] or x[0]).lower(), x[0]))
    everyone = [{"name": names[e] or e, "email": e, "meetings": c} for e, c in ranked]
    top10 = everyone[:10]
    occurrences.sort(key=lambda o: (o["date"], o["time"] or "", o["title"]))
    return {"occurrences": occurrences, "cancelled": cancelled, "top": top10, "everyone": everyone, "warnings": sorted(set(warnings)),
            "me": mine[0] if mine else None, "mine": set(mine), "zone": display.name if display.convert else None,
            "zone_note": zone_note(display)}


def zone_note(display):
    if not display.convert:
        return ("Times are as written in the calendar file, not converted to one time zone: this computer's "
                "Python has no time-zone data (install it with: pip install tzdata).")
    return f"Times are in {display.name}."


def _decode(data):
    return data.decode("utf-8-sig", errors="replace")


def read_calendars(ics):
    """Return the calendar text from one .ics file, a .zip of .ics files (Google Calendar exports a zip
    with one .ics per calendar), or a folder of them. Several calendars are joined into one text.
    Refuses, by name, anything that holds no calendar, so a wrong file never reads as "0 meetings"."""
    ics = Path(ics)
    texts = []
    if ics.is_dir():
        texts = [_decode(p.read_bytes()) for p in sorted(ics.rglob("*.ics"))]
    elif zipfile.is_zipfile(ics):
        with zipfile.ZipFile(ics) as zf:
            for info in sorted(zf.infolist(), key=lambda i: i.filename):
                name = info.filename
                if not info.is_dir() and name.lower().endswith(".ics") and "__MACOSX/" not in name:
                    texts.append(_decode(zf.read(info)))
    else:
        texts = [_decode(ics.read_bytes())]
    texts = [t for t in texts if "BEGIN:VCALENDAR" in t.upper()]
    if not texts:
        raise SystemExit(f"{ics.name} holds no calendar. BrainOS reads a .ics calendar file, a .zip of them "
                         "(Google Calendar's export) or a folder of them. Nothing was changed.")
    return "\n".join(texts)


def run(ics, brain, me=None, tz=None):
    brain = require_brain(brain)
    text = read_calendars(ics)
    a = analyse(text, me, tz)
    occ = a["occurrences"]
    write_yaml(brain, "memory/calendar/events.yaml", [{
        "date": o["date"].isoformat(), "time": o["time"], "title": o["title"], "all_day": o["all_day"],
        "recurring": o["recurring"],
        "with": sorted((n or e) for e, n in o["people"].items() if e not in a["mine"] and is_person(e)),
        "source": "calendar",
    } for o in occ], "Calendar meetings, one entry per occurrence. Written by importers/calendar_ics.py; re-running replaces this file.\n# " + a["zone_note"])
    merge_people(brain, "calendar", [{"name": p["name"] if p["name"] != p["email"] else "", "emails": [p["email"]],
                                      "meetings": p["meetings"], **({"rank": i + 1} if i < 10 else {})}
                                     for i, p in enumerate(a["everyone"])])
    meetings, seen = [], set()
    for o in occ:
        others = sorted((n or e) for e, n in o["people"].items() if e not in a["mine"] and is_person(e))
        if not others:
            continue  # nobody else there: not an interaction with anyone
        base = f"meeting_{o['date'].isoformat()}_{(o['time'] or 'allday').replace(':', '')}_{slugify(o['title'], 'meeting')}"
        mid, n = base, 2
        while mid in seen:
            mid, n = f"{base}_{n}", n + 1
        seen.add(mid)
        meetings.append({"id": mid, "type": "meeting", "date": o["date"].isoformat(), "time": o["time"],
                         "title": o["title"], "with": others, "file": "memory/calendar/events.yaml"})
    replace_interactions(brain, "calendar", meetings)
    return {"occurrences": len(occ), "all_day": sum(1 for o in occ if o["all_day"]),
            "cancelled": a["cancelled"], "top": a["top"], "warnings": a["warnings"], "zone": a["zone"],
            "zone_note": a["zone_note"]}


USAGE = ("Usage: python3 importers/calendar_ics.py <file.ics> <brain-folder> [--me <your-email>]... "
         "[--tz <zone, e.g. Europe/London>] (one --me per address)")


def main(argv):
    args, me, tz = argv[1:], [], None
    for flag in ("--me", "--tz"):
        while flag in args:
            i = args.index(flag)
            if i + 1 >= len(args) or args[i + 1].startswith("-") or (flag == "--tz" and tz is not None):
                raise SystemExit(USAGE)
            if flag == "--me":
                me.append(args[i + 1])
            else:
                tz = args[i + 1]
            del args[i:i + 2]
    if len(args) != 2:
        raise SystemExit(USAGE)
    try:
        r = run(args[0], args[1], me, tz)
    except (OSError, zipfile.BadZipFile) as e:
        raise SystemExit(f"Could not read the calendar file: {e}")
    print(f"Calendar: {r['occurrences']} meetings ({r['all_day']} all-day), {r['cancelled']} cancelled skipped.")
    print(r["zone_note"])
    for i, p in enumerate(r["top"], 1):
        print(f"  {i}. {p['name']}: {p['meetings']} meetings")
    for w in r["warnings"]:
        print(f"Note: {w}.")


if __name__ == "__main__":
    main(sys.argv)
