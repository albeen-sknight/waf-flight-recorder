#!/usr/bin/env bash
# Run the lab WITHOUT Docker on an Ubuntu 24.04 machine (this is how the lab
# is developed in the cloud build workspace). Same Apache config as the
# container; the stand-in backend replaces Juice Shop.
#
#   sudo apt-get install -y apache2 libapache2-mod-security2
#   sudo git clone --depth 1 --branch v4.29.0 https://github.com/coreruleset/coreruleset.git /opt/crs
#   tools/native-lab.sh install      # once
#   tools/native-lab.sh start|stop|restart|status
#
# Logs: ./evidence/raw/ (same place as the Docker lab)
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
export WFR_HOME="$REPO"
export CRS_HOME="${CRS_HOME:-/opt/crs}"
export WFR_LOG_DIR="$REPO/evidence/raw"
export BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:3000}"
export WFR_RULE_ENGINE="${WFR_RULE_ENGINE:-On}"
export WFR_INBOUND_THRESHOLD="${WFR_INBOUND_THRESHOLD:-5}"

apache() { sudo --preserve-env=WFR_HOME,CRS_HOME,WFR_LOG_DIR,BACKEND_URL,WFR_RULE_ENGINE,WFR_INBOUND_THRESHOLD apache2ctl "$@"; }

backend_start() {
  if ! curl -s -o /dev/null "http://127.0.0.1:3000/"; then
    nohup python3 "$REPO/tools/echo_backend.py" >/dev/null 2>&1 &
    sleep 0.5
  fi
}

case "${1:-}" in
  install) sudo WFR_HOME="$WFR_HOME" "$REPO/waf/install.sh" ;;
  start)   mkdir -p "$WFR_LOG_DIR"; backend_start; apache -t && apache -k start; sleep 1 ;;
  stop)    apache -k stop || true; pkill -f echo_backend.py || true ;;
  restart) mkdir -p "$WFR_LOG_DIR"; backend_start; apache -t && (apache -k stop || true); sleep 1; apache -k start; sleep 1 ;;
  test)    apache -t ;;
  status)  curl -s -o /dev/null -w "waf: %{http_code}\n" http://localhost:8080/wfr-health || echo "waf: down" ;;
  *) echo "usage: $0 install|start|stop|restart|test|status"; exit 1 ;;
esac
