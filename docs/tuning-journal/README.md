# Tuning journal

One entry per change to WAF behaviour that was driven by evidence.

| Entry | Problem | Change | Kind | Regression scenarios |
| --- | --- | --- | --- | --- |
| [FP-001](FP-001.md) | Feedback comment with a tracking URL blocked by CRS 932235 | Runtime exclusion 1010: one rule, one argument, one route | CRS false positive | FP-001, FP-001-CTRL-1..4 |
| [FP-002](FP-002.md) | Juice Shop's own PUT/DELETE requests blocked by CRS 911100 | `tx.allowed_methods` in crs-setup.conf | Configuration for the application | NRM-003, NRM-004, MTH-001 |
| [LAB-F](LAB-F.md) | Own rule 100050 blocked "cough drops" | Rewrote the rule (word boundaries + statement) | Own-rule false positive | LABF-001..003 |
| [INFRA-1000](#infra-1000) | Docker health check would log a 920350 match every 5 s | Exclusion 1000: health route skips ModSecurity | Infrastructure | test_isolation: test_waf_answers |

## INFRA-1000

`curl http://127.0.0.1:8080/wfr-health` (the container health check) matches
920350 (numeric Host). Rather than disabling 920350, rule 1000 turns the rule
engine and audit engine off for the exact path `/wfr-health`, which Apache
serves itself (never proxied).
