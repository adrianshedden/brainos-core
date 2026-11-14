# Automations

Jobs the person has asked their AI app to run by itself on a schedule, such as "every Monday at 8am, do the what's-on-my-plate skill".

## How to set one up

- In the Claude desktop app, use its Scheduled feature: make a scheduled task, choose how often, and give it one instruction, for example "Follow `skills/morning-brief/SKILL.md` in my brain folder." How often it can run, and whether the app must stay open, is in the app's own help pages: check there.
- Other AI apps have their own way, or none. If yours has none, run the skill by hand; `python3 scripts/jobs.py list .` shows which are due.
- Suggested jobs. Daily: `morning-brief` (each morning). Weekly: `weekly-review` (Friday afternoon).
- Others that work well: `whats-on-my-plate` (Monday morning), `what-am-i-putting-off` (Friday afternoon), `who-to-reply-to-first` (daily) and `who-have-i-gone-quiet-with` (monthly; it only drafts; you send).

## What goes in

- One row in the table below for each scheduled job: what it runs, how often, in which app, and when it was set up.
- When a scheduled job runs, it adds one line to `memory/events.jsonl` saying what it did.

## What stays out

- Anything that sends, posts or replies by itself. A scheduled job only reads and drafts; the person sends.
- Passwords and keys.

## Scheduled jobs

| Job | Runs | How often | In | Set up on |
|---|---|---|---|---|
| (none yet) | | | | |
