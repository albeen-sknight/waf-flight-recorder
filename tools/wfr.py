"""WAF Flight Recorder: shared helpers for the scenario runner and the tests.

A scenario is a YAML document describing ONE request to the lab and what the
WAF is expected to do with it. `send()` sends it and returns an `Outcome`
built from the ModSecurity audit log entry of that exact transaction
(matched via the X-WFR-Transaction response header = ModSecurity's
transaction id). The audit log, not the HTTP status alone, is the source of
truth for "what fired and why".

Safety: requests are only ever sent to the lab. The destination host must be
localhost, 127.0.0.1, the compose service name `waf`, or a host explicitly
allowed with ALLOW_DEMO_HOST (the private Cloudflare demo hostname).
"""
from __future__ import annotations

import json
import os
import re
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

import requests
import yaml

REPO = Path(__file__).resolve().parent.parent
BASE_URL = os.environ.get("WFR_BASE_URL", "http://localhost:8080")
AUDIT_LOG = Path(os.environ.get("WFR_AUDIT_LOG", REPO / "evidence" / "raw" / "audit.json"))
ALLOWED_HOSTS = {"localhost", "127.0.0.1", "waf"}
if os.environ.get("ALLOW_DEMO_HOST"):
    ALLOWED_HOSTS.add(os.environ["ALLOW_DEMO_HOST"].strip().lower())

RULE_ID_RE = re.compile(r'\[id "(\d+)"\]')
SCORE_RE = re.compile(r"Inbound Scores: blocking=(\d+), detection=(\d+)")
DATA_RE = re.compile(r'\[data "((?:[^"\\]|\\.)*)"\]')
MSG_RE = re.compile(r'\[msg "((?:[^"\\]|\\.)*)"\]')


class UnsafeTarget(Exception):
    """Raised when a scenario would send traffic outside the lab."""


def check_target(url: str) -> None:
    host = (urlsplit(url).hostname or "").lower()
    if host not in ALLOWED_HOSTS:
        raise UnsafeTarget(
            f"refusing to send lab traffic to {host!r}; allowed: {sorted(ALLOWED_HOSTS)}"
        )


@dataclass
class Match:
    rule_id: str
    msg: str
    data: str
    raw: str


@dataclass
class Outcome:
    status: int
    transaction_id: str
    intercepted: bool
    phase: int | None
    matches: list[Match] = field(default_factory=list)
    inbound_blocking_score: int | None = None
    inbound_detection_score: int | None = None
    entry: dict | None = None

    @property
    def decision(self) -> str:
        return "blocked" if self.intercepted else "allowed"

    @property
    def rule_ids(self) -> list[str]:
        return [m.rule_id for m in self.matches]

    def summary(self) -> str:
        ids = ", ".join(i for i in self.rule_ids if i != "980170") or "none"
        score = self.inbound_detection_score
        return (f"{self.decision.upper():8} status={self.status} rules=[{ids}] "
                f"inbound_score={score if score is not None else '-'} tx={self.transaction_id}")


def parse_entry(entry: dict) -> tuple[bool, int | None, list[Match], int | None, int | None]:
    audit = entry.get("audit_data", {})
    action = audit.get("action") or {}
    matches, blocking, detection = [], None, None
    for raw in audit.get("messages", []):
        rid = RULE_ID_RE.search(raw)
        msg = MSG_RE.search(raw)
        data = DATA_RE.search(raw)
        matches.append(Match(rid.group(1) if rid else "?",
                             msg.group(1) if msg else "",
                             data.group(1) if data else "", raw))
        score = SCORE_RE.search(raw)
        if score:
            blocking, detection = int(score.group(1)), int(score.group(2))
    return bool(action.get("intercepted")), action.get("phase"), matches, blocking, detection


def find_audit_entry(transaction_id: str, timeout: float = 5.0) -> dict | None:
    """Return the audit log entry for a transaction id (the log is JSON lines)."""
    deadline = time.time() + timeout
    needle = f'"transaction_id":"{transaction_id}"'
    while time.time() < deadline:
        if AUDIT_LOG.exists():
            with AUDIT_LOG.open("r", encoding="utf-8", errors="replace") as fh:
                for line in reversed(fh.readlines()[-2000:]):
                    if needle in line.replace(" ", ""):
                        return json.loads(line)
        time.sleep(0.2)
    return None


