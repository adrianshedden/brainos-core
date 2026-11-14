---
name: show-it-visually
description: Show an answer as one polished page in the AI Ops style, with a headline that says the point, short sections and the file behind every fact. In the Claude app it appears as a page in the chat; in other apps it is saved in views/ and opened. Use when I say "show it visually", "make it a page", "show me that as a page" or "make this look good".
---
# Show it visually

Question: Show this answer as a page.
Cadence: as-needed
Read: skills/show-it-visually/page.html, skills/show-it-visually/style.css

What to do:

1. Take the answer I mean: the last one you gave, unless I name another. Use only what it says and the files it names. Add nothing new.
2. Write it as plain text in this shape, in plain British English with no jargon:
   - `# ` then the headline: one sentence that says the point, for example "Three people are waiting on you, Priya first", not a label such as "Replies".
   - One or two lines of summary, saying only what the points below show.
   - Two to five sections. Each is `## ` and a short heading, then up to five points. A point is one fact on one line, ending with its source: `- Weekly sync with Priya at 10:00. (source: memory/calendar/events.yaml)`. A fact from a connector names it: `(source: Google Calendar connector)`.
   - A fact with no file behind it does not go on the page. Find its file, or leave it out and tell me.
3. Make the page.
   - In the Claude app (the Chat tab or claude.ai): show it as an artifact (a page Claude draws in the chat). Build it from `page.html`: paste the whole of `style.css` where it says `[[STYLE]]` and fill the other slots as the note in `page.html` shows. Save nothing unless I ask.
   - In any other app: from the brain folder, run `python3 skills/show-it-visually/make_page.py . - --name "<two to four words>" --open` (on Windows, `py` instead of `python3`) and give it the text from step 2 as its input. It saves `views/<YYYY-MM-DD>-<name>.html`, with the style pasted in, opens it, and refuses any point that has no source. The first time, it makes the `views/` folder. If Python will not run, fill `page.html` by hand the same way, save it under that name and open it.
4. Tell me in one line where the page is, and that it works offline.

Show your sources: every point on the page ends with the file it came from (or the connector), and the foot of the page lists every file used.
Never: invent a fact, a number or a source, or put anything on the page that was not in the answer or its files. Never link the page to a website, a web font or an online script: it must work offline. Never publish, upload, share or send the page, and never overwrite an earlier page.
