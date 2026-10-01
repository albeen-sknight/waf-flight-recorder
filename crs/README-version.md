# OWASP CRS version

| | |
| --- | --- |
| Pinned tag | **v4.29.0** |
| Where it is pinned | `waf/Dockerfile` (`ARG CRS_VERSION`), `tools/native-lab.sh` (install comment), `modsecurity/crs-setup.conf` (`tx.crs_setup_version=4290`) |
| Source | https://github.com/coreruleset/coreruleset |
| Installed at | `/opt/crs` (container and build workspace) |

CRS is **not** vendored into this repository and is never edited. Local
behaviour changes live in `modsecurity/crs-setup.conf` and
`modsecurity/exclusions/`.

## Bumping CRS

1. Change `CRS_VERSION` in `waf/Dockerfile` and `tx.crs_setup_version` in `crs-setup.conf`.
2. Diff `crs-setup.conf.example` between the two tags for new settings.
3. `docker compose up -d --build && docker compose --profile test run --rm tests`
4. Any scenario whose matched rule IDs changed is a finding: record it in `docs/tuning-journal/`.
