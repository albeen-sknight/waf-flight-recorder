# OWASP CRS version

| | |
| --- | --- |
| Pinned tag | **v4.29.0** |
| Pinned in | `waf/Dockerfile` (`ARG CRS_VERSION`), `tools/native-lab.sh` (install comment), `modsecurity/crs-setup.conf` (`tx.crs_setup_version=4290`) |
| Source | https://github.com/coreruleset/coreruleset |
| Installed at | `/opt/crs` (container and native lab) |

I don't copy CRS into this repo and I never edit it. Anything I change about its behaviour lives in `modsecurity/crs-setup.conf` or `modsecurity/exclusions/`.

## How I bump it

1. Change `CRS_VERSION` in `waf/Dockerfile` and `tx.crs_setup_version` in `crs-setup.conf`.
2. Diff `crs-setup.conf.example` between the old and new tags. New settings show up there.
3. `docker compose up -d --build && docker compose --profile test run --rm tests`
4. A scenario whose matched rule IDs changed? That's a finding. It goes in `docs/tuning-journal/`.
