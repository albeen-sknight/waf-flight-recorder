# Anomaly-scoring experiment

**Result:** at the default threshold of 5, every attack scenario is blocked and
every normal scenario is allowed. Raising the threshold to 10 — the tempting
"fix" for a false positive — turned **six** blocked scenarios into allowed ones,
four of them real attack strings, including the SQL-injection login bypass on
`/rest/user/login`.

## How the decision is made

ModSecurity executes rules; **CRS** turns rule matches into a decision:

1. CRS rule 901200 (phase 1) sets every score to 0.
2. Each CRS detection rule that matches adds points to `tx.inbound_anomaly_score_pl1`
   (PL2–4 for higher paranoia levels): CRITICAL 5, ERROR 4, WARNING 3, NOTICE 2.
   Its action is `block`, which in anomaly mode means "the default action" = `pass`.
3. Rule 949110 (phase 2) sums the scores of the active paranoia levels into
   `TX:BLOCKING_INBOUND_ANOMALY_SCORE` and runs
   `@ge %{tx.inbound_anomaly_score_threshold}` → **deny**.
4. Rule 980170 (phase 5) writes the final scores into the audit log whenever any score was accumulated.

Threshold is set in `modsecurity/crs-setup.conf` (rule 900110) from the
`WFR_INBOUND_THRESHOLD` environment variable, default 5.

## Experiments at threshold 5 (the regression suite)

| Scenario | Request | Rules matched (points) | Score | Decision |
| --- | --- | --- | --- | --- |
| SCORE-001 | `Host: 127.0.0.1` | 920350 (3) | 3 | **allowed** — a match is not a block |
| SCORE-004 | `Host: 127.0.0.1` + empty User-Agent | 920350 (3) + 920330 (2) | 5 | **blocked** by 949110 — two weak signals add up |
| SCORE-002 | `?wfr_score=phase1` | local 100071 (+5 in **phase 1**) | 0 | allowed — CRS 901200 reset the score after our rule ran |
| SCORE-003 | `?wfr_score=phase2` | local 100070 (+5 in **phase 2**) | 5 | **blocked** by 949110 |
| CRS-SQLI-001 | `q=' OR 1=1--` | 942100 (5) | 5 | blocked |
| CRS-XSS-001 | `q=<script>alert(1)</script>` | 941100, 941110, 941160, 941390 | 20 | blocked |
| CRS-LFI-001 | `file=../../../../etc/passwd` | 930100 ×2, 930110 ×4, 930120, 932160 | 40 | blocked |

SCORE-002 vs SCORE-003 is the same rule logic in two phases. The phase-1
version is *correct* and still useless: rule order inside phase 1 puts our file
before CRS initialisation (see `modsecurity/main.conf`).

## Threshold experiment: 5 → 10

Run with `WFR_INBOUND_THRESHOLD=10 tools/native-lab.sh restart`
(Docker: `WFR_INBOUND_THRESHOLD=10 docker compose up -d`).

| Scenario | Score | Threshold 5 | Threshold 10 |
| --- | --- | --- | --- |
| SCORE-001 numeric Host | 3 | allowed | allowed |
| SCORE-004 numeric Host + empty UA | 5 | blocked | **allowed** |
| SCORE-003 local phase-2 rule | 5 | blocked | **allowed** |
| CRS-SQLI-001 `' OR 1=1--` in search | 5 | blocked | **allowed** |
| CRS-SQLI-003 `' OR 1=1--` as login e-mail | 5 | blocked | **allowed** (HTTP 201 from the backend) |
| CRS-SCAN-001 sqlmap User-Agent | 5 | blocked | **allowed** |
| FP-001-CTRL-3 `=mail -s` in a parameter | 5 | blocked | **allowed** |
| CRS-RCE-001 `x; cat /etc/passwd` | 10 | blocked | blocked |
| CRS-SQLI-002 UNION SELECT | 20 | blocked | blocked |
| CRS-XSS-001 / 002 | 20 / 25 | blocked | blocked |
| CRS-LFI-001 | 40 | blocked | blocked |

Evidence: [`phase5-threshold5-login-sqli-blocked.json`](../evidence/sanitized-samples/phase5-threshold5-login-sqli-blocked.json),
[`phase5-threshold10-login-sqli-allowed.json`](../evidence/sanitized-samples/phase5-threshold10-login-sqli-allowed.json).

### What this shows

- Many real attacks are caught by **exactly one** CRITICAL rule (score 5).
  Doubling the threshold silently disables CRS for all of them.
- The login SQLi (`' OR 1=1--` as e-mail) is the classic Juice Shop admin-login
  bypass. At threshold 10 the WAF logs it and lets it through.
- FP-001 had score 5. "Raise the threshold to 10" would have fixed the false
  positive *and* reopened every single-rule attack above. The narrow exclusion
  in [FP-001](tuning-journal/FP-001.md) fixed it with no change to any other request.

> Treat threshold changes as experiments, not as the default fix for false positives.

## How to reproduce

```bash
python3 tools/run_scenario.py SCORE-001 SCORE-002 SCORE-003 SCORE-004
WFR_INBOUND_THRESHOLD=10 tools/native-lab.sh restart
python3 tools/run_scenario.py          # the FAILs are the attacks that now pass
tools/native-lab.sh restart            # back to 5
```
