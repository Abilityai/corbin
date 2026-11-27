---
name: follow-up-check
description: Finds where the person asked someone for something and has heard nothing back - in sent mail when a mailbox is connected, and in processed meetings and dropped emails otherwise - adds what is missing to the commitments list as owed to the person, and drafts a short nudge for each one that has waited past the follow-up days. Sends nothing.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, mcp__trinity__report, mcp__trinity__record_metrics
user-invocable: true
argument-hint: "[--days N]"
metadata:
  version: "1.0"
  created: 2026-11-27
---

# Follow-up check

`/check-commitments` reviews what is already on the list. This finds what never made it there:
the questions the person asked that nobody answered.

## Step 1: Window

Look back `--days` (default 30). Follow-up threshold from `workspace/profile/preferences.md`
(default 5 working days). Read policies and procedures.

## Step 2: Find unanswered asks

- **Connected mailbox:** `python3 scripts/mail.py list --folder sent --after <today - days> --newest-first --max 100`.
  Read bodies of messages addressed to people outside the organisation in
  `workspace/profile/about-me.md`. Keep those whose text asks for a reply, a document or a
  decision. For each, check its thread for a later message from a recipient
  (`--filter-file` with `{"thread": "<thread_id>"}`). A reply exists: skip it.
- **Always:** the meeting notes and email notes in `workspace/` within the window: action items
  owed to the person, and messages in "Waiting on them".

## Step 3: Record

For each unanswered ask with no open line already: add an `owed_to_me` line (shape in
`/note-commitment`) with its quote and source.

## Step 4: Draft nudges

For each open `owed_to_me` line past the threshold: one nudge as `/draft-reply` Steps 3 and 4 say,
at most 80 words, referring to the original by date. Mark `Draft - not sent`.

## Step 5: Close

Record `last_run_state` (`not_set_up` is never used here: without a mailbox the run uses the
notes and says "checked your notes only - connect a mailbox to check sent mail too"),
`owed_to_me_open`. Publish a report, `report_type` `chief_of_staff.follow_up_check`.

Reply: how many asks are waiting, oldest first, the nudges in full, and "Nothing was sent."
