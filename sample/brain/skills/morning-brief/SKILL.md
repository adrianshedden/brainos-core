---
name: morning-brief
description: A short, plain brief to start my day. What is on today, who to reply to and one thing to prepare, each with the file or connector it came from. Never sends anything. Use when I say "morning brief", "brief me", "what's on today" or "start my day", or when it runs as a scheduled job each morning.
---
# Morning brief

Question: What do I need to know this morning?
Cadence: daily
Read: memory/calendar/, memory/conversations/, network/, memory/decisions.jsonl, CLAUDE.md, tools/TOOLS.md

What to do:

1. Check today's date and time first.
2. What's on. Today's meetings in time order: the time, the title and who it is with. If `tools/TOOLS.md` lists a calendar connector as on, read today from it first (it has the latest changes), then `memory/calendar/events.yaml`. If nothing is on today, say so in one line and name the next thing coming up.
3. Who to reply to. Up to three people waiting on me: chats in `memory/conversations/`, and any mail or message connector `tools/TOOLS.md` lists as on, where someone else spoke last and I have not answered. Direct questions and people I talk to often (most lines in `network/interactions.jsonl`) come first, group chatter last. One line each: who, and what they are waiting for.
4. One thing to prepare. Pick the one that matters most today: a meeting linked to a goal in `CLAUDE.md`, or something I said I would do (in my own messages or `memory/decisions.jsonl`) that falls today. Say what to prepare and why, in one line. For more, offer the `prep-my-next-meeting` skill.
5. Keep it under about 150 words, in this order: what's on, who to reply to, one thing to prepare. Plain words, no jargon.
6. If it ran as a scheduled job, add one line to `memory/events.jsonl` saying the brief ran, shaped as `memory/MEMORY.md` says. Change nothing else.

Show your sources: after each point, name the file it came from (for example `memory/calendar/events.yaml` or the chat file in `memory/conversations/`) or the connector.
Never: send, reply, post or forward anything, or contact anyone. Never accept, decline or move a meeting. The brief stays in the chat for me to read. Never invent a meeting, a message or a promise: if the files do not show it, say so.
