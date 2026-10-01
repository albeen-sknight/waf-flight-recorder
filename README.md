# WAF Flight Recorder

[![WAF lab](https://github.com/albeen-sknight/waf-flight-recorder/actions/workflows/lab.yml/badge.svg)](https://github.com/albeen-sknight/waf-flight-recorder/actions/workflows/lab.yml)

I put OWASP Juice Shop, a shop that's broken on purpose, behind Apache + ModSecurity 2.9.7 + OWASP CRS v4.29.0. Then I attacked it, wrote my own rules, broke them, and tuned them. Every claim in this repo has an audit-log entry behind it and a test that fails if it stops being true.

> It's a defensive learning lab. Not a WAF engine, not protecting anything real. All traffic goes to a local, isolated target.

The whole point is one question, asked of every request: what did the WAF look at, which rule fired, why, what did it decide, and how do I tune that without opening a hole?

## Quick start

You need Docker Desktop. That's it.

```bash
git clone https://github.com/albeen-sknight/waf-flight-recorder.git
cd waf-flight-recorder
docker compose up -d --build                    # http://localhost:8080
docker compose --profile test run --rm tests    # 60+ checks against the live WAF
docker compose down
```

Poke it by hand:

```bash
curl -i "http://localhost:8080/rest/products/search?q=apple"              # 200, allowed
curl -i "http://localhost:8080/rest/products/search?q=%27%20OR%201%3D1--" # 403 WFR-BLOCKED
curl -i -A "WFR-Lab-Bot/1.0" http://localhost:8080/                       # 403, my rule 100001
python3 tools/summarize_audit.py -n 5                                     # what fired, and why
```

Every response comes back with an `X-WFR-Transaction` header. Grab that id and you'll find the exact entry in `evidence/raw/audit.json`.

## What's in here

| Area | Where | What it shows |
| --- | --- | --- |
| Architecture | [docs/architecture.md](docs/architecture.md) | Isolated networks, request path, two ways to run it |
| Reading the evidence | [docs/how-to-read-a-transaction.md](docs/how-to-read-a-transaction.md) | One real audit entry, piece by piece |
| My rules (labs A–H) | [modsecurity/custom-rules/](modsecurity/custom-rules/), [docs/modsecurity-notes.md](docs/modsecurity-notes.md) | Phases, targets, operators, transformations, chains, scoring |
| CRS rule autopsies | [docs/crs-rule-autopsies/](docs/crs-rule-autopsies/) | 942100, 941110, 930120, 932235 and 920350, taken apart |
| Anomaly scoring | [docs/anomaly-scoring-experiment.md](docs/anomaly-scoring-experiment.md) | A match isn't a block. 3 + 2 = 5. Threshold 10 lets the login SQLi back in |
| Tuning journal | [docs/tuning-journal/](docs/tuning-journal/) | FP-001, FP-002, LAB-F |
| Scenarios | [scenarios/](scenarios/) | 45 YAML requests: normal traffic, controls, false positives |
| Tests + CI | [tests/](tests/), [.github/workflows/lab.yml](.github/workflows/lab.yml) | The real Docker stack and Juice Shop, on every push |
| Evidence | [evidence/sanitized-samples/](evidence/sanitized-samples/) | Before/after audit entries |

## What I found

**FP-001.** A customer pastes a tracking link into the feedback form: `…&utm_source=mail in your newsletter…`. Blocked. CRS 932235 reads `=` + `mail` + a space as Unix command injection. The fix is one runtime exclusion: one rule, one argument, one route. And the same field still blocks command injection and XSS. CI checks both.

**The threshold trap.** Bumping the inbound threshold from 5 to 10 would've "fixed" FP-001 too. It also lets `' OR 1=1--` straight through the login form. Don't.

**Phase matters.** Same scoring rule, two phases. In phase 1 it does nothing, because CRS resets the score right after. In phase 2 it blocks.

**Transformations matter.** `/FTP/` and `/fTp/legal.md` sail past the `t:none` version of my route rule. The normalised version catches both.

## The loop

Every change went through the same cycle. Observe the request, find the variable, pick the phase, write or read the rule, run it in DetectionOnly, read the audit entry, enforce, break it, tune it as narrowly as you can, then prove two things: the legit request passes, and the attack still gets blocked. Write it down. Commit.

## Layout

```text
compose.yaml                 waf + juice-shop (+ tests, cloudflared profiles)
waf/                         WAF image: Dockerfile, install.sh, Apache vhost
modsecurity/
  main.conf                  include order. Read this first
  modsecurity.conf           engine, body access, JSON audit log
  crs-setup.conf             paranoia level, threshold, allowed methods
  custom-rules/              my rules, IDs 100000-100999
  exclusions/                tuning, IDs 1000-1999 (before / after CRS)
crs/README-version.md        pinned CRS tag. CRS itself is never edited
scenarios/                   normal/, controls/, false-positive/ (YAML)
tests/                       pytest: scenarios, config checks, isolation
tools/                       scenario runner, audit summarizer, native lab, stand-in backend
docs/                        architecture, notes, autopsies, scoring, tuning journal
evidence/sanitized-samples/  committed audit entries (raw logs stay out of git)
```

## No Docker? (Ubuntu 24.04)

```bash
sudo apt-get install -y apache2 libapache2-mod-security2 python3-pytest python3-yaml python3-requests
sudo git clone --depth 1 --branch v4.29.0 https://github.com/coreruleset/coreruleset.git /opt/crs
tools/native-lab.sh install && tools/native-lab.sh start
python3 -m pytest
```

Same config, same rules. A tiny echo app stands in for Juice Shop.

## Knobs

```bash
WFR_RULE_ENGINE=DetectionOnly docker compose up -d   # log everything, block nothing
WFR_INBOUND_THRESHOLD=10 docker compose up -d        # watch what slips through
```

## Safety

- Juice Shop lives on an internal Docker network. No published port.
- The WAF listens on `127.0.0.1`. Your LAN can't see it.
- The scenario runner refuses anything that isn't the lab.
- Synthetic data only. Audit samples get sanitized before they're committed.

## Roadmap

- [x] MVP: ModSecurity, my rules, tests, audit-log notes
- [x] V1: CRS, five autopsies, anomaly scoring, a real false positive, a narrow exclusion, regression tests, CI
- [ ] Private demo link through Cloudflare Tunnel + Access, plus a head-to-head with Cloudflare's free WAF
- [ ] V2: paranoia levels 2–3, response-body rules, libModSecurity v3 + Nginx

## References

- [ModSecurity Reference Manual](https://github.com/owasp-modsecurity/ModSecurity/wiki)
- [OWASP CRS docs](https://coreruleset.org/docs/), especially [false positives and tuning](https://coreruleset.org/docs/2-how-crs-works/2-3-false-positives-and-tuning/)
- [OWASP Juice Shop](https://owasp.org/www-project-juice-shop/)
