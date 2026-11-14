---
name: weekly-review
description: Once a week, look back and ahead. What happened this week, open loops, who has gone quiet and my top three for next week, each with the file it came from. Saves one short dated line in memory/events.jsonl. Never sends anything. Use when I say "weekly review", "review my week" or "plan next week", or when it runs as a scheduled job.
---
# Weekly review

Question: How did my week go, and what are my top three for next week?
Cadence: weekly
Read: memory/calendar/, memory/conversations/, network/, memory/decisions.jsonl, memory/events.jsonl, CLAUDE.md, tools/TOOLS.md

What to do:

1. Check today's date. "This week" is the seven days up to today. "Next week" is the seven days after.
2. Last week's top three. If `memory/events.jsonl` has an earlier line starting "Weekly review", begin with one line: which of its top three got done, going by this week's files.
3. What happened. This week's meetings (from `memory/calendar/events.yaml`, and the calendar connector if `tools/TOOLS.md` lists one as on), decisions added to `memory/decisions.jsonl`, and the chats in `memory/conversations/` with the most messages this week. Five lines at most.
4. Open loops. Things I said I would do, send or arrange, in my own messages or in `memory/decisions.jsonl`, with no sign of being done since, and people still waiting on a reply from me. Oldest first, five at most.
5. Who has gone quiet. My key people (named in `CLAUDE.md`, or with the most lines in `network/interactions.jsonl`) with nothing in the last 30 days: who, and when we last spoke. Three at most. For a draft note to any of them, offer the `who-have-i-gone-quiet-with` skill.
6. Next week's top three. Three things, one line each with why. Weigh next week's meetings, the open loops and my goals in `CLAUDE.md`. If the goals still say "not known yet", say so.
7. Save one line at the end of `memory/events.jsonl`, shaped as `memory/MEMORY.md` says: `{"date": "<today>", "event": "Weekly review: <one sentence on the week>. Top three for next week: 1) ... 2) ... 3) ...", "source": "weekly-review skill, from <the files you used>", "confidence": "medium"}`. When I run it myself, show me the line and ask before saving. When it runs as a scheduled job, save it and say so at the top.

Keep the whole review under about 250 words, in the order above.

Show your sources: after each point, name the file it came from and its date, or the connector. The saved line names its files in `source`.
Never: send, reply, post or schedule anything, or contact anyone. Never accept, decline or move a meeting. Never change or delete an earlier line in any file: only add the one new line. Never invent an event, a promise or a reason: if the files do not show it, say so.
