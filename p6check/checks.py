"""The three schedule-quality checks.

These are a small subset of the industry-standard DCMA 14-Point Schedule
Assessment that planners use to sanity-check a Primavera P6 schedule:

1. Missing links  - activities with no predecessor and/or no successor
                    ("open ends"). They weaken the CPM logic network.
2. Negative float - total float < 0. The schedule is behind: the work cannot
                    finish within its constraints/deadline.
3. High float     - total float above a threshold (DCMA uses 44 working days).
                    Usually a sign of missing logic or an unrealistic plan.

Float in the .xer file is stored in hours (total_float_hr_cnt), so the high
float threshold of 44 working days is converted using an 8-hour working day.
"""

from __future__ import annotations

from dataclasses import dataclass

from .parser import XerFile

# A working day is 8 hours; DCMA's high-float threshold is 44 working days.
HOURS_PER_DAY = 8.0
DEFAULT_HIGH_FLOAT_DAYS = 44

# P6 milestone activity types. A start/finish milestone legitimately has one
# open end, so we don't want to flag those as missing-link problems.
START_MILESTONE = "TT_Mile"
FINISH_MILESTONE = "TT_FinMile"


@dataclass
class Activity:
    task_id: str
    code: str
    name: str
    task_type: str
    total_float_hr: float | None


def _to_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def load_activities(xer: XerFile) -> list[Activity]:
    task = xer.table("TASK")
    if task is None:
        return []
    out: list[Activity] = []
    for r in task.rows:
        out.append(
            Activity(
                task_id=r.get("task_id", ""),
                code=r.get("task_code", ""),
                name=r.get("task_name", ""),
                task_type=r.get("task_type", ""),
                total_float_hr=_to_float(r.get("total_float_hr_cnt")),
            )
        )
    return out


@dataclass
class CheckResult:
    name: str
    description: str
    flagged: list[Activity]
    total: int

    @property
    def count(self) -> int:
        return len(self.flagged)

    @property
    def pct(self) -> float:
        return 100.0 * self.count / self.total if self.total else 0.0


def check_missing_links(xer: XerFile, activities: list[Activity]) -> CheckResult:
    """Flag activities missing a predecessor and/or a successor (open ends)."""
    pred = xer.table("TASKPRED")
    has_pred: set[str] = set()
    has_succ: set[str] = set()
    if pred is not None:
        for r in pred.rows:
            # In TASKPRED: task_id is the successor, pred_task_id the predecessor.
            succ_id = r.get("task_id", "")
            pred_id = r.get("pred_task_id", "")
            has_pred.add(succ_id)  # succ_id has a predecessor
            has_succ.add(pred_id)  # pred_id has a successor

    flagged: list[Activity] = []
    for a in activities:
        missing_pred = a.task_id not in has_pred
        missing_succ = a.task_id not in has_succ
        if not (missing_pred or missing_succ):
            continue
        # Start/finish milestones are allowed exactly one open end.
        if a.task_type == START_MILESTONE and missing_pred and not missing_succ:
            continue
        if a.task_type == FINISH_MILESTONE and missing_succ and not missing_pred:
            continue
        flagged.append(a)

    return CheckResult(
        name="Missing links (open ends)",
        description="Activities with no predecessor and/or no successor",
        flagged=flagged,
        total=len(activities),
    )


def check_negative_float(xer: XerFile, activities: list[Activity]) -> CheckResult:
    """Flag activities with total float < 0 (schedule is behind)."""
    flagged = [
        a for a in activities if a.total_float_hr is not None and a.total_float_hr < 0
    ]
    return CheckResult(
        name="Negative total float",
        description="Total float < 0 (behind deadline/constraint)",
        flagged=flagged,
        total=len(activities),
    )


def check_high_float(
    xer: XerFile,
    activities: list[Activity],
    high_float_days: int = DEFAULT_HIGH_FLOAT_DAYS,
) -> CheckResult:
    """Flag activities with total float above the high-float threshold."""
    threshold_hr = high_float_days * HOURS_PER_DAY
    flagged = [
        a
        for a in activities
        if a.total_float_hr is not None and a.total_float_hr > threshold_hr
    ]
    return CheckResult(
        name=f"High total float (> {high_float_days} working days)",
        description=f"Total float > {threshold_hr:.0f}h; often missing logic",
        flagged=flagged,
        total=len(activities),
    )


def run_all_checks(
    xer: XerFile, high_float_days: int = DEFAULT_HIGH_FLOAT_DAYS
) -> tuple[list[Activity], list[CheckResult]]:
    activities = load_activities(xer)
    results = [
        check_missing_links(xer, activities),
        check_negative_float(xer, activities),
        check_high_float(xer, activities, high_float_days),
    ]
    return activities, results
