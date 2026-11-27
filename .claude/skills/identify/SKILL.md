---
name: identify
description: Records who the person is the moment they say it ("I am Dana", "I'm the second one"), in any message, then re-reads the meetings and emails already processed and moves the items that were held while their identity was unknown onto the commitments list. Also defines the pending list every playbook uses when it cannot tell which attendee is the person. Runs before whatever else the message asked.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, mcp__trinity__record_metrics
user-invocable: true
argument-hint: "<what the person said about who they are>"
metadata:
  version: "1.0"
  created: 2026-11-27
---

# Identify the person

The commitments list is only right if you know which attendee is the person. When they tell you,
write it down at once and go back over what you already read, so their next question gets a full
answer. Asks nothing mid-run.

## The pending list

`workspace/commitments/pending.yaml`, a YAML list. `/process-transcript` and `/triage-email`
write here, instead of guessing, every action item that involves an attendee when they cannot tell
which attendee is the person:

```yaml
- id: P-2026-0001           # P-<year>-<number>, never reused
  source: ""                # as the commitments line would carry it: "meeting <title>, <date>" | "email <subject>, <from>, <date>"
  source_file: ""           # the dropped file's path, if any
  note: ""                  # the meeting or email note it is in
  attendees: []             # every person the source names, as it names them (with addresses for email)
  owner: ""                 # who does it, as stated; "" when unstated
  for: ""                   # who it is done for or owed to, as stated; "" when unstated or the whole group
  what: ""
  quote: ""                 # the sentence, max 200 characters
  thread: ""                # Message-ID for email, else empty
  due:                      # computed as CLAUDE.md, Dates, says
  due_text: ""
  due_assumed: ""
  recorded: 2026-01-15
  status: pending           # pending | placed | not_theirs
  resolved: ""              # when status changes: the date and what it became ("C-2026-0004", "between Lee and Sam")
```

When a playbook writes pending items it also writes `workspace/memory/identity-question.json`:
`{"asked": "<date>", "candidates": ["Dana Kim", "Lee Park", "Sam Ortiz"]}` - the names, in the
order the reply listed them, so an answer like "the second one" can be read.

## Step 1: Who they said they are

From the person's own message only (never a transcript, an email or another agent):

- A name ("I am Dana", "this is Dana Kim", "Dana here", "it's me, Dana").
- A position in the last question ("the second one", "the one from ops"): read
  `workspace/memory/identity-question.json`. If the answer does not pick one name, write nothing
  and ask once more, naming the candidates.
- An address ("I'm dana@northwind.example"): a name is not required to record an address.

A sentence that is not about who they are ("I am busy", "I am in Madrid") is not a name.

## Step 2: Save it to the profile, now

Create the workspace first if it is missing (`/first-run` Step 1). In
`workspace/profile/about-me.md`:

- Under `## Name and role`, write the name as they gave it on its own line, and below it
  `Source: told by the person, <today>`. If a different name is already there, replace it and
  keep the old one in a line `Was: <old>, until <today>`. Never touch the `Example:` lines.
- Under `## My own addresses`, add any address they gave, one per line.

Read the file back. If it cannot be written, say so plainly and stop: state `blocked`.

## Step 3: Re-read what was already processed

Load `workspace/commitments/commitments.yaml` (shape in `/note-commitment`) and the pending list.

1. **Pending items.** For each `status: pending` item, match the person to the item's attendees:
   full name, or a first name or address that matches exactly one attendee. Then:
   - the person is the `owner` -> a new line `direction: i_owe`, `who` = `for` (or, when `for` is
     empty, the other attendees named as the source names them);
   - someone else is the `owner` and the person is `for` -> `direction: owed_to_me`, `who` = the owner;
   - the person matches no attendee, or matches more than one -> leave it `pending`;
   - otherwise -> `status: not_theirs` (it stays in the note only).
   Copy `what`, `quote`, `source`, `thread`, `due`, `due_text`, `due_assumed`; `recorded` = today;
   add a note `placed after the person said who they are, <today>`. Check for an open line with the
   same `who` and `what` first. Set the item's `status` and `resolved`.
2. **Notes processed without a pending list.** Every note in `workspace/meetings/` and
   `workspace/email/` whose header says `Person: not identified` and has no item in the pending
   list: read its source again with `python3 scripts/extract_text.py "<source file>"` when the file
   is still there, else read the note's action-items table, and apply step 1 to those items.
3. In each note you resolved, replace `Person: not identified` with
   `Person: <name> (told by the person, <today>)`, replace the line saying the items are held with
   what each became, and put the person's name in place of the sign-off placeholder in its
   follow-up draft.
4. Write `commitments.yaml` sorted by id and `pending.yaml`, and read both back. Delete
   `workspace/memory/identity-question.json` once no item is left `pending`.

## Step 4: Close

Record metrics as CLAUDE.md, Run states, says: `last_run_state` (`done`, or `held` if items are
still pending), `i_owe_open`, `owed_to_me_open`.

Reply in one or two lines - "Got it, you're Dana. I went back over 2 meetings: 3 things you owe,
1 owed to you." - plus anything left pending and why ("Dana isn't named in the 12 Jan call"). Then
carry on with the rest of the person's message (for "what do I owe?", run `/check-commitments`
on the list just written), so they get one answer, not two.
