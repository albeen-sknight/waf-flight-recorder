# My anomaly scoring experiment

At the default threshold of 5, every attack scenario I wrote gets blocked and every normal one gets through. When I raised it to 10, the lazy "fix" for a false positive, six blocked scenarios flipped to allowed. Four of them are real attack strings. One is the SQL injection login bypass on `/rest/user/login`.

## How the decision gets made

ModSecurity runs the rules. CRS turns their matches into a verdict:

1. CRS rule 901200 (phase 1) zeroes every score.
2. Each CRS detection rule that matches adds points to `tx.inbound_anomaly_score_pl1` (PL2 to PL4 at higher paranoia levels). CRITICAL is 5, ERROR 4, WARNING 3, NOTICE 2. The action says `block`, but in anomaly mode that falls back to the default action, `pass`.
3. Rule 949110 (phase 2) adds up the active paranoia levels into `TX:BLOCKING_INBOUND_ANOMALY_SCORE` and runs `@ge %{tx.inbound_anomaly_score_threshold}`. True? **Deny.**
4. Rule 980170 (phase 5) writes the final scores to the audit log, as long as there's a score to write.

I set the threshold in `modsecurity/crs-setup.conf` (rule 900110) from the `WFR_INBOUND_THRESHOLD` environment variable. Default: 5.

## At threshold 5 (my regression suite)

![Anomaly scoring scenarios](screenshots/12-anomaly-scoring.png)

| Scenario | Request | Rules matched (points) | Score | Decision |
| --- | --- | --- | --- | --- |
| SCORE-001 | `Host: 127.0.0.1` | 920350 (3) | 3 | **allowed**. A match isn't a block |
| SCORE-004 | `Host: 127.0.0.1` + empty User Agent | 920350 (3) + 920330 (2) | 5 | **blocked** by 949110. Two weak signals add up |
| SCORE-002 | `?wfr_score=phase1` | my 100071 (+5 in **phase 1**) | 0 | allowed. CRS 901200 wiped the score after my rule ran |
| SCORE-003 | `?wfr_score=phase2` | my 100070 (+5 in **phase 2**) | 5 | **blocked** by 949110 |
| CRS-SQLI-001 | `q=' OR 1=1--` | 942100 (5) | 5 | blocked |
| CRS-XSS-001 | `q=<script>alert(1)</script>` | 941100, 941110, 941160, 941390 | 20 | blocked |
| CRS-LFI-001 | `file=../../../../etc/passwd` | 930100 ×2, 930110 ×4, 930120, 932160 | 40 | blocked |

Look at SCORE-002 next to SCORE-003. Identical logic, different phase. My phase 1 version is correct and completely useless, because my file loads before CRS initialisation inside phase 1 (see `modsecurity/main.conf`).

## Threshold 5 → 10

I ran it with `WFR_INBOUND_THRESHOLD=10 tools/native-lab.sh restart`. On Docker it's `WFR_INBOUND_THRESHOLD=10 docker compose up -d`.

![What gets through at threshold 10](screenshots/14-threshold-10.png)

| Scenario | Score | Threshold 5 | Threshold 10 |
| --- | --- | --- | --- |
| SCORE-001 numeric Host | 3 | allowed | allowed |
| SCORE-004 numeric Host + empty User Agent | 5 | blocked | **allowed** |
| SCORE-003 my phase 2 rule | 5 | blocked | **allowed** |
| CRS-SQLI-001 `' OR 1=1--` in search | 5 | blocked | **allowed** |
| CRS-SQLI-003 `' OR 1=1--` as the login email | 5 | blocked | **allowed** (HTTP 201 from the backend) |
| CRS-SCAN-001 sqlmap User Agent | 5 | blocked | **allowed** |
| FP-001-CTRL-3 `=mail -s` in a parameter | 5 | blocked | **allowed** |
| CRS-RCE-001 `x; cat /etc/passwd` | 10 | blocked | blocked |
| CRS-SQLI-002 UNION SELECT | 20 | blocked | blocked |
| CRS-XSS-001 and 002 | 20 and 25 | blocked | blocked |
| CRS-LFI-001 | 40 | blocked | blocked |

Evidence: [`phase5-threshold5-login-sqli-blocked.json`](../evidence/sanitized-samples/phase5-threshold5-login-sqli-blocked.json), [`phase5-threshold10-login-sqli-allowed.json`](../evidence/sanitized-samples/phase5-threshold10-login-sqli-allowed.json).

### So what?

Plenty of real attacks trip exactly one CRITICAL rule. Score 5. Double the threshold and CRS goes blind to every one of them, without a single warning in the config.

The login SQL injection is the classic Juice Shop admin bypass. At threshold 10 my WAF logs it. Then waves it through.

FP-001 scored 5 too. "Just raise it to 10" would've fixed my false positive and reopened every single rule attack in that table. The narrow exclusion in [FP-001](tuning-journal/FP-001.md) fixed it and changed nothing else.

> Threshold changes are experiments. They're not how I fix false positives.

## Reproduce it

```bash
python3 tools/run_scenario.py SCORE-001 SCORE-002 SCORE-003 SCORE-004
WFR_INBOUND_THRESHOLD=10 tools/native-lab.sh restart
python3 tools/run_scenario.py          # every FAIL is an attack that now gets through
tools/native-lab.sh restart            # back to 5
```