def build_request(scenario: dict, base_url: str = BASE_URL) -> dict:
    req = scenario["request"]
    url = base_url.rstrip("/") + req.get("path", "/")
    headers = {"User-Agent": "Mozilla/5.0 (WFR lab test runner)", "Host": "localhost"}
    if urlsplit(base_url).hostname not in {"localhost", "127.0.0.1", "waf"}:
        headers.pop("Host")  # real hostname (demo): let requests set it
    headers.update(req.get("headers", {}) or {})
    headers["X-WFR-Scenario"] = scenario["id"]
    headers["X-WFR-Run"] = uuid.uuid4().hex[:12]
    kwargs = {"method": req.get("method", "GET"), "url": url, "headers": headers,
              "params": req.get("params"), "allow_redirects": False, "timeout": 15}
    if "json" in req:
        kwargs["json"] = req["json"]
    elif "data" in req:
        kwargs["data"] = req["data"]
    return kwargs


def send(scenario: dict, base_url: str = BASE_URL, extra_headers: dict | None = None) -> Outcome:
    kwargs = build_request(scenario, base_url)
    if extra_headers:
        kwargs["headers"].update(extra_headers)
    check_target(kwargs["url"])
    resp = requests.request(**kwargs)
    tx = resp.headers.get("X-WFR-Transaction", "")
    entry = find_audit_entry(tx) if tx else None
    if entry is None:
        return Outcome(resp.status_code, tx, intercepted=False, phase=None, entry=None)
    intercepted, phase, matches, blocking, detection = parse_entry(entry)
    # CRS rule 980170 reports scores only when a score was accumulated.
    blocking = 0 if blocking is None else blocking
    detection = 0 if detection is None else detection
    return Outcome(resp.status_code, tx, intercepted, phase, matches, blocking, detection, entry)


def load_scenarios(root: Path | None = None) -> list[dict]:
    root = root or REPO / "scenarios"
    out = []
    for path in sorted(root.rglob("*.yaml")):
        for doc in yaml.safe_load_all(path.read_text(encoding="utf-8")):
            if doc:
                doc["_file"] = str(path.relative_to(REPO))
                out.append(doc)
    return out


def check_expectations(scenario: dict, outcome: Outcome) -> list[str]:
    """Compare an outcome with scenario['expected']; return a list of failures."""
    exp = scenario.get("expected", {})
    problems = []
    if outcome.entry is None:
        problems.append("no audit-log entry found for this transaction")
    if "decision" in exp and outcome.decision != exp["decision"]:
        problems.append(f"decision {outcome.decision} != expected {exp['decision']}")
    if "status" in exp and outcome.status != exp["status"]:
        problems.append(f"HTTP status {outcome.status} != expected {exp['status']}")
    for rid in exp.get("rule_ids", []) or []:
        if str(rid) not in outcome.rule_ids:
            problems.append(f"expected rule {rid} to match; matched {outcome.rule_ids}")
    for rid in exp.get("not_rule_ids", []) or []:
        if str(rid) in outcome.rule_ids:
            problems.append(f"rule {rid} matched but must not")
    if "only_rule_ids" in exp:
        extra = set(outcome.rule_ids) - {str(r) for r in exp["only_rule_ids"]} - {"980170"}
        if extra:
            problems.append(f"unexpected extra rules matched: {sorted(extra)}")
    if "intercepted_by" in exp:
        blockers = [m.rule_id for m in outcome.matches if m.raw.startswith("Access denied")]
        if str(exp["intercepted_by"]) not in blockers:
            problems.append(f"expected rule {exp['intercepted_by']} to deny; denying rules: {blockers}")
    if "inbound_score" in exp and outcome.inbound_detection_score != exp["inbound_score"]:
        problems.append(f"inbound score {outcome.inbound_detection_score} != {exp['inbound_score']}")
    if "min_inbound_score" in exp and (outcome.inbound_detection_score or 0) < exp["min_inbound_score"]:
        problems.append(f"inbound score {outcome.inbound_detection_score} < {exp['min_inbound_score']}")
    return problems
