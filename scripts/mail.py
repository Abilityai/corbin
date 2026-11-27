#!/usr/bin/env python3
"""The one way this agent touches mail: the Gmail API, and nothing else.

Sign-in: a Google service-account key that a Google Workspace administrator has allowed
to act as the mailbox (domain-wide delegation). The key's JSON is the secret. It is taken
from the environment, never from an argument, and is never printed or written anywhere:

    MAILBOX_READ_CREDENTIAL   every command      scope gmail.readonly

The variable holds the key's JSON itself, or the path of a file that holds it.

The mailbox address is never an argument. Google gives a key's access for every mailbox in
the domain, not for one, so this tool reads the one address it may act as from the agent's
own profile file, workspace/profile/connections.md, and takes no other: the one line written
"address: name@domain" (a line that starts with "Example" does not count). No such line, or
more than one, and nothing is read or sent.

Anything that came from outside (an address, a subject, a Message-ID header) is never put on
the command line: it goes into a JSON file, written as a file, that the command reads. The
command line holds days, numbers, file paths and ids this tool printed.

    python3 scripts/mail.py check
    python3 scripts/mail.py list  [--folder inbox|sent|any] [--after WHEN] [--before WHEN]
                                  [--max N] [--newest-first] [--known FILE] [--filter-file FILE]
    python3 scripts/mail.py get   MAIL_ID
    python3 scripts/mail.py --selftest        (offline: no network, no credential, no library)

check  one read of the mailbox's profile: proves the sign-in works. Prints no mail.
list   headers only, as JSON, oldest first. WHEN is a day (YYYY-MM-DD, from 00:00 UTC) or a
       time (YYYY-MM-DDTHH:MM:SSZ), compared with the time the mail service received the
       message, never the date written in it. --after includes that moment, --before does
       not. --known FILE leaves out every message whose id stands in that JSON file as a
       "mail_id" value. "more": true says more messages match than were returned;
       "matching" is how many match in all, when that is known.
       --filter-file FILE narrows the list: a JSON object with any of "with" (only mail to
       or from that address), "thread" (only that thread_id) and "message_id" (only the
       message with that Message-ID header).
get    one message as JSON: headers, the plain-text body and the names of its attachments.
       No attachment is downloaded.

There is no command that sends, changes, labels, marks as read, moves or deletes anything,
and the one scope asked for cannot do any of it.

Exit codes (one line on standard error says which, as "mail.py: <name>: <what>"):
     0  done
     2  usage                 wrong arguments; nothing was done
     3  dependencies_missing  the libraries in requirements.txt are not installed
     4  credential_missing    the variable is not set, or names a file that is not there
     5  credential_not_json   the value is not the JSON of a service-account key
     6  delegation_refused    Google refused this key for this mailbox or scope (403)
     7  mailbox_not_found     no Google mailbox with this address
     8  rate_limited          the mail service says too many requests; try later
     9  message_not_found     no such message or thread in this mailbox
    10  service_error         network, time-out or an error of the mail service
    12  credential_refused    Google does not accept this key (revoked, deleted, disabled)
    13  window_too_large      more messages match than can be put in order; give a later --after
    14  mailbox_not_set       the profile file does not hold exactly one "address:" line
"""
import argparse
import base64
import datetime
import html.parser
import json
import os
import re
import sys

API = "https://gmail.googleapis.com/gmail/v1/users/me"
MAILBOX_FILE = "workspace/profile/connections.md"
READ_ENV = "MAILBOX_READ_CREDENTIAL"
READ_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
HEADERS = ("From", "To", "Cc", "Reply-To", "Subject", "Date", "Message-ID", "In-Reply-To", "References")
FOLDER_LABEL = {"inbox": "INBOX", "sent": "SENT"}
MAX_LIST = 500
MAX_ORDERED = 5000
BODY_LIMIT = 100000
TIMEOUT = 30

CODES = {"usage": 2, "dependencies_missing": 3, "credential_missing": 4, "credential_not_json": 5,
         "delegation_refused": 6, "mailbox_not_found": 7, "rate_limited": 8, "message_not_found": 9,
         "service_error": 10, "credential_refused": 12, "window_too_large": 13, "mailbox_not_set": 14}
RATE_REASONS = ("ratelimitexceeded", "userratelimitexceeded", "dailylimitexceeded", "quotaexceeded",
                "resource_exhausted")


