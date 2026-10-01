# WAF Flight Recorder: WAF image
#
# Apache 2.4 + ModSecurity 2.9.7 (Ubuntu packages) + OWASP CRS (pinned tag).
# The same install script runs natively in the build workspace, so a rule
# tested there behaves identically inside this container.

FROM ubuntu:24.04

ARG CRS_VERSION=v4.29.0

ENV DEBIAN_FRONTEND=noninteractive \
    WFR_HOME=/opt/wfr \
    CRS_HOME=/opt/crs \
    WFR_LOG_DIR=/var/log/modsec

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      apache2 libapache2-mod-security2 ca-certificates curl git \
 && git clone --depth 1 --branch "${CRS_VERSION}" \
      https://github.com/coreruleset/coreruleset.git "${CRS_HOME}" \
 && rm -rf "${CRS_HOME}/.git" "${CRS_HOME}/tests" "${CRS_HOME}/regex-assembly" \
 && apt-get purge -y git && apt-get autoremove -y \
 && rm -rf /var/lib/apt/lists/*

# Baseline copy of the repo's WAF config. compose.yaml mounts ./modsecurity
# over it as read only, so rule edits only need `docker compose restart waf`.
COPY waf/ ${WFR_HOME}/waf/
COPY modsecurity/ ${WFR_HOME}/modsecurity/

RUN ${WFR_HOME}/waf/install.sh

EXPOSE 8080

HEALTHCHECK --interval=5s --timeout=3s --retries=20 \
  CMD curl -fsS -o /dev/null http://127.0.0.1:8080/wfr-health || exit 1

ENTRYPOINT ["/opt/wfr/waf/entrypoint.sh"]
