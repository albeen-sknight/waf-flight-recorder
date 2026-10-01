# ModSecurity notes — the local rules line by line

Every local rule, with the five decisions that define it. Files are in
`modsecurity/custom-rules/`; each file's header explains the choice.

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

Exclusions (`modsecurity/exclusions/`): **1000** health route off, **1010** FP-001.

## Findings while building

1. **Some directives are server-only.** `SecPcreMatchLimit` and friends are
   refused inside `<VirtualHost>`; ModSecurity is included in server context.
2. **JSON argument names are paths, not `json.` prefixed** (ModSecurity 2.9.7):
   `{"comment": …}` → `ARGS:comment`, `{"a":{"b":…}}` → `ARGS:a.b`,
   `{"list":[…]}` → `ARGS:list.list`. ARG-003/ARG-005 lock this in.
3. **`@within` is a substring test.** `@within PROPFIND PROPPATCH` would match
   `PATCH`. Anchored `@rx` for exact sets (100010). CRS 911100 has the same property.
4. **Apache normalises before ModSecurity sees the path.** `//ftp/` arrives as
   `/ftp/` (MergeSlashes), so even the `t:none` rule catches it; `/FTP/` and
   `/fTp/legal.md` are only caught by the `t:lowercase` rule (RTE-002/004).
5. **Phase decides whether a rule has any effect.** The phase-1 scoring rule is
   wiped by CRS initialisation (901200); the same rule in phase 2 blocks.
6. **CRS rules use `block`, not `deny`.** In anomaly mode `block` resolves to
   the default action (`pass`); only 949110 denies.
7. **DetectionOnly changes the wording.** 949110's line becomes `Warning. …`
   instead of `Access denied …`, and `audit_data.action` disappears.
8. **`ctl:` in a chained rule works.** Exclusion 1010 puts
   `ctl:ruleRemoveTargetById` on the second link, so it fires only when both
   method and route match.
9. **CRS 980170 reports scores only when there is a score.** A clean request
   has no 980170 line; the harness treats a missing score as 0.
