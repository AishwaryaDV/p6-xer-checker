#!/usr/bin/env python3
"""check_xer.py - a simple quality checker for Primavera P6 .xer schedules.

Reads a .xer file, flags broken rows, runs three basic schedule-quality
checks, prints a report, and saves one chart.

Usage:
    python check_xer.py samples/terminal.xer
    python check_xer.py samples/hotel.xer --out out --high-float-days 44
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from p6check.parser import parse_xer
from p6check.checks import run_all_checks, DEFAULT_HIGH_FLOAT_DAYS, HOURS_PER_DAY
from p6check.chart import plot_float_distribution

SAMPLE_LIMIT = 5  # how many example activities to print per failing check


def _build_report(xer, task_rows, pred_rows, activities, results) -> dict:
    """Machine-readable summary (for --json / CI)."""
    return {
        "file": os.path.basename(xer.path),
        "p6_version": xer.header[0] if xer.header else None,
        "activities": task_rows,
        "links": pred_rows,
        "broken_rows": [
            {"table": b.table, "line": b.line_no, "reason": b.reason}
            for b in xer.broken_rows
        ],
        "checks": [
            {
                "name": r.name,
                "description": r.description,
                "failed": r.count > 0,
                "count": r.count,
                "total": r.total,
                "pct": round(r.pct, 2),
                "activities": [
                    {
                        "code": a.code,
                        "name": a.name,
                        "total_float_days": (
                            round(a.total_float_hr / HOURS_PER_DAY, 2)
                            if a.total_float_hr is not None
                            else None
                        ),
                    }
                    for a in r.flagged
                ],
            }
            for r in results
        ],
        "passed": not any(r.count for r in results),
    }


def _print_header(xer, task_rows, pred_rows) -> None:
    ver = xer.header[0] if xer.header else "?"
    print("=" * 70)
    print(f"  P6 SCHEDULE CHECK  -  {os.path.basename(xer.path)}")
    print("=" * 70)
    print(f"  P6 export version : {ver}")
    print(f"  Activities (TASK) : {task_rows}")
    print(f"  Links (TASKPRED)  : {pred_rows}")


def _print_broken(xer) -> None:
    broken = xer.broken_rows
    print("-" * 70)
    print(f"  BROKEN ROWS: {len(broken)}")
    if not broken:
        print("    none - every data row matched its table header")
    for b in broken[:SAMPLE_LIMIT]:
        print(f"    [{b.table} line {b.line_no}] {b.reason}")
    if len(broken) > SAMPLE_LIMIT:
        print(f"    ... and {len(broken) - SAMPLE_LIMIT} more")


def _print_checks(results) -> None:
    print("-" * 70)
    print("  CHECKS")
    for res in results:
        flag = "FAIL" if res.count else "pass"
        print(f"\n  [{flag}] {res.name}")
        print(f"         {res.description}")
        print(f"         {res.count} of {res.total} activities ({res.pct:.1f}%)")
        for a in res.flagged[:SAMPLE_LIMIT]:
            fd = (
                f"{a.total_float_hr / HOURS_PER_DAY:.1f}d"
                if a.total_float_hr is not None
                else "n/a"
            )
            name = (a.name[:40] + "...") if len(a.name) > 40 else a.name
            print(f"           - {a.code:<14} float={fd:<8} {name}")
        if res.count > SAMPLE_LIMIT:
            print(f"           ... and {res.count - SAMPLE_LIMIT} more")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("xer", help="path to the .xer file")
    ap.add_argument("--out", default="out", help="directory for the chart PNG")
    ap.add_argument(
        "--high-float-days",
        type=int,
        default=DEFAULT_HIGH_FLOAT_DAYS,
        help="high-float threshold in working days (default: 44, the DCMA value)",
    )
    ap.add_argument("--no-chart", action="store_true", help="skip the chart")
    ap.add_argument(
        "--json",
        action="store_true",
        help="print results as JSON instead of a text report",
    )
    args = ap.parse_args(argv)

    if not os.path.isfile(args.xer):
        print(f"error: file not found: {args.xer}", file=sys.stderr)
        return 2

    xer = parse_xer(args.xer)
    task = xer.table("TASK")
    pred = xer.table("TASKPRED")
    task_rows = len(task.rows) if task else 0
    pred_rows = len(pred.rows) if pred else 0

    activities, results = run_all_checks(xer, args.high_float_days)

    if not args.json:
        _print_header(xer, task_rows, pred_rows)
        _print_broken(xer)
        _print_checks(results)

    if not args.no_chart:
        os.makedirs(args.out, exist_ok=True)
        base = os.path.splitext(os.path.basename(args.xer))[0]
        chart_path = os.path.join(args.out, f"{base}_float_distribution.png")
        plot_float_distribution(
            activities,
            chart_path,
            title=f"Total float distribution - {base}",
            high_float_days=args.high_float_days,
        )
        if not args.json:
            print("-" * 70)
            print(f"  CHART: {chart_path}")

    if args.json:
        report = _build_report(xer, task_rows, pred_rows, activities, results)
        print(json.dumps(report, indent=2))
    else:
        print("=" * 70)
    # Exit non-zero if any check failed (handy for CI), but broken rows alone
    # don't fail the run - they're reported and skipped.
    return 1 if any(r.count for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
