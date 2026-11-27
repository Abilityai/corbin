#!/usr/bin/env python3
"""What a person dropped on the agent, and which of it is already handled.

Trinity saves files dropped in the Workspace under inbox/<who>/ and chat uploads under
uploads/<session>/. Both are kept out of git by the platform. This script lists them and keeps
one ledger, workspace/ledger/intake.jsonl, so a file is handled once even when the same file
is dropped twice (it is matched by its content's sha256, not its name).

    python3 scripts/inbox.py new            files not yet in the ledger, oldest first (JSON)
    python3 scripts/inbox.py all            every file, with its ledger row when it has one
    python3 scripts/inbox.py mark FILE --as KIND --result TEXT
                                            add one ledger row (KIND: transcript | email |
                                            notes | document | skipped | failed)
Standard library only. Reads nothing inside the files.
"""
import datetime
import hashlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DROP_DIRS = ("inbox", "uploads")
LEDGER = os.path.join(ROOT, "workspace", "ledger", "intake.jsonl")
SKIP = {".DS_Store", "Thumbs.db"}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ledger():
    rows = {}
    if os.path.exists(LEDGER):
        with open(LEDGER, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    row = json.loads(line)
                    rows[row["sha256"]] = row
    return rows


def files():
    out = []
    for d in DROP_DIRS:
        base = os.path.join(ROOT, d)
        if not os.path.isdir(base):
            continue
        for dirpath, _, names in os.walk(base):
            for n in names:
                if n in SKIP or n.startswith("."):
                    continue
                p = os.path.join(dirpath, n)
                rel = os.path.relpath(p, ROOT)
                parts = rel.split(os.sep)
                out.append({"path": rel, "from": parts[1] if len(parts) > 2 else "",
                            "modified": datetime.datetime.fromtimestamp(os.path.getmtime(p), datetime.timezone.utc)
                            .strftime("%Y-%m-%dT%H:%M:%SZ"), "sha256": sha256(p)})
    return sorted(out, key=lambda f: f["modified"])


def main(argv):
    if not argv or argv[0] not in ("new", "all", "mark"):
        print(__doc__)
        return 64
    seen = ledger()
    if argv[0] == "new":
        new = [f for f in files() if f["sha256"] not in seen]
        print(json.dumps({"new": new, "count": len(new)}, indent=1))
        return 0
    if argv[0] == "all":
        print(json.dumps([dict(f, ledger=seen.get(f["sha256"])) for f in files()], indent=1))
        return 0
    if len(argv) < 6 or argv[2] != "--as" or argv[4] != "--result":
        print("usage: inbox.py mark FILE --as KIND --result TEXT", file=sys.stderr)
        return 64
    path = os.path.join(ROOT, argv[1]) if not os.path.isabs(argv[1]) else argv[1]
    row = {"sha256": sha256(path), "path": os.path.relpath(path, ROOT), "as": argv[3], "result": argv[5],
           "at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    with open(LEDGER, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(json.dumps(row))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
