"""connections.yaml: every source the setup can connect, in every AI app, with the exact clicks (kit 2.0).

Checks the file against the sprint contract's schema: the twelve source ids, the route fields, Rian's
route order (builtin, custom, local, cli, export), a builtin or export route for every source, a way in
from every app, command-line routes marked technical_only, checked_on a real date or null, a harmless
proof read, and a scheduler for every app. Read with a small standard-library reader (the kit never
needs PyYAML); where PyYAML is installed, the two readings must agree."""
import json
import re
import unittest
from datetime import date
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
FILE = KIT / "connections.yaml"

SOURCES = {"google-calendar", "gmail", "google-drive", "outlook-calendar", "outlook-mail", "onedrive", "whatsapp",
           "linkedin", "notion", "slack", "apple-contacts", "other-custom"}
APPS = ["claude", "chatgpt", "cursor", "opencode", "orca", "terminal"]
TYPES = ["builtin", "custom", "local", "cli", "export"]  # Rian's order
ROUTE_FIELDS = {"app", "type", "clicks", "proof_read", "technical_only", "checked_on", "notes"}
SCHEDULER_FIELDS = {"how", "clicks", "checked_on"}
# Command-line tools: only ever on a technical_only cli route (Rian, 19 Oct: never pushed on the day).
CLI_TOOLS = re.compile(r"\b(gws|m365|wacli)\b")
# Words a non-technical person should never be asked to deal with in a click. What the AI does with
# settings files goes in the route's notes, not its clicks.
JARGON = re.compile(r"\b(OAuth|JSON|token|config\.toml|mcp\.json|opencode\.json|npm|brew)\b", re.IGNORECASE)
READ_VERBS = ("List ", "Show ", "Check ")
NOT_HARMLESS = re.compile(r"\b(send|delete|post|reply|forward|archive|move|bin|trash)\b", re.IGNORECASE)


def load(text):
    """Read the YAML this file uses: block maps and lists, "double-quoted" strings, null, true, false,
    whole numbers, [] and {}. Anything else is refused with its line number."""
    lines = []
    for n, raw in enumerate(text.splitlines(), 1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if "\t" in raw:
            raise ValueError(f"line {n}: tab character")
        lines.append([len(raw) - len(raw.lstrip(" ")), raw.strip(), n])
    pos = 0

    def scalar(s, n):
        if s.startswith('"'):
            value, end = json.JSONDecoder().raw_decode(s)
            if s[end:].strip():
                raise ValueError(f"line {n}: text after a quoted string")
            return value
        known = {"null": None, "true": True, "false": False, "[]": [], "{}": {}}
        if s in known:
            return known[s]
        if re.fullmatch(r"-?\d+", s):
            return int(s)
        raise ValueError(f"line {n}: unquoted text {s!r}")

    def block(indent):
        nonlocal pos
        if not lines[pos][1].startswith("- "):
            return mapping(indent)
        out = []
        while pos < len(lines) and lines[pos][0] == indent and lines[pos][1].startswith("- "):
            rest, n = lines[pos][1][2:].strip(), lines[pos][2]
            if re.match(r"^[A-Za-z0-9_-]+:( |$)", rest):
                lines[pos] = [indent + 2, rest, n]  # "- key: value" opens a map one level in
                out.append(mapping(indent + 2))
            else:
                pos += 1
                out.append(scalar(rest, n))
        return out

    def mapping(indent):
        nonlocal pos
        out = {}
        while pos < len(lines) and lines[pos][0] == indent:
            content, n = lines[pos][1], lines[pos][2]
            m = re.match(r"^([A-Za-z0-9_-]+):(?: (.*))?$", content)
            if not m:
                raise ValueError(f"line {n}: expected key: value")
            key, value = m.group(1), m.group(2)
            if key in out:
                raise ValueError(f"line {n}: {key} appears twice")
            pos += 1
            if value:
                out[key] = scalar(value, n)
            elif pos < len(lines) and lines[pos][0] > indent:
                out[key] = block(lines[pos][0])
            else:
                out[key] = None
        if pos < len(lines) and lines[pos][0] > indent:
            raise ValueError(f"line {lines[pos][2]}: unexpected indent")
        return out

    data = mapping(0)
    if pos != len(lines):
        raise ValueError(f"line {lines[pos][2]}: not read")
    return data


DATA = load(FILE.read_text(encoding="utf-8"))


def routes():
    for sid, source in DATA["sources"].items():
        for i, route in enumerate(source["routes"], 1):
            yield sid, i, route


def is_real_date(value):
    if not (isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value)):
        return False
    try:
        return date(2026, 1, 1) <= date.fromisoformat(value) <= date.today()
    except ValueError:
        return False


