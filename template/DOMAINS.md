# Domains

Each folder below is a domain: one area of this brain, with its own `{DOMAIN}.md` saying what goes in, what stays out and which files it holds. Read a domain's file only when the task touches it.

## Core domains (every brain has these)

| Domain | File | What it holds |
|---|---|---|
| automations | `automations/AUTOMATIONS.md` | Jobs the person has asked an AI app to run on a schedule |
| memory | `memory/MEMORY.md` | What has happened: calendar, conversations, decisions, events, profile |
| scripts | `scripts/SCRIPTS.md` | Small helper programs, such as the jobs list |
| skills | `skills/SKILLS.md` | Things an AI can do for the person, one folder each |
| tools | `tools/TOOLS.md` | AI tools and connectors in use, and how to point each at this folder |

## Personal domains (chosen for this person)

| Domain | File | What it holds |
|---|---|---|
{{PERSONAL_DOMAINS}}

## Adding a domain

Ask the person first. For an area from BrainOS's library (network, work, knowledge, family, health, finance), run `python3 kit/create_brain.py . --add work,family` from this folder (their areas, comma-separated): it makes each folder and its `{DOMAIN}.md`, adds a row here, a line to the routing table and the file index in `AGENTS.md`, and its place in `brain.yaml`, and changes nothing else.

For any other area, add one when a kind of information keeps coming up and fits none of the folders above. Make the folder, write its `{DOMAIN}.md` (what goes in, what stays out, its files), add a row here and a line to the routing table in `AGENTS.md`, and note the decision in `memory/decisions.jsonl`.
