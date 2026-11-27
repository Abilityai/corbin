---
name: connect
description: Explains, when the person asks, how to connect their calendar or their Google mailbox so the agent can read them - read-only, optional, step by step - and checks a connection once it is in place. The agent works fully without either; nothing is ever required.
allowed-tools: Read, Write, Edit, Bash
user-invocable: true
argument-hint: "[calendar | mail | check]"
metadata:
  version: "1.0"
  created: 2026-11-27
---

# Connect a calendar or a mailbox (optional)

Only run when the person asks. Never suggest it more than once a week, and never present it as
something they must do. Never ask the person to paste a secret into chat: secrets go into the
Trinity Credentials tab, by name.

## What to say first

"You don't need this - I work from what you drop on me. Connecting means I see new mail and
today's meetings without you exporting them. Both are read-only: I can't send, reply, accept or
delete anything."

## calendar

1. In the calendar app, find the private iCalendar address: Google Calendar - Settings, the
   calendar, "Secret address in iCal format"; Outlook - Settings, Calendar, Shared calendars,
   "Publish a calendar", the ICS link; Apple iCloud - share the calendar as public and copy the link.
2. In Trinity, open this agent, Credentials, and set `CALENDAR_READ_CREDENTIAL` to that address.
3. Restart the agent if Trinity asks, then say "check my connections".

## mail

Only Google mailboxes (Gmail in Google Workspace) are supported, read-only, through one script.

1. A Google Workspace administrator creates a service account for this agent alone, enables the
   Gmail API, and grants it domain-wide delegation with the single scope
   `https://www.googleapis.com/auth/gmail.readonly`. Say plainly: Google grants this for every
   mailbox in the domain; what keeps the agent to the person's own mailbox is its script, which
   reads only the one address in their profile.
2. In Trinity, set `MAILBOX_READ_CREDENTIAL` to the service account's JSON key.
3. Tell the agent your address; write it into `workspace/profile/connections.md` as one line
   `address: name@domain`, and a `Start from` date if they want older mail read (else from now on).
4. Install the script's two libraries once: `python3 -m pip install -r requirements.txt`.
5. Then "check my connections".

Mailbox not on Google: say it isn't supported yet, and that exporting emails (.eml) and dropping
them works just as well.

## check

Run what is set, never printing a value:

```bash
[ -n "$CALENDAR_READ_CREDENTIAL" ] && python3 scripts/calendar.py check
[ -n "$MAILBOX_READ_CREDENTIAL" ] && python3 scripts/mail.py check
```

Translate each result to one plain line: connected / not set / the problem and its fix (for
mail.py: 3 a library missing - install requirements; 6 delegation not granted - the admin step;
14 no single `address:` line in the profile). Record `last_run_state` (`not_set_up` if the person
asked to check something that is not set, else `done`).
