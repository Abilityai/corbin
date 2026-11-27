# What is connected (optional)

Nothing here is needed: the agent works from files you drop on it. Fill this in only if you
connect a mailbox or a calendar. Ask the agent "how do I connect my email?" and it will walk
you through it. Never write a password, a key or a feed address here: those go into the agent's
credentials, by name, in the Trinity Credentials tab.

## Calendar

Read as a private iCalendar (.ics) feed; the feed address goes into CALENDAR_READ_CREDENTIAL.

Example: calendar: work calendar, iCalendar feed (set up 2026-01-15)

## Mailbox

Read through the Gmail API only, read-only. The service-account key goes into
MAILBOX_READ_CREDENTIAL. Write the address of your own mailbox once, on a line of its own, as
`address: name@domain`. The mail script reads that line and acts as no other address.

Example: address: person@example.com

## Start from

The first day mail may be read from. Blank means the first run reads nothing and starts from now.

Example: 2026-01-01
