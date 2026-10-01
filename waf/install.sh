#!/usr/bin/env bash
# Configure Ubuntu's Apache so that the ONLY ModSecurity config loaded is this
# repo's modsecurity/main.conf. Used by waf/Dockerfile and by tools/native-lab.sh.
set -euo pipefail

WFR_HOME="${WFR_HOME:?set WFR_HOME to the repo root}"

a2enmod -q security2 proxy proxy_http headers unique_id remoteip >/dev/null
a2dissite -q 000-default >/dev/null 2>&1 || true

# Ubuntu's security2.conf includes /etc/modsecurity/*.conf and the packaged
# (older) CRS. Replace it so nothing loads behind our back.
cat > /etc/apache2/mods-available/security2.conf <<'EOF'
<IfModule security2_module>
    SecDataDir /var/cache/modsecurity
</IfModule>
EOF

# Listen on 8080 only.
echo "Listen 8080" > /etc/apache2/ports.conf

ln -sf "${WFR_HOME}/waf/apache/wfr-site.conf" /etc/apache2/sites-enabled/wfr-site.conf

mkdir -p /var/log/modsec /var/cache/modsecurity
chmod 0755 /var/log/modsec
echo "ServerName localhost" > /etc/apache2/conf-enabled/wfr-servername.conf
