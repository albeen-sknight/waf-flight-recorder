#!/usr/bin/env python3
"""Summarise ModSecurity JSON audit-log entries, one line per transaction.

    python3 tools/summarize_audit.py                 # last 20 transactions
    python3 tools/summarize_audit.py -n 50
    python3 tools/summarize_audit.py --tx <transaction id>   # full detail for one
    python3 tools/summarize_audit.py --sanitize <transaction id> > evidence/sanitized-samples/x.json

--sanitize drops cookies/authorization headers and replaces client IPs, so an
entry can be committed as evidence.
"""
import argparse
import json
import sys

import wfr

SENSITIVE_HEADERS = {"cookie", "authorization", "cf-access-client-secret",
                     "cf-access-client-id", "x-forwarded-for", "cf-connecting-ip"}


def load(n: int | None = None) -> list[dict]:
    lines = wfr.AUDIT_LOG.read_text(encoding="utf-8", errors="replace").splitlines()
    if n:
        lines = lines[-n:]
    return [json.loads(line) for line in lines if line.strip()]


def one_line(entry: dict) -> str:
    intercepted, phase, matches, _, detection = wfr.parse_entry(entry)
    req = entry.get("request", {})
    ids = ",".join(m.rule_id for m in matches if m.rule_id != "980170") or "-"
    return (f"{entry['transaction']['transaction_id']}  "
            f"{'BLOCK' if intercepted else 'allow'} p{phase or '-'}  "
            f"score={detection if detection is not None else 0:<3} "
            f"{entry.get('response', {}).get('status', '?')}  "
            f"{req.get('request_line', '')[:70]:<70}  rules={ids}")


def sanitize(entry: dict) -> dict:
    entry = json.loads(json.dumps(entry))
    entry["transaction"]["remote_address"] = "192.0.2.10"  # TEST-NET-1 placeholder
    for section in ("request", "response"):
        hdrs = entry.get(section, {}).get("headers", {})
        for k in list(hdrs):
            if k.lower() in SENSITIVE_HEADERS:
                hdrs[k] = "[redacted]"
    return entry


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, default=20)
    ap.add_argument("--tx")
    ap.add_argument("--sanitize")
    args = ap.parse_args()
    if args.tx or args.sanitize:
        tx = args.tx or args.sanitize
        entry = next((e for e in load() if e["transaction"]["transaction_id"] == tx), None)
        if not entry:
            print(f"transaction {tx} not found", file=sys.stderr)
            return 1
        print(json.dumps(sanitize(entry) if args.sanitize else entry, indent=2))
        return 0
    for entry in load(args.n):
        print(one_line(entry))
    return 0


if __name__ == "__main__":
    sys.exit(main())
