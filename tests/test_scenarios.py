"""Every YAML scenario in scenarios/ is one test.

normal/          must be allowed and match nothing          (allow tests)
controls/        local rules, CRS and anomaly-scoring checks (block + rule tests)
false-positive/  legitimate requests that were once blocked, plus their
                 security controls                         (tuning regression tests)
"""
import pytest

import wfr

SCENARIOS = wfr.load_scenarios()


@pytest.mark.parametrize("scenario", SCENARIOS, ids=[s["id"] for s in SCENARIOS])
def test_scenario(scenario):
    outcome = wfr.send(scenario)
    problems = wfr.check_expectations(scenario, outcome)
    detail = "\n".join(f"  {m.rule_id}: {m.msg} | {m.data[:160]}" for m in outcome.matches)
    assert not problems, (
        f"{scenario['id']} ({scenario['_file']}): {scenario.get('name')}\n"
        f"{outcome.summary()}\n" + "\n".join(f"- {p}" for p in problems) + f"\n{detail}"
    )
