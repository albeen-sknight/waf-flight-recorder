# Architecture

```
                         ┌──────────────────────── Docker: network "edge" ───────────────────────┐
 browser / test runner ──▶ 127.0.0.1:8080 ─▶ waf (Apache 2.4.58 + ModSecurity 2.9.7 + CRS v4.29.0) │
                         │                        │ allowed only                                   │
                         └────────────────────────┼───────────────────────────────────────────────┘
                                                  ▼        Docker: network "backend" (internal: true)
                                         juice-shop:3000 (OWASP Juice Shop v20.2.0, no published port)

 waf ──▶ ./evidence/raw/audit.json   (one JSON line per transaction — the flight recorder)
```

| Component | Image / version | Network | Published | Purpose |
| --- | --- | --- | --- | --- |
| `waf` | built from `waf/Dockerfile` (ubuntu:24.04) | edge + backend | `127.0.0.1:8080` only | Reverse proxy + ModSecurity |
| `juice-shop` | `bkimminich/juice-shop:v20.2.0` | backend (internal) | nothing | Deliberately vulnerable target |
| `tests` (profile `test`) | built from `tests/Dockerfile` | edge | nothing | pytest + scenario runner |
| `cloudflared` (profile `demo`) | `cloudflare/cloudflared:2026.9.3` | edge | nothing (outbound tunnel) | Private demo link (Session C) |

## Request path inside the WAF

1. Apache receives the request on :8080 (`waf/apache/wfr-site.conf`).
2. ModSecurity runs phase 1 (headers) and phase 2 (body) rules in the order of
   `modsecurity/main.conf`: engine settings → CRS setup → runtime exclusions →
   local rules → CRS → configure-time exclusions.
3. A deny returns 403/405 with the `WFR-BLOCKED` page; otherwise `mod_proxy`
   forwards to `BACKEND_URL`.
4. Phase 5 writes the audit entry; the response carries `X-WFR-Transaction`
   (= ModSecurity transaction id) so any request can be traced to its entry.

## Isolation guarantees (tested)

- `backend` is `internal: true`: Juice Shop has no route to the host or internet.
- No `ports:` on Juice Shop: `curl 127.0.0.1:3000` fails on the host (CI step).
- The test container is on `edge` only: `http://juice-shop:3000` is unreachable
  (`tests/test_isolation.py`).
- The WAF binds to `127.0.0.1`, not `0.0.0.0`: not reachable from the LAN.
- The scenario runner refuses any destination outside the lab (`tools/wfr.py`).

## Two ways to run the same config

| | Docker (laptop, CI) | Native (build workspace) |
| --- | --- | --- |
| Start | `docker compose up -d --build` | `tools/native-lab.sh start` |
| Backend | real Juice Shop | `tools/echo_backend.py` stand-in |
| Config | `waf/install.sh` + mounted `modsecurity/` | same `waf/install.sh`, same files |
| Logs | `./evidence/raw/` | `./evidence/raw/` |

ModSecurity decides on the request, so rule results carry over; CI confirms
every scenario against the real Juice Shop on each push.

## Knobs (environment variables)

| Variable | Default | Effect |
| --- | --- | --- |
| `WFR_RULE_ENGINE` | `On` | `DetectionOnly` to log without blocking |
| `WFR_INBOUND_THRESHOLD` | `5` | CRS inbound anomaly threshold (experiments only) |
| `BACKEND_URL` | `http://juice-shop:3000` | Proxied application |
| `CLOUDFLARE_TUNNEL_TOKEN` | empty | Needed only for `--profile demo` |
