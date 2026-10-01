# How to read a ModSecurity transaction

Every request through the lab leaves exactly one line in `evidence/raw/audit.json`. That's `SecAuditEngine On` plus `SecAuditLogFormat JSON`. Here's a real one, taken apart: a textbook SQL injection string fired at Juice Shop's product search.

```
GET /rest/products/search?q=' OR 1=1--
```

Full entry, sanitized: [`evidence/sanitized-samples/phase1-crs-sqli-blocked.json`](../evidence/sanitized-samples/phase1-crs-sqli-blocked.json)

The one-line version (`python3 tools/summarize_audit.py`):

```
ar4djKPK1WHVNKMHG_yyEQAAAEI  BLOCK p2  score=5  403  GET /rest/products/search?q=%27%20OR%201%3D1-- HTTP/1.1  rules=942100,949110
```

## The parts (`SecAuditLogParts ABCFHZ`)

| Part | JSON key | What's in it | Why you care |
| --- | --- | --- | --- |
| A | `transaction` | time, **transaction_id**, client/server address | The id ties together the browser response, the access log and this entry. The lab sends it back as `X-WFR-Transaction`. |
| B | `request.request_line`, `request.headers` | exactly what the client sent | Raw input, before any transformation touches it. |
| C | `request.body` | the request body (POST/PUT) | Only there when there's a body. |
| F | `response.status`, `response.headers` | what the client got back | `403` here, from Apache's error page. Juice Shop never saw the request. |
| H | `audit_data` | rule messages, the action, timings, engine mode | The part that tells you what fired and why. |
| Z | — | end marker | — |

## Reading `audit_data` (part H)

### `messages`: one line per rule that matched

```
Warning. detected SQLi using libinjection with fingerprint 's&1c'
  [file ".../REQUEST-942-APPLICATION-ATTACK-SQLI.conf"] [line "66"] [id "942100"]
  [msg "SQL Injection Attack Detected via libinjection"]
  [data "Matched Data: s&1c found within ARGS:q: ' OR 1=1--"]
  [severity "CRITICAL"] [tag "attack-sqli"] [tag "paranoia-level/1"] ...
```

| Field | Value | Meaning |
| --- | --- | --- |
| `Warning.` | prefix | The rule **matched**. It didn't stop anything itself. |
| `id` | 942100 | CRS rule: SQL injection via libinjection. |
| `file` / `line` | REQUEST-942…, 66 | Where to go read the rule. That's your autopsy starting point. |
| `data` | `ARGS:q: ' OR 1=1--` | **Which variable** matched (`ARGS:q`, the `q` parameter) and its value. |
| `severity` | CRITICAL | In CRS anomaly mode, that's **5 points** on the inbound score. |
| `tag paranoia-level/1` | PL1 | Active at the lowest paranoia level. |

```
Access denied with code 403 (phase 2). Operator GE matched 5 at TX:blocking_inbound_anomaly_score.
  [id "949110"] [msg "Inbound Anomaly Score Exceeded (Total Score: 5)"]
```

This is the line that actually blocks. Note the wording: `Access denied`. Rule 942100 didn't block anything. Rule **949110**, CRS's blocking evaluation, added up the score (5), compared it with the threshold (5), and denied the request in **phase 2**.

> A rule matching and a request getting blocked are two separate events. 942100 matched. 949110 blocked.

```
Anomaly Scores: (Inbound Scores: blocking=5, detection=5, per_pl=5-0-0-0, threshold=5) ...
  (SQLI=5, XSS=0, ... COMBINED_SCORE=5)   [id "980170"]
```

Rule **980170** runs in phase 5 (logging) and reports the final tally: total inbound score, score per paranoia level, the threshold, and points per attack category. It never blocks anything.

### `action`

```json
"action": { "intercepted": true, "phase": 2, "message": "Operator GE matched 5 at TX:blocking_inbound_anomaly_score." }
```

`intercepted: true` means ModSecurity killed the transaction. No `action` block means it went through.

### `engine_mode`

`ENABLED` (SecRuleEngine On) or `DETECTION_ONLY`. Send the same request in DetectionOnly ([`phase1-crs-sqli-detectiononly.json`](../evidence/sanitized-samples/phase1-crs-sqli-detectiononly.json)) and you get a **200**. It reached the backend. Rule 949110's line flips from `Access denied with code 403 (phase 2).` to `Warning. Operator GE matched 5 at TX:blocking_inbound_anomaly_score.`, and the `action` block disappears. Same rules, same score, zero enforcement. That's exactly what DetectionOnly is for: baseline first, block later.

### `stopwatch`

Microseconds per phase (`p1`…`p5`). Handy later, when you start caring about performance.

## A match that didn't block

[`evidence/sanitized-samples/phase1-numeric-host-allowed.json`](../evidence/sanitized-samples/phase1-numeric-host-allowed.json), from `curl http://127.0.0.1:8080/`:

```
allow  score=3  200  GET / HTTP/1.1  rules=920350
```

Rule **920350** ("Host header is a numeric IP address", severity WARNING, 3 points) matched on `REQUEST_HEADERS:Host`. Three is under five. So 949110 stayed quiet and the request went through. It's also why the test runner always sends `Host: localhost`. And it's where the [anomaly-scoring experiment](anomaly-scoring-experiment.md) starts.

## Checklist for any transaction

1. Find it. Transaction id from the `X-WFR-Transaction` header, or `tools/summarize_audit.py`.
2. Decision. Is `action.intercepted` true? Which phase?
3. Which rule denied (`Access denied` line) and which only matched (`Warning.` lines)?
4. For every match: the variable (`data`), severity, paranoia level, file and line.
5. Scores. Read the 980170 line: total, per category, threshold.
6. Open the rule source at that file and line. Explain the match out loud.
