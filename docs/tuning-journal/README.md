# My tuning journal

One entry per change I made to how the WAF behaves. Every one is backed by evidence.

| Entry | Problem | My change | Kind | Regression scenarios |
| --- | --- | --- | --- | --- |
| [FP-001](FP-001.md) | Feedback comment with a tracking URL, blocked by CRS 932235 | Runtime exclusion 1010: one rule, one argument, one route | CRS false positive | FP-001, FP-001-CTRL-1 to 4 |
| [FP-002](FP-002.md) | Juice Shop's own PUT and DELETE requests, blocked by CRS 911100 | `tx.allowed_methods` in `crs-setup.conf` | App configuration | NRM-003, NRM-004, MTH-001 |
| [LAB-F](LAB-F.md) | My own rule 100050 blocked "cough drops" | Rewrote the rule: word boundaries, whole statement | My own false positive | LABF-001 to 003 |
| [INFRA-1000](#infra-1000) | Docker health check would log a 920350 match every 5 seconds | Exclusion 1000: health route skips ModSecurity | Infrastructure | test_isolation: test_waf_answers |

## INFRA-1000

The container health check runs `curl http://127.0.0.1:8080/wfr-health`. Numeric Host, so 920350 fires. Every five seconds, forever. I didn't touch 920350. My rule 1000 switches the rule engine and the audit engine off for that one exact path, which Apache serves itself and never proxies.
