"""Smoke tests for the parser and the three checks.

Runnable with either `pytest` or `python tests/test_checks.py`.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from p6check.parser import parse_xer
from p6check.checks import run_all_checks

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "broken_sample.xer")
SAMPLES = os.path.join(os.path.dirname(os.path.dirname(__file__)), "samples")


def test_fixture_flags_broken_row():
    xer = parse_xer(FIXTURE)
    broken = xer.broken_rows
    assert len(broken) == 1
    assert broken[0].table == "TASK"
    assert "column count mismatch" in broken[0].reason


def test_fixture_runs_all_three_checks():
    xer = parse_xer(FIXTURE)
    _, results = run_all_checks(xer)
    by_count = {r.name.split(" (")[0].split(" >")[0]: r.count for r in results}
    # 3 open ends, 1 negative float, 1 high float in the crafted fixture.
    assert results[0].count == 3  # missing links
    assert results[1].count == 1  # negative float
    assert results[2].count == 1  # high float
    _ = by_count


def test_real_sample_parses():
    path = os.path.join(SAMPLES, "terminal-airport.xer")
    if not os.path.isfile(path):
        return  # samples not present (e.g. shallow checkout) -> skip
    xer = parse_xer(path)
    task = xer.table("TASK")
    assert task is not None and len(task.rows) > 0


if __name__ == "__main__":
    test_fixture_flags_broken_row()
    test_fixture_runs_all_three_checks()
    test_real_sample_parses()
    print("all tests passed")
