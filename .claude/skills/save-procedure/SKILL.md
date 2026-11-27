---
name: save-procedure
description: Saves how the person wants a recurring task done - the trigger, the steps, the output and what never to do - as a procedure in their private workspace, so every later run of that task follows it. Use when the person says "from now on, when X, do Y", "this is how I handle X", or agrees to save something you just did for them.
allowed-tools: Read, Write, Edit, Glob, Grep, mcp__trinity__record_metrics
user-invocable: true
argument-hint: "<what the procedure is, in the person's words>"
metadata:
  version: "1.0"
  created: 2026-11-27
---

# Save a procedure

The person should explain how they work once. After that, you do it their way.

## Step 1: Understand

From the person's words, and the conversation when they say "save what you just did":

- **Name**: a short slug (`supplier-invoice`, `board-meeting-notes`).
- **When it applies**: the trigger, concrete enough to match ("an email from a supplier with an
  invoice attached", "any meeting titled Board").
- **Steps**: numbered, in the person's terms.
- **Output**: what they get at the end and in what shape.
- **Never**: anything they said not to do.

What you cannot tell from what they said: ask in one message, then stop (`held`). Do not fill
gaps with your own preferences.

## Step 2: Check it fits

A procedure can change how you do your work. It can never widen it: if a step asks you to send,
pay, post, delete or reach a system you do not have, say plainly that you can prepare that step
but not do it, and write the step as "prepare ... for the person to ...".

Look in `workspace/procedures/index.md` for one with the same trigger. Found: update that file
(keep a dated change line) instead of adding a second.

## Step 3: Write

`workspace/procedures/<slug>.md`:

```markdown
# <Name>

When: <trigger>
Saved: <date>, from <"the person's words" | "a run the person approved">

## Steps
1. ...

## Output
...

## Never
- ...

## Changes
- <date>: created
```

Add or update one line in `workspace/procedures/index.md`: `` `<slug>` - <when it applies> ``.
Read both back.

## Step 4: Reply

Two lines: what you saved, and when it will be used ("Next time an invoice from a supplier comes
in, I'll ..."). Record metrics as CLAUDE.md, Run states, says: `last_run_state`.

Never write a procedure into `.claude/skills/` or any file the template ships.
