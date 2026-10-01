# Test runner image: pytest + the scenario harness. Runs on the 'edge' network
# only, so it can reach the WAF but not Juice Shop.
FROM python:3.12-slim
WORKDIR /lab
COPY tests/requirements.txt tests/requirements.txt
RUN pip install --no-cache-dir -r tests/requirements.txt
COPY tools/ tools/
COPY scenarios/ scenarios/
COPY tests/ tests/
COPY modsecurity/ modsecurity/
COPY pytest.ini .
CMD ["python", "-m", "pytest"]
