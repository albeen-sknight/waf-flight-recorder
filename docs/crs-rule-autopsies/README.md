# CRS rule autopsies

Five CRS v4.29.0 rules, each taken apart from a real audit-log event in this
lab, then probed by changing **one input characteristic at a time**.
Template from the project report. Line numbers are where each `SecRule` starts in
`/opt/crs/rules/` at tag v4.29.0 (the audit log reports the line where the rule *ends*, e.g. 942100 starts at 46, logged as 66).

| Rule | Category | Severity (points) | Triggered by scenario | Notable lesson |
| --- | --- | --- | --- | --- |
| [942100](942100.md) | SQL injection (libinjection) | CRITICAL (5) | CRS-SQLI-001, CRS-SQLI-003 | Not a regex: a SQL tokenizer. `O'Reilly` passes, `1 OR 1=1` does not. |
| [941110](941110.md) | XSS, script tag | CRITICAL (5) | CRS-XSS-001 | Six transformations decode HTML entities before matching. |
| [930120](930120.md) | Local file inclusion | CRITICAL (5) | CRS-LFI-001 | Phrase list from a data file (`@pmFromFile`), not a regex. |
| [932235](932235.md) | Unix command injection | CRITICAL (5) | FP-001 | Cause of the project's real false positive. |
| [920350](920350.md) | Protocol enforcement | WARNING (3) | SCORE-001 | Matches but never blocks on its own at threshold 5. |

The rule that actually **denies** in every CRS case is not in this list:
[949110](../anomaly-scoring-experiment.md#how-the-decision-is-made) compares
the summed score with the threshold. Every rule above uses the action
`block`, which in CRS's anomaly mode means "use SecDefaultAction" — i.e. `pass`.
