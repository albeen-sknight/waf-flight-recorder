"""The vulnerable application must only be reachable through the WAF."""
import os

import pytest
import requests

import wfr


def test_waf_answers():
    r = requests.get(wfr.BASE_URL.rstrip("/") + "/wfr-health", timeout=5)
    assert r.status_code == 200


@pytest.mark.skipif(not os.environ.get("WFR_ISOLATION_TARGET"),
                    reason="only meaningful in the Docker lab (set WFR_ISOLATION_TARGET)")
def test_juice_shop_is_not_reachable_directly():
    # The test container sits on the 'edge' network only; Juice Shop is on the
    # internal 'backend' network. Name resolution or the connection must fail.
    with pytest.raises(requests.exceptions.ConnectionError):
        requests.get(os.environ["WFR_ISOLATION_TARGET"], timeout=5)


def test_runner_refuses_non_lab_destinations():
    with pytest.raises(wfr.UnsafeTarget):
        wfr.check_target("https://example.com/")
    with pytest.raises(wfr.UnsafeTarget):
        wfr.check_target("http://10.0.0.5:8080/")
    wfr.check_target("http://localhost:8080/")
    wfr.check_target("http://waf:8080/")
