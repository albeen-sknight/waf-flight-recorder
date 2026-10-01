#!/usr/bin/env python3
"""Run lab scenarios by id (or all) and print what the WAF decided.

    python3 tools/run_scenario.py              # every scenario
    python3 tools/run_scenario.py HDR-001 FP-001
    python3 tools/run_scenario.py --show HDR-001   # also print matched rule messages

Only sends traffic to the lab (see tools/wfr.py: check_target).
"""
import sys

import wfr


def main(argv: list[str]) -> int:
    show = "--show" in argv
    wanted = [a for a in argv if not a.startswith("--")]
    scenarios = [s for s in wfr.load_scenarios() if not wanted or s["id"] in wanted]
    if not scenarios:
        print("no matching scenarios")
        return 1
    failures = 0
    for sc in scenarios:
        outcome = wfr.send(sc)
        problems = wfr.check_expectations(sc, outcome)
        mark = "PASS" if not problems else "FAIL"
        failures += bool(problems)
        print(f"[{mark}] {sc['id']:<14} {outcome.summary()}")
        for p in problems:
            print(f"         - {p}")
        if show:
            for m in outcome.matches:
                print(f"         {m.rule_id}: {m.msg} | {m.data}")
    print(f"\n{len(scenarios) - failures}/{len(scenarios)} scenarios as expected")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