class MailError(Exception):
    def __init__(self, kind, text):
        super().__init__(text)
        self.name, self.text, self.code = kind, " ".join(str(text).split()), CODES[kind]


# --- the credential: read from the environment, never shown ---------------------------------

def load_key(env_name, environ=None):
    """The service-account key as a dict. No message of this function holds any part of it."""
    value = ((os.environ if environ is None else environ).get(env_name) or "").strip()
    if not value:
        raise MailError("credential_missing", f"{env_name} is not set")
    if not value.startswith("{"):
        try:
            with open(os.path.expanduser(value), encoding="utf-8") as fh:
                value = fh.read().strip()
        except (OSError, UnicodeDecodeError, ValueError):
            raise MailError("credential_missing", f"{env_name} is neither JSON nor the path of a readable file") from None
    try:
        info = json.loads(value)
    except ValueError:
        raise MailError("credential_not_json", f"{env_name} does not hold valid JSON") from None
    if not isinstance(info, dict) or info.get("type") != "service_account" or not info.get("private_key") \
            or not info.get("client_email"):
        raise MailError("credential_not_json", f"{env_name} holds JSON that is not a service-account key")
    return info


def access_token(env_name, scope, mailbox):
    info = load_key(env_name)
    try:
        import requests  # noqa: F401  (the transport google-auth uses)
        from google.auth import exceptions as gexc
        from google.auth.transport.requests import Request
        from google.oauth2 import service_account
    except ImportError as e:
        raise MailError("dependencies_missing", f"{e.name or 'a library'} is not installed: "
                        "python3 -m pip install -r requirements.txt") from None
    try:
        creds = service_account.Credentials.from_service_account_info(info, scopes=[scope], subject=mailbox)
    except Exception:
        raise MailError("credential_not_json", f"{env_name} holds a service-account key that cannot be used") from None
    try:
        creds.refresh(Request())
    except gexc.RefreshError as e:
        raise classify_refresh(str(e), mailbox, scope) from None
    except Exception as e:
        raise MailError("service_error", f"no answer from the sign-in service ({e.__class__.__name__})") from None
    return creds.token


def classify_refresh(text, mailbox, scope):
    t = text.lower()
    short = scope.rsplit("/", 1)[-1]
    if "invalid_grant" in t and ("invalid email" in t or "user id" in t):
        return MailError("mailbox_not_found", f"Google knows no mailbox {mailbox}")
    if "unauthorized_client" in t or "access_denied" in t:
        return MailError("delegation_refused", f"the key is not allowed to act as {mailbox} with {short}: a Google "
                         "Workspace administrator must allow it (domain-wide delegation)")
    if "invalid_grant" in t or "invalid_client" in t or "disabled" in t or "deleted" in t:
        return MailError("credential_refused", "Google does not accept this key (revoked, deleted or disabled, "
                         "or this machine's clock is wrong)")
    return MailError("service_error", "the sign-in service refused the request without a reason this tool knows")


# --- the mail service ------------------------------------------------------------------------

def classify_http(status, payload, what):
    err = payload.get("error") if isinstance(payload, dict) else None
    err = err if isinstance(err, dict) else {}
    msg = " ".join(str(err.get("message") or "").split())[:200]
    reasons = " ".join(str(x.get("reason") or "") for x in err.get("errors") or [] if isinstance(x, dict))
    low = (reasons + " " + str(err.get("status") or "") + " " + msg).lower()
    if status == 429 or (status == 403 and any(r in low for r in RATE_REASONS)):
        return MailError("rate_limited", "the mail service says too many requests; try again later")
    if status == 401:
        return MailError("credential_refused", "the mail service did not accept the sign-in")
    if status == 403:
        return MailError("delegation_refused", f"not allowed (403): {msg or 'no reason given'}")
    if status == 404:
        return MailError("message_not_found", f"{what} is not in this mailbox")
    if status == 400 and ("mail service not enabled" in low or "failedprecondition" in low or "failed_precondition" in low):
        return MailError("mailbox_not_found", "this address has no Google mailbox")
    if status == 400:
        return MailError("usage", f"the mail service refused the request (400): {msg or 'no reason given'}")
    return MailError("service_error", f"the mail service answered {status}")


