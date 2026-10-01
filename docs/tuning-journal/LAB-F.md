# LAB-F — A deliberately broad local rule, and the narrow fix

Rule **100050** (`modsecurity/custom-rules/140-deliberate-fp.conf`).

## v1 — too broad (on purpose)

```apache
SecRule ARGS "@contains drop" "id:100050,phase:2,deny,status:403,t:none,t:lowercase,..."
```

Intent: stop `DROP TABLE` in any parameter.

| Request | Result |
| --- | --- |
| `GET /rest/products/search?q=cough drops` | **BLOCKED** 403 by 100050 — false positive ([sample](../../evidence/sanitized-samples/labf-before-cough-drops-blocked.json)) |
| `GET /rest/products/search?q=1; DROP TABLE users` | BLOCKED by 100050 ([sample](../../evidence/sanitized-samples/labf-before-drop-table-blocked.json)) |

`@contains` is a substring test: `drop` is inside `drops`, `dropdown`, `raindrop`, `Dropbox`.

## Diagnosis

The rule tested for a **word fragment**; the threat is a **statement**.

## v2 — narrowed

```apache
SecRule ARGS "@rx \bdrop\s+(?:table|database|schema|view)\b" \
    "id:100050,phase:2,deny,status:403,t:none,t:lowercase,t:compressWhitespace,..."
```

- `\b…\b` — whole words only.
- `drop` must be followed by whitespace and an object type.
- `t:lowercase` + `t:compressWhitespace` — `DrOp    TaBlE` normalises to `drop table`.

| Scenario | Request | v1 | v2 |
| --- | --- | --- | --- |
| LABF-001 | `q=cough drops` | blocked | **allowed** ([sample](../../evidence/sanitized-samples/labf-after-cough-drops-allowed.json)) |
| LABF-002 | `q=1; DROP TABLE users` | blocked | **blocked** ([sample](../../evidence/sanitized-samples/labf-after-drop-table-blocked.json)) |
| LABF-003 | `q=x; DrOp    TaBlE users` | blocked | **blocked** |

## Lesson

A local rule is code: it gets the same treatment as a CRS false positive —
evidence, a narrower condition, and a test for both the legitimate and the
malicious case. CRS already covers SQL injection far better (942xxx); this
rule exists to practise the tuning loop.
