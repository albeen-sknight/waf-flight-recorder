# How to read a ModSecurity transaction

Every request through the lab produces one line in `evidence/raw/audit.json`
(`SecAuditEngine On`, `SecAuditLogFormat JSON`). This note walks through a real
entry: a classic SQL-injection test string sent to the Juice Shop product search.

```
GET /rest/products/search?q=' OR 1=1--
```

Full sanitized entry: [`evidence/sanitized-samples/phase1-crs-sqli-blocked.json`](../evidence/sanitized-samples/phase1-crs-sqli-blocked.json)

One-line view (`python3 tools/summarize_audit.py`):

```
ar4djKPK1WHVNKMHG_yyEQAAAEI  BLOCK p2  score=5  403  GET /rest/products/search?q=%27%20OR%201%3D1-- HTTP/1.1  rules=942100,949110
```

## The parts (`SecAuditLogParts ABCFHZ`)

| Part | JSON key | What it holds | Why it matters |
| --- | --- | --- | --- |
| A | `transaction` | time, **transaction_id**, client/server address | The id ties the browser response, the access log and this entry together. The lab returns it as the `X-WFR-Transaction` response header. |
| B | `request.request_line`, `request.headers` | exactly what the client sent | The raw input before any transformation. |
| C | `request.body` | request body (POST/PUT) | Only present when there is a body. |
| F | `response.status`, `response.headers` | what the client received | `403` here, from Apache's error page — the backend never saw the request. |
| H | `audit_data` | rule messages, the action taken, timings, engine mode | The part you read to answer *what fired and why*. |
| Z | — | end marker | — |

## Reading `audit_data` (part H)

### `messages` — one line per rule that matched

```
Warning. detected SQLi using libinjection with fingerprint 's&1c'
  [file ".../REQUEST-942-APPLICATION-ATTACK-SQLI.conf"] [line "66"] [id "942100"]
  [msg "SQL Injection Attack Detected via libinjection"]
  [data "Matched Data: s&1c found within ARGS:q: ' OR 1=1--"]
  [severity "CRITICAL"] [tag "attack-sqli"] [tag "paranoia-level/1"] ...
```

| Field | Value | Meaning |
| --- | --- | --- |
| `Warning.` | prefix | The rule **matched** but did **not** stop the request itself. |
| `id` | 942100 | CRS rule: SQL injection via libinjection. |
| `file` / `line` | REQUEST-942…, 66 | Where to read the rule source (the "rule autopsy"). |
| `data` | `ARGS:q: ' OR 1=1--` | **Which variable** matched (`ARGS:q`, the query parameter `q`) and the value. |
| `severity` | CRITICAL | In CRS anomaly mode this adds **5 points** to the inbound score. |
| `tag paranoia-level/1` | PL1 | Active at the lowest paranoia level. |

```
Access denied with code 403 (phase 2). Operator GE matched 5 at TX:blocking_inbound_anomaly_score.
  [id "949110"] [msg "Inbound Anomaly Score Exceeded (Total Score: 5)"]
```

This is the **disruptive** line (`Access denied`). Rule 942100 did not block;
rule **949110**, the CRS blocking evaluation, compared the accumulated score
(5) with the threshold (5) and denied the request in **phase 2**.

> A rule match is not the same event as a block. 942100 matched; 949110 blocked.

```
Anomaly Scores: (Inbound Scores: blocking=5, detection=5, per_pl=5-0-0-0, threshold=5) ...
  (SQLI=5, XSS=0, ... COMBINED_SCORE=5)   [id "980170"]
```

Rule **980170** runs in phase 5 (logging) and reports the final scores: total
inbound score, per paranoia level, the threshold, and the score per attack
category. It never blocks.

### `action`

```json
"action": { "intercepted": true, "phase": 2, "message": "Operator GE matched 5 at TX:blocking_inbound_anomaly_score." }
```

`intercepted: true` = ModSecurity stopped the transaction. Absent = allowed.

### `engine_mode`

`ENABLED` (SecRuleEngine On) or `DETECTION_ONLY`. The same request in
DetectionOnly ([`phase1-crs-sqli-detectiononly.json`](../evidence/sanitized-samples/phase1-crs-sqli-detectiononly.json))
returns **200** — it reached the backend — and rule 949110's line changes from
`Access denied with code 403 (phase 2).` to
`Warning. Operator GE matched 5 at TX:blocking_inbound_anomaly_score.`,
with no `action` block. Same rules, same score, no enforcement: that is what
DetectionOnly is for (baselining before you block).

### `stopwatch`

Microseconds spent per phase (`p1`…`p5`). Useful later for performance
experiments.

## A match that did not block

[`evidence/sanitized-samples/phase1-numeric-host-allowed.json`](../evidence/sanitized-samples/phase1-numeric-host-allowed.json):
`curl http://127.0.0.1:8080/`

```
allow  score=3  200  GET / HTTP/1.1  rules=920350
```

Rule **920350** ("Host header is a numeric IP address", severity WARNING = 3
points) matched on `REQUEST_HEADERS:Host`. 3 is below the threshold of 5, so
949110 did not deny and the request reached the application. This is why the
test runner always sends `Host: localhost` — and why this request is the
starting point of the [anomaly-scoring experiment](anomaly-scoring-experiment.md).

## Checklist for any transaction

1. Find it: transaction id from the `X-WFR-Transaction` header, or `tools/summarize_audit.py`.
2. Decision: is `action.intercepted` true? In which phase?
3. Which rule denied (`Access denied` line) and which rules only matched (`Warning.` lines)?
4. For each match: variable (`data`), severity, paranoia level, file/line.
5. Scores: 980170 line — total, per category, threshold.
6. Open the rule source at that file/line and explain the match.
