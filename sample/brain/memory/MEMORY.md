# Memory

What has happened. Filled by the importers and, with the person's say-so, by skills.

## Files

| File or folder | What it holds | Written by |
|---|---|---|
| `decisions.jsonl` | Decisions the person has made, one per line | Skills, with the person's say-so |
| `events.jsonl` | Things that happened: milestones, and each run of a scheduled job | Skills and scheduled jobs |
| `calendar/events.yaml` | Every meeting, one entry per occurrence, in one time zone | The calendar importer |
| `conversations/` | Readable chat text (`whatsapp/<chat>.md`) and your own X posts (`x-posts.yaml`) | The WhatsApp and X importers |
| `profile/` | What your LinkedIn and X exports say about you, and your LinkedIn positions | The LinkedIn and X importers |
| `people/` | Only when the brain has no network domain: `people.jsonl` and `interactions.jsonl` | The LinkedIn, WhatsApp, calendar and contacts importers |

Re-running an importer replaces only its own files and lines.

## Line shapes

- `decisions.jsonl`: `{"date": "YYYY-MM-DD", "decision": "...", "why": "...", "source": "...", "confidence": "high|medium|low"}`
- `events.jsonl`: `{"date": "YYYY-MM-DD", "event": "...", "source": "...", "confidence": "high|medium|low"}`

## What goes in

- What happened and what was decided, in the person's own words where possible, each line with its source.

## What stays out

- Other people's private data from anywhere other than the person's own exports.
- Passwords, card numbers and keys.
- Guesses. If it is not in the files and the person has not said it, it does not go in.

## What's here

- (Written by `mine-my-context`: a line or two on what the imported memory covers, with source and confidence.)
