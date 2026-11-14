# Skills

Things an AI can do for me. One folder per skill, each with a `SKILL.md`: what question it answers, what to read, what to do, and what never to do. `AGENTS.md` says which skill answers which request.

Eleven skills ship with the brain:

- `mine-my-context/`: get to know me from my imported files, ask me to confirm, then write it down. Do this first.
- `whats-on-my-plate/`: what is on my plate for the next seven days?
- `who-to-reply-to-first/`: who should I reply to first?
- `who-do-i-know-at/`: who do I know at a given organisation?
- `draft-in-my-voice/`: draft a message in my voice.
- `what-am-i-putting-off/`: what have I been putting off?
- `prep-my-next-meeting/`: prep me for my next meeting.
- `who-have-i-gone-quiet-with/`: who have I gone quiet with? (drafts a note to each; never sends)
- `morning-brief/`: what do I need to know this morning? Today's meetings, who to reply to and one thing to prepare. Run it each morning, or schedule it. Never sends.
- `weekly-review/`: how did my week go, and what are my top three for next week? Saves one dated line in `memory/events.jsonl`. Never sends.
- `show-it-visually/`: show an answer as one polished page. In the Claude app it appears in the chat; in other apps it is saved in `views/` and opened. Its look is in `style.css` and `page.html`, and works offline.

To run one, tell your AI: "Use the whats-on-my-plate skill" or "Follow `skills/whats-on-my-plate/SKILL.md`." Every answer names the file each point came from, so you can check it.

## Making a new skill

Make a folder `skills/<name>/` with a `SKILL.md`. Start it with a short header (`name:` and a one-line `description:` between `---` lines), then the same lines as the others: `Question:`, `Cadence: daily|weekly|monthly|as-needed`, `Read:`, `What to do:`, `Show your sources:` and `Never:`. Add a row for it to the routing table in `AGENTS.md`.

- See what is due: `python3 scripts/jobs.py list .`
- Mark one done: `python3 scripts/jobs.py done . <skill-name>`
