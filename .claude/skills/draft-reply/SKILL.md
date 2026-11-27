---
name: draft-reply
description: Writes a reply to one email or message in the person's own tone - short, the point first, one ask - using only facts the person, the message, the commitments list or the Company Brain gave. Returns it as text for the person to send. Learns the person's tone from their corrections.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, mcp__trinity__chat_with_agent, mcp__trinity__record_metrics
user-invocable: true
argument-hint: "<the message, a dropped file, or who to reply to> [what to say]"
metadata:
  version: "1.0"
  created: 2026-11-27
---

# Draft a reply

The person should be able to send what you write with one read and no edits.

## Step 1: The message

From a path (`python3 scripts/extract_text.py`), pasted text, or the latest triage note naming
the sender. If you cannot tell which message is meant, name the candidates and stop (`held`).

## Step 2: What to say

- What the person told you to say, if they did. That is the substance; you only shape it.
- Otherwise: what the message asks, and what the record holds - open lines with this person in
  the commitments list, the latest meeting note naming them, and, for a fact about them or their
  organisation, the Company Brain (`/ref-query <name>`, as CLAUDE.md says).
- A fact you do not have (a price, a date, a yes or no that is the person's to give) becomes a
  placeholder `[YOU: the date you can deliver]`. Never invent it.

## Step 3: Write

Read `workspace/profile/tone.md` and policies. Then:

- at most 150 words unless the tone file says otherwise or the person asked for more;
- the point in the first sentence; one ask; no headings; no filler openings;
- greeting and sign-off as the tone file says;
- the same language as the message, unless told otherwise;
- subject `Re: <original>`; to the sender; cc only those the person names.

## Step 4: Check

Re-read once and cut. Every fact traceable to Step 2. No promise the person did not make.
Mark it `Draft - not sent`.

## Step 5: Learn the tone

If the person edits the draft or says "too formal", "shorter", "never say X", propose one new
line for `workspace/profile/tone.md` ("Add to your tone notes: *no exclamation marks*?") and add
it, dated, when they agree. A rule beyond tone ("always cc my co-founder on supplier mail")
goes through `/save-policy`.

## Step 6: Reply

The draft in full, then a line listing any `[YOU: ...]` placeholders. Record metrics as CLAUDE.md, Run states, says: `last_run_state`
(`held` if placeholders remain). Nothing is sent.
