# Scripts

Small helper programs that live in the brain. Plain Python 3: nothing to install.

## Files

| File | What it does |
|---|---|
| `jobs.py` | Lists the skills, says which are due by their `Cadence:` line, and marks one done |

- See what is due: `python3 scripts/jobs.py list .` (run from inside this brain folder)
- Mark one done: `python3 scripts/jobs.py done . whats-on-my-plate`

It keeps when each skill was last done in `skills/jobs-state.json`.

## What goes in

- Small scripts the person asked for, each with a line in the table above saying what it does.

## What stays out

- Anything that uses the internet, sends messages or holds passwords.
- The importers: they stay in the BrainOS download, not in the brain.