def answer(r, what):
    try:
        payload = r.json()
    except ValueError:
        payload = None
    if 200 <= r.status_code < 300 and isinstance(payload, dict):
        return payload, None
    return payload, classify_http(r.status_code, payload, what)


def call(token, path, params=None, what="it"):
    """One read of the mail service. This function can only GET."""
    import requests
    try:
        r = requests.get(API + path, params=params, timeout=TIMEOUT,
                         headers={"Authorization": "Bearer " + token, "Accept": "application/json"})
    except requests.RequestException as e:
        raise MailError("service_error", f"no answer from the mail service ({e.__class__.__name__})") from None
    payload, err = answer(r, what)
    if err:
        raise err
    return payload


# --- reading a message as data ----------------------------------------------------------------

class _Text(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.out, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "head"):
            self.skip += 1
        elif tag in ("br", "p", "div", "tr", "li"):
            self.out.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "head") and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            self.out.append(data)


def html_to_text(text):
    p = _Text()
    try:
        p.feed(text)
        p.close()
    except Exception:
        return ""
    return re.sub(r"\n\s*\n\s*", "\n\n", "".join(p.out)).strip()


def _decode(data):
    try:
        return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("utf-8", "replace")
    except (ValueError, TypeError):
        return ""


def header_map(payload):
    out = {}
    for h in (payload or {}).get("headers") or []:
        out.setdefault(str(h.get("name", "")).lower(), str(h.get("value", "")))
    return out


def when(ms):
    try:
        return datetime.datetime.fromtimestamp(int(ms) / 1000, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError, OverflowError, OSError):
        return ""


def summary(msg):
    """Headers only: what `list` prints for one message."""
    h = header_map(msg.get("payload"))
    labels = msg.get("labelIds") or []
    return {"mail_id": msg.get("id", ""), "thread_id": msg.get("threadId", ""),
            "message_id": h.get("message-id", ""), "in_reply_to": h.get("in-reply-to", ""),
            "references": h.get("references", ""), "received": when(msg.get("internalDate")),
            "date": h.get("date", ""), "from": h.get("from", ""), "to": h.get("to", ""), "cc": h.get("cc", ""),
            "reply_to": h.get("reply-to", ""), "subject": h.get("subject", ""),
            "folders": [n for n, lab in (("inbox", "INBOX"), ("sent", "SENT"), ("draft", "DRAFT")) if lab in labels]}


def parse_message(msg):
    """Headers, plain-text body and attachment names: what `get` prints."""
    plain, rich, names = [], [], []

    def walk(part):
        name = part.get("filename") or ""
        if name:
            names.append(name)
        else:
            data = (part.get("body") or {}).get("data")
            mime = part.get("mimeType", "")
            if data and mime == "text/plain":
                plain.append(_decode(data))
            elif data and mime == "text/html":
                rich.append(_decode(data))
        for sub in part.get("parts") or []:
            walk(sub)

    walk(msg.get("payload") or {})
    body = "\n".join(plain).strip()
    from_html = False
    if not body and rich:
        body, from_html = html_to_text("\n".join(rich)), True
    out = summary(msg)
    out.update({"body": body[:BODY_LIMIT], "body_truncated": len(body) > BODY_LIMIT,
                "body_from_html": from_html, "attachments": names})
    return out


# --- arguments --------------------------------------------------------------------------------

def parse_when(text):
    t = text.strip()
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", t):
            d = datetime.datetime.strptime(t, "%Y-%m-%d")
        else:
            d = datetime.datetime.fromisoformat(t[:-1] + "+00:00" if t.endswith(("Z", "z")) else t)
    except ValueError:
        raise MailError("usage", f"`{text}` is not a day (YYYY-MM-DD) or a time (YYYY-MM-DDTHH:MM:SSZ)") from None
    if d.tzinfo is None:
        d = d.replace(tzinfo=datetime.timezone.utc)
    return int(d.timestamp() * 1000)


def address(text):
    t = text.strip()
    if not re.fullmatch(r"[^\s@<>(){}\[\]\",;:\\]+@[^\s@<>(){}\[\]\",;:\\]+\.[^\s@<>(){}\[\]\",;:\\]+", t):
        raise MailError("usage", "an address must be one plain address, name@domain")
    return t


