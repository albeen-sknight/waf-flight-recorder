# ModSecurity notes: my rules, line by line

Each rule boils down to five choices: phase, target, operator, transformations, action. Here they all are in one table. The files live in `modsecurity/custom-rules/`, and each file's header says why I picked what I picked.

| ID | Lab | Phase | Target | Operator | Transformations | Action | Scenarios |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 100001 | B header | 1 | `REQUEST_HEADERS:User-Agent` | `@contains WFR-Lab-Bot` | none | deny 403 | HDR-001/002 |
| 100010 | A method | 1 | `REQUEST_METHOD` | `@rx ^(?:PROPFIND\|…)$` | none | deny 405 | MTH-001..003 |
| 100040 | E naive twin | 1 | `REQUEST_FILENAME` | `@beginsWith /ftp` | none | pass, log | RTE-001..004 |
| 100020 | C route | 1 | `REQUEST_FILENAME` | `@beginsWith /ftp` | urlDecodeUni, normalizePath, lowercase | deny 403 | RTE-001..005 |
| 100030 | D argument | 2 | `ARGS:wfr_marker` | `@streq WFR-ARG-MARKER` | none | deny 403 | ARG-001..005 |
| 100050 | F false positive | 2 | `ARGS` | `@rx \bdrop\s+(?:table\|…)\b` | lowercase, compressWhitespace | deny 403 | LABF-001..003 |
| 100060 | G chain | 1 | `REQUEST_METHOD` + `REQUEST_FILENAME` | `@streq DELETE` + `@beginsWith /api/feedbacks` | (2nd) urlDecodeUni, normalizePath, lowercase | deny 403 | CHN-001..003 |
| 100071 | H score, phase 1 | 1 | `ARGS:wfr_score` | `@streq phase1` | none | pass, `setvar` +5 | SCORE-002 |
| 100070 | H score, phase 2 | 2 | `ARGS:wfr_score` | `@streq phase2` | none | pass, `setvar` +critical | SCORE-003 |

Exclusions (`modsecurity/exclusions/`): **1000** switches ModSecurity off for the health route, **1010** is the FP-001 fix.

## Things I learned the hard way

1. **Some directives only work at server level.** Put `SecPcreMatchLimit` inside `<VirtualHost>` and Apache refuses to start. So ModSecurity gets included in server context.
2. **JSON argument names are paths. No `json.` prefix** (ModSecurity 2.9.7). `{"comment": …}` becomes `ARGS:comment`. `{"a":{"b":…}}` becomes `ARGS:a.b`. `{"list":[…]}` becomes `ARGS:list.list`. I'd guessed wrong at first. ARG-003 and ARG-005 now lock the real behaviour in.
3. **`@within` is a substring test.** `@within PROPFIND PROPPATCH` matches `PATCH`. Ouch. For an exact set, use an anchored `@rx` (that's what 100010 does). CRS 911100 has the exact same quirk.
4. **Apache cleans up the path before ModSecurity sees it.** `//ftp/` arrives as `/ftp/` thanks to MergeSlashes, so even the `t:none` rule catches it. `/FTP/` and `/fTp/legal.md`? Only the `t:lowercase` rule gets those (RTE-002/004).
5. **Phase decides whether a rule does anything at all.** The phase-1 scoring rule gets wiped by CRS initialisation (901200). Move the same rule to phase 2 and it blocks.
6. **CRS rules say `block`, not `deny`.** In anomaly mode `block` falls back to the default action, which is `pass`. Only 949110 actually denies.
7. **DetectionOnly changes the log wording.** 949110's line turns into `Warning. …` instead of `Access denied …`, and `audit_data.action` vanishes.
8. **`ctl:` works on a chained rule.** Exclusion 1010 puts `ctl:ruleRemoveTargetById` on the second link, so it only fires when both the method and the route match.
9. **CRS 980170 only reports a score when there is one.** Clean request, no 980170 line. The harness reads a missing score as 0.
