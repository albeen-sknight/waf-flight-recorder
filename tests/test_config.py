"""Static checks on the WAF configuration (no running lab needed)."""
import re
from pathlib import Path

import pytest

import wfr

MODSEC = wfr.REPO / "modsecurity"
ID_RE = re.compile(r'["\s,]id:(\d+)')


def rule_ids(path: Path) -> list[int]:
    text = path.read_text(encoding="utf-8")
    text = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))
    return [int(i) for i in ID_RE.findall(text)]


def local_files():
    return sorted(MODSEC.rglob("*.conf"))


def test_rule_ids_are_unique():
    seen = {}
    for path in local_files():
        for rid in rule_ids(path):
            assert rid not in seen, f"id {rid} in {path.name} already used in {seen[rid]}"
            seen[rid] = path.name


def test_custom_rules_use_the_local_id_range():
    for path in sorted((MODSEC / "custom-rules").glob("*.conf")):
        for rid in rule_ids(path):
            assert 100000 <= rid <= 100999, f"{path.name}: id {rid} outside 100000-100999"


def test_exclusions_use_the_exclusion_id_range():
    for path in sorted((MODSEC / "exclusions").glob("*.conf")):
        for rid in rule_ids(path):
            assert 1000 <= rid <= 1999, f"{path.name}: id {rid} outside 1000-1999"


def test_every_exclusion_references_the_tuning_journal_or_is_infrastructure():
    text = (MODSEC / "exclusions" / "REQUEST-900-EXCLUSION-RULES-BEFORE-CRS.conf").read_text()
    blocks = re.split(r"\n(?=# \d{4}: )", text)
    for block in blocks[1:]:
        assert "tuning-journal" in block or "Infrastructure" in block, block[:120]


def test_include_order():
    lines = [l.split()[-1] for l in (MODSEC / "main.conf").read_text().splitlines()
             if l.startswith(("Include", "IncludeOptional"))]
    expected = ["modsecurity.conf", "crs-setup.conf", "REQUEST-900-EXCLUSION-RULES-BEFORE-CRS.conf",
                "custom-rules/*.conf", "rules/*.conf", "RESPONSE-999-EXCLUSION-RULES-AFTER-CRS.conf"]
    assert len(lines) == len(expected)
    for got, want in zip(lines, expected):
        assert got.endswith(want), f"include order: {got} should end with {want}"


def test_crs_files_are_not_vendored_or_edited():
    # CRS is pinned and pulled at build time; local changes live in exclusions/.
    assert not (wfr.REPO / "crs" / "rules").exists()


def test_rule_engine_is_configurable_and_audit_log_is_json():
    conf = (MODSEC / "modsecurity.conf").read_text()
    assert "SecRuleEngine ${WFR_RULE_ENGINE}" in conf
    assert "SecAuditLogFormat JSON" in conf


@pytest.mark.parametrize("path", sorted((MODSEC / "custom-rules").glob("*.conf")), ids=lambda p: p.name)
def test_every_custom_rule_file_documents_phase_and_scenarios(path):
    text = path.read_text()
    assert "Phase" in text or "phase" in text
    assert "Scenarios" in text or "scenario" in text.lower() or "LAB-F" in text
