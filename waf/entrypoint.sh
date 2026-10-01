#!/usr/bin/env bash
# Start Apache in the foreground with lab defaults. Every value can be
# overridden from compose.yaml / the environment.
set -euo pipefail

export WFR_HOME="${WFR_HOME:-/opt/wfr}"
export CRS_HOME="${CRS_HOME:-/opt/crs}"
export WFR_LOG_DIR="${WFR_LOG_DIR:-/var/log/modsec}"
export BACKEND_URL="${BACKEND_URL:-http://juice-shop:3000}"
# On | DetectionOnly | Off
export WFR_RULE_ENGINE="${WFR_RULE_ENGINE:-On}"
export WFR_INBOUND_THRESHOLD="${WFR_INBOUND_THRESHOLD:-5}"

mkdir -p "${WFR_LOG_DIR}"
rm -f /var/run/apache2/apache2.pid

exec apache2ctl -D FOREGROUND
