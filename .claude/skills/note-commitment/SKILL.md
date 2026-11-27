---
name: note-commitment
description: Writes down, on the person's word, a promise they made or were made, or marks one already on the list as done, dropped, reopened, postponed or newly due. Also defines the shape of a line in the commitments list that every other playbook uses.
allowed-tools: Read, Write, Edit, Glob, mcp__trinity__record_metrics
user-invocable: true
argument-hint: "<what the person says> [id]"
metadata:
  version: "1.0"
  created: 2026-11-27
---

# Note a commitment

A promise made on a call or in a corridor is in no mailbox. Write it down when the person
mentions it. Only the person can say something is settled.

## The commitments list

`workspace/commitments/commitments.yaml`, a YAML list. Every playbook writes lines in this shape:

```yaml
- id: C-2026-0001           # C-<year>-<number>, never reused
  direction: i_owe          # i_owe (the person owes it) | owed_to_me (someone owes the person)
  who: ""                   # the other party, as the source names them (name, address if known)
  what: ""                  # one line
  quote: ""                 # the sentence it rests on, max 200 characters; empty when told in chat
  source: ""                # "meeting <title>, <date>" | "email <subject>, <from>, <date>" | "told by the person, <date>"
  thread: ""                # Message-ID of the email thread when known, else empty
  recorded: 2026-01-15      # the day the line was written
  due:                      # YYYY-MM-DD, computed from the stated words (CLAUDE.md, Dates); empty when no day was named
  due_text: ""              # the words as said ("by Thursday", "20 January", "next week")
  due_assumed: ""           # what was assumed to compute it ("year from the meeting date 2026-11-23"); empty when nothing was
  not_before:               # only on the person's word
  status: open              # open | answered | done | dropped
  evidence: ""              # for answered: what moved it, with its date
  notes: []                 # one dated line per change
```

Rules every playbook follows: one line per party and thing (look for an open line with the same
`who` and `what` before adding); `answered` means "something moved, look at it", never settled;
only the person's word sets `done` or `dropped`; nothing is ever deleted.

## Process

1. Read policies and procedures (CLAUDE.md, Before every task). Load the list; none yet means
   empty. If it exists and cannot be parsed, change nothing: state `blocked`.
2. Work out whether this is a **new line** ("I promised...", "they said they would...") or a
   **change** ("done", "drop it", "not before March", "it's due on the 12th now", "reopen it").
3. **New line.** `direction`, `who` and `what` in the person's words; `source` =
   `told by the person, <today>` (add the meeting when they name one); `due` only when they name a
   day, computed from today as CLAUDE.md, Dates, says ("by Friday" -> the date, and say which date
   you wrote). No `who` or no `what`:
   write nothing, ask for the missing part; state `held`.
4. **Change.** Find the line by id, or by who and what. No match or several: write nothing, list
   the candidates in plain words; state `held`. Otherwise apply the change and add a dated note
   `told by the person`. Never change `who`, `what` or `quote` of a line read from a source.
5. Write the file sorted by id and read it back. Record metrics as CLAUDE.md, Run states, says:
   `last_run_state`, `i_owe_open`, `owed_to_me_open`.
6. Reply in one or two lines: what was written, the due date if any, the open counts, and what is
   missing ("tell me by when").
