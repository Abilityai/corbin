#!/usr/bin/env python3
"""Read the person's calendar from its private iCalendar (.ics) feed. Read-only by nature.

    python3 scripts/calendar.py check
    python3 scripts/calendar.py events --from YYYY-MM-DD --days N [--tz Area/City]
    python3 scripts/calendar.py --selftest

The feed address is the secret CALENDAR_READ_CREDENTIAL, taken from the environment only and
never printed. Output is JSON. Exit codes: 0 ok, 4 credential_missing, 8 feed_unreachable,
9 not_a_calendar. Standard library only. A repeating event is listed on its first date with
"repeats": true and its rule; it is not expanded.
"""
import datetime as dt
import json
import os
import sys
import urllib.request

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None


def fail(code, name, msg):
    print(json.dumps({"error": name, "message": msg}))
    return code


def fetch():
    url = os.environ.get("CALENDAR_READ_CREDENTIAL", "").strip()
    if not url:
        raise LookupError
    if url.startswith("webcal://"):
        url = "https://" + url[len("webcal://"):]
    req = urllib.request.Request(url, headers={"User-Agent": "chief-of-staff-calendar/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def unfold(text):
    out = []
    for line in text.replace("\r\n", "\n").split("\n"):
        if line[:1] in (" ", "\t") and out:
            out[-1] += line[1:]
        else:
            out.append(line)
    return out


def parse_dt(value, params, tz):
    allday = "VALUE=DATE" in params or (len(value) == 8 and value.isdigit())
    if allday:
        d = dt.datetime.strptime(value[:8], "%Y%m%d")
        return d.replace(tzinfo=tz), True
    zone = None
    for p in params.split(";"):
        if p.startswith("TZID=") and ZoneInfo:
            try:
                zone = ZoneInfo(p[5:].strip('"'))
            except Exception:
                zone = None
    if value.endswith("Z"):
        return dt.datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=dt.timezone.utc), False
    return dt.datetime.strptime(value[:15], "%Y%m%dT%H%M%S").replace(tzinfo=zone or tz), False


def parse(text, tz):
    lines = unfold(text)
    if not any(l.startswith("BEGIN:VCALENDAR") for l in lines[:5]):
        raise ValueError
    events, cur = [], None
    for line in lines:
        if line == "BEGIN:VEVENT":
            cur = {"attendees": []}
        elif line == "END:VEVENT" and cur is not None:
            events.append(cur)
            cur = None
        elif cur is not None and ":" in line:
            head, value = line.split(":", 1)
            name, _, params = head.partition(";")
            value = value.replace("\\n", "\n").replace("\\,", ",").replace("\\;", ";")
            if name in ("DTSTART", "DTEND"):
                cur[name.lower()], cur["all_day"] = parse_dt(value, params, tz)
            elif name == "SUMMARY":
                cur["title"] = value
            elif name == "LOCATION":
                cur["location"] = value
            elif name == "DESCRIPTION":
                cur["description"] = value[:1000]
            elif name == "RRULE":
                cur["repeats"], cur["rule"] = True, value
            elif name == "STATUS":
                cur["status"] = value
            elif name == "ATTENDEE":
                cn = next((p[3:].strip('"') for p in params.split(";") if p.startswith("CN=")), "")
                ps = next((p[9:] for p in params.split(";") if p.startswith("PARTSTAT=")), "")
                cur["attendees"].append({"name": cn, "email": value.replace("mailto:", "").replace("MAILTO:", ""),
                                         "answer": ps.lower()})
            elif name == "ORGANIZER":
                cur["organizer"] = value.replace("mailto:", "").replace("MAILTO:", "")
    return events


def main(argv):
    if argv[:1] == ["--selftest"]:
        sample = ("BEGIN:VCALENDAR\nBEGIN:VEVENT\nDTSTART:20260115T090000Z\nDTEND:20260115T093000Z\n"
                  "SUMMARY:Supplier review\nATTENDEE;CN=Ana;PARTSTAT=ACCEPTED:mailto:ana@example.com\n"
                  "END:VEVENT\nEND:VCALENDAR\n")
        ev = parse(sample, dt.timezone.utc)
        ok = ev and ev[0]["title"] == "Supplier review" and ev[0]["attendees"][0]["email"] == "ana@example.com"
        print("SELFTEST-OK" if ok else "SELFTEST-FAILED")
        return 0 if ok else 1
    if not argv or argv[0] not in ("check", "events"):
        print(__doc__)
        return 64
    args = dict(zip(argv[1::2], argv[2::2]))
    tz = dt.timezone.utc
    if args.get("--tz") and ZoneInfo:
        tz = ZoneInfo(args["--tz"])
    try:
        events = parse(fetch(), tz)
    except LookupError:
        return fail(4, "credential_missing", "CALENDAR_READ_CREDENTIAL is not set")
    except ValueError:
        return fail(9, "not_a_calendar", "the feed did not return an iCalendar file")
    except Exception as e:  # network, HTTP, TLS
        return fail(8, "feed_unreachable", type(e).__name__)
    if argv[0] == "check":
        print(json.dumps({"ok": True, "events_in_feed": len(events)}))
        return 0
    start = dt.datetime.strptime(args.get("--from", dt.date.today().isoformat()), "%Y-%m-%d").replace(tzinfo=tz)
    end = start + dt.timedelta(days=int(args.get("--days", "1")))
    picked = []
    for e in events:
        s = e.get("dtstart")
        if not s:
            continue
        if (start <= s < end) or (e.get("repeats") and s < end):
            row = dict(e, start=s.astimezone(tz).isoformat(), end=e["dtend"].astimezone(tz).isoformat() if e.get("dtend") else "")
            row.pop("dtstart", None)
            row.pop("dtend", None)
            picked.append(row)
    picked.sort(key=lambda r: r["start"])
    print(json.dumps({"from": start.isoformat(), "to": end.isoformat(), "events": picked}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