ADDRESS_IN_TEXT = re.compile(r"[^\s@<>(){}\[\]\",;:\\]+@[^\s@<>(){}\[\]\",;:\\]+\.[A-Za-z0-9-]+")


def parse_mailbox(text):
    """The one address this agent may act as: the single `address:` line of its profile file."""
    found = []
    for line in text.splitlines():
        t = line.strip().lstrip("-*").strip()
        if t.lower().startswith("example"):
            continue
        m = re.match(r"address\s*:(.*)", t, re.I)
        if m:
            found.append(ADDRESS_IN_TEXT.findall(m.group(1)))
    if not found:
        raise MailError("mailbox_not_set", f"{MAILBOX_FILE} holds no `address:` line (an Example line does not count)")
    if len(found) > 1 or len(found[0]) != 1:
        raise MailError("mailbox_not_set", f"{MAILBOX_FILE} must hold exactly one `address:` line with exactly one "
                        "address; it holds more, or none that can be read")
    return address(found[0][0])


def mailbox_address():
    """Read from the agent's own profile file, next to this script's folder. There is no argument for it."""
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), *MAILBOX_FILE.split("/"))
    try:
        with open(path, encoding="utf-8") as fh:
            return parse_mailbox(fh.read())
    except (OSError, UnicodeDecodeError):
        raise MailError("mailbox_not_set", f"{MAILBOX_FILE} cannot be read") from None


def path_id(text, what):
    """An id that becomes part of a request's path: the mail service's own ids, and nothing else."""
    t = text.strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", t):
        raise MailError("usage", f"{what} must be an id as this tool printed it (letters, digits, - and _)")
    return t


def token_arg(text, what):
    t = text.strip().strip("<>")
    if not t or re.search(r"[\s{}()\"]", t):
        raise MailError("usage", f"{what} must be one id with no spaces")
    return t


def load_known(path):
    if not path or not os.path.exists(path):
        return set()
    try:
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, ValueError):
        raise MailError("usage", "the --known file cannot be read as JSON") from None
    found = set()

    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if k == "mail_id" and isinstance(v, str):
                    found.add(v)
                else:
                    walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(doc)
    return found


def read_object(path, what, allowed):
    """A JSON object from a file the agent wrote: where everything from outside travels."""
    try:
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, ValueError):
        raise MailError("usage", f"the {what} cannot be read as JSON") from None
    if not isinstance(doc, dict) or any(k not in allowed for k in doc) \
            or any(not isinstance(v, str) for v in doc.values()):
        raise MailError("usage", f"the {what} must be one JSON object with text values, keys: " + ", ".join(allowed))
    return doc


def build_query(folder, after_ms, before_ms, with_addr, message_id):
    """The search sent to the mail service; (params without paging)."""
    q = []
    if after_ms is not None:
        q.append(f"after:{after_ms // 1000}")
    if before_ms is not None:
        q.append(f"before:{-(-before_ms // 1000)}")
    if with_addr:
        q.append("{" + f"from:{with_addr} to:{with_addr} cc:{with_addr}" + "}")
    if message_id:
        q.append(f"rfc822msgid:{message_id}")
    params = {}
    if folder in FOLDER_LABEL:
        params["labelIds"] = FOLDER_LABEL[folder]
    else:
        q.append("-in:draft")
    if q:
        params["q"] = " ".join(q)
    return params


def in_window(msg, folder, after_ms, before_ms, known):
    labels = msg.get("labelIds") or []
    try:
        at = int(msg.get("internalDate"))
    except (TypeError, ValueError):
        at = None
    if msg.get("id") in known or "DRAFT" in labels and folder != "sent" or "SPAM" in labels or "TRASH" in labels:
        return False
    if folder in FOLDER_LABEL and FOLDER_LABEL[folder] not in labels:
        return False
    if at is not None and after_ms is not None and at < after_ms:
        return False
    if at is not None and before_ms is not None and at >= before_ms:
        return False
    return True


