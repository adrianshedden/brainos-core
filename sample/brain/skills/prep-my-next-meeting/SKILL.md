---
name: prep-my-next-meeting
description: Prep me for my next meeting. Who it is with, when we last spoke and about what, anything I promised them, how it links to my goals, and three questions to ask. Use when I say "prep me for my next meeting", "get me ready for my 2pm", "brief me before this call" or name a meeting.
---
# Prep me for my next meeting

Question: Prep me for my next meeting.
Cadence: as-needed
Read: memory/calendar/, network/, memory/conversations/, memory/decisions.jsonl, CLAUDE.md, tools/TOOLS.md

What to do:

1. Find the meeting. Check today's date and time first. If I named a meeting, use that one; if not, use the next one that has not started yet. If `tools/TOOLS.md` lists a calendar connector as on, look there first (it has the latest changes); if not, use `memory/calendar/events.yaml`. If neither has a meeting coming up, say so and stop.
2. Who it is with. Match each person in the meeting to `network/people.jsonl`, by email first, then by name. Give their role and organisation from that file. If someone does not match, say "not in the brain" for them. Do not guess who they are.
3. When we last spoke, and about what. For each person, their most recent line in `network/interactions.jsonl` before today: the date, what kind (meeting, message, chat) and its title or subject. If the line names a `file` in `memory/conversations/`, read the last few messages there to say what it was about. If the meeting repeats, say when the last one was.
4. Anything I promised them. Look in those conversations for messages I wrote myself saying I would do, send, bring or arrange something, and for lines in `memory/decisions.jsonl` that name them. Quote my words, short. If you find none, say "nothing found", not "nothing promised".
5. Why it matters. Link the meeting to a goal under "Goals this quarter" in `CLAUDE.md` (level 1), only if the link is clear. If the goals still say "not known yet", say so.
6. Three questions to ask, each built on something you found above.

Keep the whole answer under about 200 words, in this order: meeting and time; who; last spoke; promised; goal; three questions.

Show your sources: after every point, name the file it came from (for example `network/interactions.jsonl`) or the calendar connector, and a confidence: high (stated in the file), medium (worked out from several lines) or low (one hint).
Never: invent a person, a past conversation, a promise or a goal. If there is no match, say so. Never accept, decline or move the meeting, and never contact anyone.
