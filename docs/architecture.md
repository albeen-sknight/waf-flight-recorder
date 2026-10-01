# Architecture

Three containers, two networks, one way in. That was the rule I set myself before writing anything else.

```
                         ┌──────────────────────── Docker: network "edge" ───────────────────────┐
 browser / test runner ──▶ 127.0.0.1:8080 ─▶ waf (Apache 2.4.58 + ModSecurity 2.9.7 + CRS v4.29.0) │
                         │                        │ allowed only                                   │
                         └────────────────────────┼───────────────────────────────────────────────┘
                                                  ▼        Docker: network "backend" (internal: true)
                                         juice-shop:3000 (OWASP Juice Shop v20.2.0, no published port)

 waf ──▶ ./evidence/raw/audit.json   (one JSON line per transaction. That's the flight recorder)
```

| Component | Image / version | Network | Published | Job |
| --- | --- | --- | --- | --- |
| `waf` | my image, built from `waf/Dockerfile` (ubuntu:24.04) | edge + backend | `127.0.0.1:8080` only | Reverse proxy + ModSecurity |
| `juice-shop` | `bkimminich/juice-shop:v20.2.0`, the official OWASP image, unmodified | backend (internal) | nothing | The vulnerable target |
| `tests` (profile `test`) | built from `tests/Dockerfile` | edge | nothing | pytest + scenario runner |
| `cloudflared` (profile `demo`) | `cloudflare/cloudflared:2026.9.3` | edge | nothing (outbound tunnel) | Private demo link, next on my list |

## What happens to a request

1. Apache takes it on port 8080 (`waf/apache/wfr-site.conf`).
2. ModSecurity runs phase 1 (headers), then phase 2 (body), in the order I set in `modsecurity/main.conf`: engine settings, CRS setup, runtime exclusions, my rules, CRS, exclusions applied at configure time.
3. Denied? You get a 403 or 405 with my `WFR-BLOCKED` page. Allowed? `mod_proxy` hands it to Juice Shop.
4. Phase 5 writes the audit entry. The response carries `X-WFR-Transaction`, ModSecurity's transaction id, so I can trace any request to its log line.

## Isolation, and how I test it

- `backend` is `internal: true`. Juice Shop can't reach my host or the internet.
- Juice Shop has no `ports:`. `curl 127.0.0.1:3000` fails on the host, and CI checks that on every push.
- The test container sits on `edge` only. It can't reach `http://juice-shop:3000` (`tests/test_isolation.py`).
- The WAF binds to `127.0.0.1`, not `0.0.0.0`. Nothing on my LAN gets in.
- My scenario runner won't send a single byte outside the lab (`tools/wfr.py`).

## Same config, two ways to run it

| | Docker (laptop, CI) | Native (Ubuntu, while I developed) |
| --- | --- | --- |
| Start | `docker compose up -d --build` | `tools/native-lab.sh start` |
| Backend | real Juice Shop | `tools/echo_backend.py`, a tiny stand in |
| Config | `waf/install.sh` + mounted `modsecurity/` | same `waf/install.sh`, same files |
| Logs | `./evidence/raw/` | `./evidence/raw/` |

ModSecurity decides on the request, not on the app behind it, so results carry over from the stand in. And CI runs every scenario against the real Juice Shop on every push anyway.

## Knobs

| Variable | Default | What it does |
| --- | --- | --- |
| `WFR_RULE_ENGINE` | `On` | `DetectionOnly` logs without blocking |
| `WFR_INBOUND_THRESHOLD` | `5` | CRS inbound anomaly threshold. For experiments only |
| `BACKEND_URL` | `http://juice-shop:3000` | The app behind the proxy |
| `CLOUDFLARE_TUNNEL_TOKEN` | empty | Only needed for `--profile demo` |