def parser():
    p = argparse.ArgumentParser(prog="mail.py", formatter_class=argparse.RawDescriptionHelpFormatter,
                                epilog=__doc__.split("\n\n", 1)[1],
                                description="Read a Google mailbox through the Gmail API"
                                ". The key comes from the environment, never from an argument.")
    p.add_argument("--selftest", action="store_true", help="run the offline checks and exit")
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("check", help="prove the read sign-in works (gmail.readonly)")
    c = sub.add_parser("list", help="headers of messages, as JSON (gmail.readonly)")
    c.add_argument("--folder", choices=("inbox", "sent", "any"), default="inbox")
    c.add_argument("--after", help="received at or after this day or time (UTC)")
    c.add_argument("--before", help="received before this day or time (UTC)")
    c.add_argument("--max", type=int, default=30, help=f"at most this many (default 30, never more than {MAX_LIST})")
    c.add_argument("--newest-first", action="store_true", help="newest first (default: oldest first)")
    c.add_argument("--known", help="a JSON file; messages whose id stands in it as a mail_id value are left out")
    c.add_argument("--filter-file", help='a JSON file with any of "with", "thread", "message_id"')
    c = sub.add_parser("get", help="one message: headers, plain text, attachment names (gmail.readonly)")
    c.add_argument("mail_id")
    return p


# --- commands ---------------------------------------------------------------------------------

def cmd_check(a):
    mailbox = mailbox_address()
    token = access_token(READ_ENV, READ_SCOPE, mailbox)
    prof = call(token, "/profile", what="the mailbox")
    return {"ok": True, "mailbox": prof.get("emailAddress", mailbox), "scope": "gmail.readonly"}


def cmd_list(a):
    mailbox = mailbox_address()
    if not 1 <= a.max <= MAX_LIST:
        raise MailError("usage", f"--max must be between 1 and {MAX_LIST}")
    after_ms = parse_when(a.after) if a.after else None
    before_ms = parse_when(a.before) if a.before else None
    f = read_object(a.filter_file, "--filter-file", ("with", "thread", "message_id")) if a.filter_file else {}
    with_addr = address(f["with"]) if f.get("with") else None
    message_id = token_arg(f["message_id"], "message_id") if f.get("message_id") else None
    thread = path_id(f["thread"], "thread") if f.get("thread") else None
    known = load_known(a.known)
    token = access_token(READ_ENV, READ_SCOPE, mailbox)
    meta = [("format", "metadata")] + [("metadataHeaders", h) for h in HEADERS]
    more, matching = False, None
    if thread:
        t = call(token, "/threads/" + thread, params=meta, what="the thread")
        msgs = [m for m in t.get("messages") or [] if in_window(m, a.folder, after_ms, before_ms, known)]
        if with_addr:
            w = with_addr.lower()
            msgs = [m for m in msgs if any(w in header_map(m.get("payload")).get(k, "").lower() for k in ("from", "to", "cc"))]
    else:
        params = build_query(a.folder, after_ms, before_ms, with_addr, message_id)
        params["maxResults"] = 500
        ids, page = [], None
        while True:
            if page:
                params["pageToken"] = page
            got = call(token, "/messages", params=params, what="the mailbox")
            ids += [m["id"] for m in got.get("messages") or [] if m.get("id") not in known]
            page = got.get("nextPageToken")
            if not page or (a.newest_first and len(ids) > a.max):
                break
            if len(ids) > MAX_ORDERED:
                raise MailError("window_too_large", f"more than {MAX_ORDERED} messages match; give a later --after, "
                                "or use --newest-first")
        if not a.newest_first:
            ids.reverse()
        more = len(ids) > a.max or bool(page)
        matching = None if page else len(ids)
        msgs = [call(token, "/messages/" + i, params=meta, what="a message") for i in ids[:a.max]]
        msgs = [m for m in msgs if in_window(m, a.folder, after_ms, before_ms, known)]
    msgs.sort(key=lambda m: int(m.get("internalDate") or 0), reverse=a.newest_first)
    if len(msgs) > a.max:
        msgs, more = msgs[:a.max], True
    return {"mailbox": mailbox, "folder": a.folder, "count": len(msgs), "more": more, "matching": matching,
            "messages": [summary(m) for m in msgs]}


def cmd_get(a):
    mailbox = mailbox_address()
    mail_id = path_id(a.mail_id, "the message id")
    token = access_token(READ_ENV, READ_SCOPE, mailbox)
    return parse_message(call(token, "/messages/" + mail_id, params={"format": "full"}, what="the message"))


# --- the offline self-test --------------------------------------------------------------------

