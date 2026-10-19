# Scripts

Small helper programs that live in the brain. Plain Python 3: nothing to install.

## Files

| File | What it does |
|---|---|
| `jobs.py` | Lists the skills, says which are due by their `Cadence:` line, and marks one done |
| `level1.py` | Keeps level 1 word for word the same in `CLAUDE.md`, `GEMINI.md` and the top of `AGENTS.md` |

- See what is due: `python3 scripts/jobs.py list .` (run from inside this brain folder)
- Mark one done: `python3 scripts/jobs.py done . whats-on-my-plate`

It keeps when each skill was last done in `skills/jobs-state.json`.

- Check level 1 matches at every front door: `python3 scripts/level1.py check .`
- After editing level 1 in `CLAUDE.md`, copy it to the others: `python3 scripts/level1.py sync .`

## What goes in

- Small scripts the person asked for, each with a line in the table above saying what it does.

## What stays out

- Anything that uses the internet, sends messages or holds passwords.
- The importers: they stay in BrainOS (`kit/`), not in `scripts/`.