class ConnectionsYaml(unittest.TestCase):
    def test_the_reader_refuses_what_it_cannot_read(self):
        for bad in ("a: unquoted words\n", "a:\n\tb: 1\n", 'a: "x"\na: "y"\n', 'a:\n    b: 1\n  c: 2\n'):
            with self.assertRaises(ValueError, msg=bad):
                load(bad)
        self.assertEqual(load('a:\n  - b: "x"\n    c: null\n  - "y"\nd: []\n'),
                         {"a": [{"b": "x", "c": None}, "y"], "d": []})

    def test_pyyaml_reads_it_the_same_way_when_installed(self):
        try:
            import yaml
        except ImportError:
            self.skipTest("PyYAML not installed; the kit does not need it")
        self.assertEqual(yaml.safe_load(FILE.read_text(encoding="utf-8")), DATA)

    def test_top_level_has_sources_and_schedulers_only(self):
        self.assertEqual(set(DATA), {"sources", "schedulers"})

    def test_the_twelve_source_ids(self):
        self.assertEqual(set(DATA["sources"]), SOURCES)
        for sid, source in DATA["sources"].items():
            self.assertEqual(set(source), {"name", "kind", "routes"}, sid)
            self.assertTrue(isinstance(source["name"], str) and source["name"].strip(), sid)
            self.assertIn(source["kind"], ("live", "export", "both"), sid)
            self.assertTrue(isinstance(source["routes"], list) and source["routes"], sid)

    def test_every_route_has_exactly_the_contract_fields(self):
        for sid, i, r in routes():
            where = f"{sid} route {i}"
            self.assertEqual(set(r), ROUTE_FIELDS, where)
            self.assertIn(r["app"], APPS + ["any"], where)
            self.assertIn(r["type"], TYPES, where)
            self.assertTrue(isinstance(r["clicks"], list) and r["clicks"], where)
            for click in r["clicks"]:
                self.assertTrue(isinstance(click, str) and click.strip(), where)
            self.assertTrue(isinstance(r["proof_read"], str) and r["proof_read"].strip(), where)
            self.assertIsInstance(r["technical_only"], bool, where)
            self.assertIsInstance(r["notes"], str, where)

    def test_routes_follow_rians_order(self):
        for sid, source in DATA["sources"].items():
            order = [TYPES.index(r["type"]) for r in source["routes"]]
            self.assertEqual(order, sorted(order), f"{sid}: routes must go builtin, custom, local, cli, export")

    def test_every_source_has_a_builtin_or_an_export_route(self):
        for sid, source in DATA["sources"].items():
            self.assertTrue({"builtin", "export"} & {r["type"] for r in source["routes"]}, sid)

    def test_kind_matches_the_routes(self):
        for sid, source in DATA["sources"].items():
            types = {r["type"] for r in source["routes"]}
            live, export = bool(types - {"export"}), "export" in types
            expected = "both" if live and export else "export" if export else "live"
            self.assertEqual(source["kind"], expected, sid)

    def test_every_app_has_a_way_in_for_every_source(self):
        for sid, source in DATA["sources"].items():
            apps = {r["app"] for r in source["routes"]}
            for app in APPS:
                self.assertTrue({app, "any"} & apps, f"{sid}: nothing for {app}")

    def test_command_line_routes_are_for_technical_people_only(self):
        cli = [(sid, r) for sid, _, r in routes() if r["type"] == "cli"]
        self.assertTrue(cli, "no command-line routes: the guard would pass by accident")
        for sid, r in cli:
            self.assertIs(r["technical_only"], True, sid)
        for sid, i, r in routes():
            if CLI_TOOLS.search(" ".join(r["clicks"]) + " " + r["proof_read"]):
                self.assertEqual(r["type"], "cli", f"{sid} route {i} names a command-line tool")

    def test_named_command_line_tools_are_there(self):
        clicks = {sid: " ".join(" ".join(r["clicks"]) for r in s["routes"] if r["type"] == "cli")
                  for sid, s in DATA["sources"].items()}
        for sid in ("google-calendar", "gmail", "google-drive"):
            self.assertIn("@googleworkspace/cli", clicks[sid])
        for sid in ("outlook-calendar", "outlook-mail", "onedrive"):
            self.assertIn("@pnp/cli-microsoft365", clicks[sid])
        self.assertIn("wacli", clicks["whatsapp"])

    def test_whatsapp_is_beeper_first_then_export(self):
        wa = DATA["sources"]["whatsapp"]["routes"]
        claude = next(r for r in wa if r["app"] == "claude")
        self.assertEqual(claude["type"], "local")
        self.assertIn("Beeper", " ".join(claude["clicks"]))
        self.assertIn("deny send_message", " ".join(claude["clicks"]))
        self.assertIn("Opt-in", claude["notes"])
        self.assertIn("export", [r["type"] for r in wa])

    def test_personal_outlook_falls_back_to_a_calendar_export(self):
        routes_ = DATA["sources"]["outlook-calendar"]["routes"]
        claude = next(r for r in routes_ if r["app"] == "claude")
        self.assertIn("personal Outlook.com", claude["notes"])
        self.assertIn("IT admin", claude["notes"])
        self.assertTrue(any(r["type"] == "export" and "outlook.com" in " ".join(r["clicks"]) for r in routes_))

    def test_checked_on_is_a_real_date_or_null(self):
        checked = 0
        for sid, i, r in routes():
            if r["checked_on"] is not None:
                checked += 1
                self.assertTrue(is_real_date(r["checked_on"]), f"{sid} route {i}: {r['checked_on']!r}")
        self.assertGreater(checked, 0)
        for app, s in DATA["schedulers"].items():
            self.assertTrue(s["checked_on"] is None or is_real_date(s["checked_on"]), app)

    def test_every_proof_read_is_harmless(self):
        for sid, i, r in routes():
            read = r["proof_read"]
            self.assertTrue(read.startswith(READ_VERBS), f"{sid} route {i}: {read}")
            if NOT_HARMLESS.search(read):
                self.assertIn("do not", read.lower(), f"{sid} route {i}: {read}")

    def test_clicks_for_everyone_are_free_of_jargon(self):
        for sid, i, r in routes():
            if not r["technical_only"]:
                for click in r["clicks"]:
                    self.assertIsNone(JARGON.search(click), f"{sid} route {i}: {click}")

    def test_every_route_ends_by_waiting_for_the_person(self):
        for sid, i, r in routes():
            self.assertIn("say done", r["clicks"][-1].lower(), f"{sid} route {i}")

    def test_a_scheduler_for_every_app(self):
        self.assertEqual(set(DATA["schedulers"]), set(APPS))
        for app, s in DATA["schedulers"].items():
            self.assertEqual(set(s), SCHEDULER_FIELDS, app)
            self.assertTrue(isinstance(s["how"], str) and s["how"].strip(), app)
            self.assertTrue(isinstance(s["clicks"], list) and s["clicks"], app)
            self.assertTrue(all(isinstance(c, str) and c.strip() for c in s["clicks"]), app)
        self.assertIn("Scheduled", DATA["schedulers"]["claude"]["how"])


if __name__ == "__main__":
    unittest.main()