def selftest():
    done = []

    def ok(name, cond):
        done.append(bool(cond))
        print(("ok   " if cond else "FAIL ") + name)

    def refused(name, fn, want):
        try:
            fn()
            ok(name, False)
        except MailError as e:
            ok(name, e.name == want)

    b64 = lambda s: base64.urlsafe_b64encode(s.encode()).decode().rstrip("=")  # noqa: E731
    canned = {"id": "m1", "threadId": "t1", "labelIds": ["INBOX", "UNREAD"], "internalDate": "1767261600000",
              "payload": {"mimeType": "multipart/mixed", "headers": [
                  {"name": "From", "value": "Sender <sender@elsewhere.example>"},
                  {"name": "To", "value": "hello@business.example"},
                  {"name": "Subject", "value": "Opening hours"},
                  {"name": "Message-Id", "value": "<abc@elsewhere.example>"},
                  {"name": "Date", "value": "Thu, 01 Jan 2026 10:00:00 +0000"}],
                  "parts": [
                      {"mimeType": "multipart/alternative", "parts": [
                          {"mimeType": "text/plain", "body": {"data": b64("Are you open on Sunday?")}},
                          {"mimeType": "text/html", "body": {"data": b64("<p>Are you open on <b>Sunday</b>?</p>")}}]},
                      {"mimeType": "application/pdf", "filename": "plan.pdf", "body": {"attachmentId": "a1"}}]}}
    m = parse_message(canned)
    ok("get: plain-text body, headers, received time",
       m["body"] == "Are you open on Sunday?" and m["subject"] == "Opening hours"
       and m["message_id"] == "<abc@elsewhere.example>" and m["received"] == "2026-01-01T10:00:00Z")
    ok("get: attachment named, not downloaded", m["attachments"] == ["plan.pdf"] and "a1" not in json.dumps(m))
    only_html = {"id": "m2", "payload": {"mimeType": "text/html", "headers": [],
                                         "body": {"data": b64("<style>x{}</style><p>Hello</p><p>there</p>")}}}
    h = parse_message(only_html)
    ok("get: a message with no plain text is read from its HTML", h["body_from_html"] and h["body"] == "Hello\nthere")
    ok("list: headers only, folder told from the labels",
       summary(canned)["folders"] == ["inbox"] and "body" not in summary(canned))

    refused("credential missing", lambda: load_key(READ_ENV, {}), "credential_missing")
    refused("credential names a file that is not there",
            lambda: load_key(READ_ENV, {READ_ENV: "/nonexistent/key.json"}), "credential_missing")
    refused("credential not valid JSON", lambda: load_key(READ_ENV, {READ_ENV: "{not json"}), "credential_not_json")
    refused("credential is JSON but no service-account key",
            lambda: load_key(READ_ENV, {READ_ENV: '{"type": "authorized_user"}'}), "credential_not_json")
    marker = "SELFTEST-PLACEHOLDER-NOT-A-KEY"
    try:
        load_key(READ_ENV, {READ_ENV: '{"type": "service_account", "private_key": "' + marker + '"}'})
        ok("an error never shows the credential", False)
    except MailError as e:
        ok("an error never shows the credential", marker not in e.text)

    args = parser().parse_args(["list", "--after", "2026-01-15", "--max", "30"])
    ok("arguments: list", args.cmd == "list" and args.max == 30 and args.folder == "inbox" and not args.newest_first)
    ok("arguments: a day and a time", parse_when("2026-01-15") == 1768435200000
       and parse_when("2026-01-15T00:00:01Z") == 1768435201000)
    import contextlib
    import io
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            parser().parse_args(["list", "--mailbox", "other@business.example"])
        ok("the mailbox address cannot be given as an argument", False)
    except SystemExit:
        ok("the mailbox address cannot be given as an argument", True)
    ok("the address is the one `address:` line of the profile file",
       parse_mailbox("## Address\n\nEXAMPLE: address: hello@business.example (x)\nExample: address: a@b.example\n"
                     "address: desk@business.example (source: office manager, 2026-01-15)\n\n## Other\nother@business.example\n")
       == "desk@business.example")
    refused("a profile file with no address is refused",
            lambda: parse_mailbox("## Address\n\nEXAMPLE: address: hello@business.example\n"), "mailbox_not_set")
    refused("a profile file with two addresses is refused",
            lambda: parse_mailbox("address: a@business.example\naddress: b@business.example\n"), "mailbox_not_set")
    refused("one line with two addresses is refused",
            lambda: parse_mailbox("address: a@business.example, b@business.example\n"), "mailbox_not_set")
    refused("an id that would change the request's path is refused", lambda: path_id("../lab" + "els?x=1", "the id"), "usage")
    ok("an id as the mail service gives it is taken", path_id("18c2f0a9b7d3e411", "the id") == "18c2f0a9b7d3e411"
       and token_arg("<abc+tag@elsewhere.example>", "message_id") == "abc+tag@elsewhere.example")
    refused("arguments: a date that is none", lambda: parse_when("yesterday"), "usage")
    refused("arguments: an address that is none", lambda: address("a@b.example, c@d.example"), "usage")
    q = build_query("inbox", 1768435200000, None, None, None)
    ok("list: the inbox from a day on", q == {"labelIds": "INBOX", "q": "after:1768435200"})
    q = build_query("any", None, None, "person@elsewhere.example", None)
    ok("list: mail with one address, drafts left out", q["q"].startswith("{from:person@elsewhere.example ")
       and q["q"].endswith("-in:draft") and "labelIds" not in q)
    ok("list: window by received time, known ids and drafts left out",
       in_window(canned, "inbox", 1767261600000, None, set()) and not in_window(canned, "inbox", 1767261600001, None, set())
       and not in_window(canned, "inbox", None, 1767261600000, set()) and not in_window(canned, "inbox", None, None, {"m1"})
       and not in_window(canned, "sent", None, None, set())
       and not in_window(dict(canned, labelIds=["DRAFT"]), "any", None, None, set()))

    e = classify_http(403, {"error": {"code": 403, "message": "Delegation denied", "errors": [{"reason": "forbidden"}]}}, "it")
    ok("403 is delegation refused", e.name == "delegation_refused" and e.code == 6)
    e = classify_http(403, {"error": {"errors": [{"reason": "rateLimitExceeded"}]}}, "it")
    ok("a rate limit is told apart, also as 403", e.name == "rate_limited" and classify_http(429, None, "it").name == "rate_limited")
    ok("no mailbox for the address", classify_http(400, {"error": {"status": "FAILED_PRECONDITION",
       "message": "Mail service not enabled"}}, "it").name == "mailbox_not_found"
       and classify_refresh("invalid_grant: Invalid email or User ID", "a@b.example", READ_SCOPE).name == "mailbox_not_found")
    ok("delegation refused at sign-in", classify_refresh("unauthorized_client: Client is unauthorized",
       "a@b.example", READ_SCOPE).name == "delegation_refused")
    ok("404 is message not found", classify_http(404, {}, "the message").name == "message_not_found")
    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    names = sorted(parser()._subparsers._group_actions[0].choices)
    ok("there is no command that sends", names == ["check", "get", "list"] and "requests.po" + "st" not in src
       and "gmail.se" + "nd" not in src)
    banned = ("/mod" + "ify", "/tr" + "ash", "/batch" + "Modify", "/batch" + "Delete", "/unt" + "rash", "gmail.mod" + "ify",
              "mail.goo" + "gle.com/", "/dra" + "fts", "/lab" + "els", "/attach" + "ments")
    ok("no request that changes, labels, moves or deletes, and no attachment download", not any(b in src for b in banned))

    good = all(done)
    print(f"SELFTEST-OK {len(done)} checks" if good else f"SELFTEST-FAILED {done.count(False)} of {len(done)}")
    return 0 if good else 1


def main(argv):
    p = parser()
    a = p.parse_args(argv)
    if a.selftest:
        return selftest()
    if not a.cmd:
        p.print_usage(sys.stderr)
        return 2
    try:
        result = globals()["cmd_" + a.cmd](a)
    except MailError as e:
        sys.stderr.write(f"mail.py: {e.name}: {e.text}\n")
        return e.code
    except Exception as e:  # never a traceback: it could show what a variable held
        sys.stderr.write(f"mail.py: service_error: unexpected {e.__class__.__name__}\n")
        return CODES["service_error"]
    print(json.dumps(result, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except ImportError:
        sys.stderr.write("mail.py: dependencies_missing: python3 -m pip install -r requirements.txt\n")
        sys.exit(CODES["dependencies_missing"])
