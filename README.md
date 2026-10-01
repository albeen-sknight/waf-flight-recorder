# WAF Flight Recorder

[![WAF lab](https://github.com/albeen-sknight/waf-flight-recorder/actions/workflows/lab.yml/badge.svg)](https://github.com/albeen-sknight/waf-flight-recorder/actions/workflows/lab.yml)

A hands-on **ModSecurity + OWASP CRS** rule-engineering lab: an intentionally
vulnerable shop (OWASP Juice Shop) behind Apache + ModSecurity 2.9.7 + CRS
v4.29.0, with my own SecLang rules, CRS rule autopsies, anomaly-scoring
experiments, false-positive tuning, and a regression suite that proves every
tuning change still blocks what it should.

> This is a **defensive learning lab**. It does not build a WAF engine and does
> not protect anything real. All test traffic goes to a local, isolated target.

For every request the lab answers: *what did the WAF inspect, which rule
fired, why, what did it decide, and how would I tune that safely?*

## Quick start (Docker Desktop)

```bash
git clone https://github.com/albeen-sknight/waf-flight-recorder.git
cd waf-flight-recorder
docker compose up -d --build                    # http://localhost:8080
docker compose --profile test run --rm tests    # 60+ checks against the live WAF
docker compose down
```

Try it by hand:

```bash
curl -i "http://localhost:8080/rest/products/search?q=apple"              # 200, allowed
curl -i "http://localhost:8080/rest/products/search?q=%27%20OR%201%3D1--" # 403 WFR-BLOCKED
curl -i -A "WFR-Lab-Bot/1.0" http://localhost:8080/                       # 403, my rule 100001
python3 tools/summarize_audit.py -n 5                                     # what fired, and why
```

Every response carries `X-WFR-Transaction`; that id finds the request's entry in
`evidence/raw/audit.json`.

## What is in here

| Area | Where | What it shows |
| --- | --- | --- |
| Architecture | [docs/architecture.md](docs/architecture.md) | Isolated networks, request path, run modes |
| Reading the evidence | [docs/how-to-read-a-transaction.md](docs/how-to-read-a-transaction.md) | One real audit entry, part by part |
| Own rules (labs A–H) | [modsecurity/custom-rules/](modsecurity/custom-rules/), [docs/modsecurity-notes.md](docs/modsecurity-notes.md) | Phases, targets, operators, transformations, chains, scoring |
| CRS rule autopsies | [docs/crs-rule-autopsies/](docs/crs-rule-autopsies/) | 942100, 941110, 930120, 932235, 920350 taken apart with one-variable experiments |
| Anomaly scoring | [docs/anomaly-scoring-experiment.md](docs/anomaly-scoring-experiment.md) | Match ≠ block; 3 + 2 = 5; threshold 10 reopens the login SQLi |
| Tuning journal | [docs/tuning-journal/](docs/tuning-journal/) | FP-001 (narrow CRS exclusion), FP-002 (method policy), LAB-F (own rule) |
| Scenarios | [scenarios/](scenarios/) | 45 YAML requests: normal, controls, false positives |
| Tests + CI | [tests/](tests/), [.github/workflows/lab.yml](.github/workflows/lab.yml) | Real Docker stack + Juice Shop on every push |
| Evidence | [evidence/sanitized-samples/](evidence/sanitized-samples/) | Before/after audit entries behind every claim |

## The headline results

- **FP-001:** a customer pasting a tracking link (`…&utm_source=mail in …`) into
  feedback was blocked by CRS **932235** (Unix command injection: `=` + `mail` +
  space). Fixed with a runtime exclusion scoped to *one rule, one argument, one
  route*. Command injection and XSS in the same field, and the same pattern on
  other routes, are still blocked — all in CI.
- **Threshold trap:** raising the inbound threshold from 5 to 10 would also have
  fixed FP-001 — and let the classic `' OR 1=1--` login bypass through.
- **Phase matters:** the same scoring rule does nothing in phase 1 (CRS resets
  the score afterwards) and blocks in phase 2.
- **Transformations matter:** `/FTP/` and `/fTp/legal.md` bypass the `t:none`
  version of my route rule, not the normalised one.

## The engineering loop used for every change

Observe → locate the variable → choose the phase → write/inspect the rule →
DetectionOnly → read the audit evidence → enforce → break it → tune narrowly →
regression-test (legitimate case allowed **and** attack still blocked) → document.

## Repository layout

```text
compose.yaml                 waf + juice-shop (+ tests, cloudflared profiles)
waf/                         WAF image: Dockerfile, install.sh, Apache vhost
modsecurity/
  main.conf                  include order — read this first
  modsecurity.conf           engine, body access, JSON audit log
  crs-setup.conf             paranoia level, threshold, allowed methods
  custom-rules/              my rules, IDs 100000-100999
  exclusions/                tuning, IDs 1000-1999 (before / after CRS)
crs/README-version.md        pinned CRS tag (CRS itself is never edited)
scenarios/                   normal/, controls/, false-positive/ (YAML)
tests/                       pytest: scenarios, config checks, isolation
tools/                       scenario runner, audit summarizer, native lab, stand-in backend
docs/                        architecture, notes, autopsies, scoring, tuning journal
evidence/sanitized-samples/  committed audit entries (raw logs are git-ignored)
```

## Running without Docker (Ubuntu 24.04)

```bash
sudo apt-get install -y apache2 libapache2-mod-security2 python3-pytest python3-yaml python3-requests
sudo git clone --depth 1 --branch v4.29.0 https://github.com/coreruleset/coreruleset.git /opt/crs
tools/native-lab.sh install && tools/native-lab.sh start
python3 -m pytest
```

## Experiment knobs

```bash
WFR_RULE_ENGINE=DetectionOnly docker compose up -d   # log, never block
WFR_INBOUND_THRESHOLD=10 docker compose up -d        # see what slips through
```

## Safety boundaries

- Juice Shop runs only on an internal Docker network with no published port.
- The WAF listens on `127.0.0.1` only.
- The scenario runner refuses any destination that is not the lab.
- Only synthetic data; audit samples are sanitized before they are committed.

## Roadmap

- [x] MVP — ModSecurity, custom rules, tests, audit-log notes
- [x] V1 — CRS, five autopsies, anomaly scoring, real false-positive investigation, narrow exclusion, regression tests, CI
- [ ] Private demo link via Cloudflare Tunnel + Access, and a comparison with Cloudflare's free WAF
- [ ] V2 — paranoia levels 2–3, response-body rules, libModSecurity v3 + Nginx comparison

## References

- [ModSecurity Reference Manual](https://github.com/owasp-modsecurity/ModSecurity/wiki)
- [OWASP CRS documentation](https://coreruleset.org/docs/) — [false positives and tuning](https://coreruleset.org/docs/2-how-crs-works/2-3-false-positives-and-tuning/)
- [OWASP Juice Shop](https://owasp.org/www-project-juice-shop/)
