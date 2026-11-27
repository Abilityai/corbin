#!/usr/bin/env python3
"""Turn one file a person dropped on the agent into plain text, with no network and no key.

    python3 scripts/extract_text.py <file> [--max-chars N]
    python3 scripts/extract_text.py --selftest

Prints one JSON object: {"path", "kind", "chars", "truncated", "headers", "attachments", "text"}
or, when the file cannot be read, {"path", "kind", "error"} and exit code 2.

kind is one of: email (.eml), transcript (.vtt, .srt), document (.txt, .md, .pdf, .docx, .html),
unsupported. Nothing is opened from inside the file: links stay text, attachments of an .eml are
listed by name and never saved. Python standard library only; a PDF is read with `pdftotext`
when it is installed, else with the `pypdf` library when it is installed, else refused by name.
"""
import email
import email.policy
import html
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile

DEFAULT_MAX = 400_000


def _strip_html(raw):
    raw = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", raw)
    raw = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</li>|</tr>|</h[1-6]>", "\n", raw)
    raw = re.sub(r"<[^>]+>", " ", raw)
    raw = html.unescape(raw)
    return re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n\n", raw)).strip()


def read_eml(path):
    with open(path, "rb") as fh:
        msg = email.message_from_binary_file(fh, policy=email.policy.default)
    headers = {k: str(msg.get(k, "")) for k in ("From", "To", "Cc", "Date", "Subject", "Message-ID",
                                                    "In-Reply-To", "References")}
    body, attachments = None, []
    for part in msg.walk():
        if part.is_multipart():
            continue
        name = part.get_filename()
        if name or part.get_content_disposition() == "attachment":
            attachments.append(name or "(unnamed)")
            continue
        ctype = part.get_content_type()
        if ctype == "text/plain" and body is None:
            body = part.get_content()
        elif ctype == "text/html" and body is None:
            body = _strip_html(part.get_content())
    return headers, attachments, (body or "")


def read_subtitles(raw):
    out, last = [], None
    for line in raw.splitlines():
        s = line.strip()
        if not s or s == "WEBVTT" or s.isdigit() or "-->" in s or s.startswith(("NOTE", "STYLE")):
            continue
        s = re.sub(r"<v\s+([^>]+)>", r"\1: ", s)
        s = re.sub(r"<[^>]+>", "", s)
        if s != last:
            out.append(s)
        last = s
    return "\n".join(out)


def read_docx(path):
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8", "replace")
    xml = re.sub(r"</w:p>", "\n", xml)
    return html.unescape(re.sub(r"<[^>]+>", "", xml)).strip()


def read_pdf(path):
    if shutil.which("pdftotext"):
        r = subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True, timeout=120)
        if r.returncode == 0:
            return r.stdout.decode("utf-8", "replace")
    try:
        import pypdf  # optional
    except ImportError:
        raise ValueError("pdf_reader_missing: install poppler-utils (pdftotext) or the pypdf library")
    reader = pypdf.PdfReader(path)
    return "\n".join((p.extract_text() or "") for p in reader.pages)


def extract(path, max_chars=DEFAULT_MAX):
    ext = os.path.splitext(path)[1].lower()
    result = {"path": path, "headers": {}, "attachments": []}
    try:
        if ext == ".eml":
            result["kind"] = "email"
            result["headers"], result["attachments"], text = read_eml(path)
        elif ext in (".vtt", ".srt"):
            result["kind"] = "transcript"
            with open(path, encoding="utf-8", errors="replace") as fh:
                text = read_subtitles(fh.read())
        elif ext in (".txt", ".md", ".markdown", ".text", ""):
            result["kind"] = "document"
            with open(path, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        elif ext in (".html", ".htm"):
            result["kind"] = "document"
            with open(path, encoding="utf-8", errors="replace") as fh:
                text = _strip_html(fh.read())
        elif ext == ".docx":
            result["kind"] = "document"
            text = read_docx(path)
        elif ext == ".pdf":
            result["kind"] = "document"
            text = read_pdf(path)
        else:
            return {"path": path, "kind": "unsupported", "error": f"unsupported_type: {ext or 'no extension'}"}
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, subprocess.SubprocessError) as e:
        return {"path": path, "kind": result.get("kind", "unknown"), "error": str(e)}
    text = text.replace("\r\n", "\n").strip()
    result["chars"] = len(text)
    result["truncated"] = len(text) > max_chars
    result["text"] = text[:max_chars]
    if not text:
        result["error"] = "empty: no text could be read (a scan or an image needs OCR, which this script does not do)"
    return result


def selftest():
    import tempfile
    d = tempfile.mkdtemp(dir=os.environ.get("TMPDIR"))
    eml = os.path.join(d, "a.eml")
    with open(eml, "w") as fh:
        fh.write("From: A <a@example.com>\nTo: b@example.com\nSubject: Quote\nMessage-ID: <1@x>\n"
                 "Content-Type: text/plain\n\nCan you send the revised quote by Friday?\n")
    vtt = os.path.join(d, "b.vtt")
    with open(vtt, "w") as fh:
        fh.write("WEBVTT\n\n1\n00:00:01.000 --> 00:00:02.000\n<v Ana>We agreed to ship on the 12th.\n")
    checks = [
        ("an .eml gives headers and body", lambda: (lambda r: r["headers"]["Subject"] == "Quote" and "Friday" in r["text"])(extract(eml))),
        ("a .vtt keeps the speaker", lambda: "Ana: We agreed" in extract(vtt)["text"]),
        ("an unknown type is refused by name", lambda: extract(os.path.join(d, "x.xyz"))["kind"] == "unsupported"),
    ]
    bad = 0
    for name, fn in checks:
        ok = bool(fn())
        bad += not ok
        print(("ok   " if ok else "FAIL ") + name)
    shutil.rmtree(d, ignore_errors=True)
    print("SELFTEST-OK" if not bad else "SELFTEST-FAILED")
    return 1 if bad else 0


def main(argv):
    if argv[:1] == ["--selftest"]:
        return selftest()
    if not argv:
        print(__doc__)
        return 64
    max_chars = DEFAULT_MAX
    if "--max-chars" in argv:
        i = argv.index("--max-chars")
        max_chars = int(argv[i + 1])
        argv = argv[:i] + argv[i + 2:]
    r = extract(argv[0], max_chars)
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 2 if "error" in r else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
