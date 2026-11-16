#!/usr/bin/env python3
"""Aggregate order logs into revenue per customer per month.

Reads a CSV with the columns:
    order_id, customer_id, amount, created_at

Invalid rows are skipped and reported (to stderr by default). The script then
prints revenue grouped by customer and month, sorted by revenue (highest first).

Usage:
    python revenue_report.py [orders.csv]
    python revenue_report.py orders.csv --report-file errors.txt

If no path is given, it defaults to "orders.csv" in the current directory.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation

REQUIRED_COLUMNS = ("order_id", "customer_id", "amount", "created_at")

# Accepted timestamp formats for created_at. The first match wins.
DATE_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%Y/%m/%d %H:%M:%S",
    "%Y/%m/%d",
    "%d/%m/%Y",
    "%m/%d/%Y",
)


def parse_date(value: str) -> datetime:
    """Parse a created_at string, trying several common formats.

    Also handles trailing 'Z' (UTC) in ISO-8601 timestamps.
    Raises ValueError if none of the formats match.
    """
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1]
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    raise ValueError(f"unrecognized date format: {value!r}")


def validate_row(row: dict) -> tuple[str, str, Decimal, datetime]:
    """Validate one row and return the cleaned (customer_id, month, amount, dt).

    Raises ValueError with a human-readable reason if the row is invalid.
    """
    # Guard against missing columns entirely (short rows).
    for col in REQUIRED_COLUMNS:
        if row.get(col) is None:
            raise ValueError(f"missing column '{col}'")

    order_id = (row["order_id"] or "").strip()
    customer_id = (row["customer_id"] or "").strip()
    amount_raw = (row["amount"] or "").strip()
    created_raw = (row["created_at"] or "").strip()

    if not order_id:
        raise ValueError("empty order_id")
    if not customer_id:
        raise ValueError("empty customer_id")

    try:
        amount = Decimal(amount_raw)
    except (InvalidOperation, ValueError):
        raise ValueError(f"amount is not a number: {amount_raw!r}")

    if amount < 0:
        raise ValueError(f"negative amount: {amount_raw!r}")

    dt = parse_date(created_raw)  # may raise ValueError

    month = dt.strftime("%Y-%m")
    return customer_id, month, amount, dt


def aggregate(path: str, report_stream) -> dict:
    """Read the CSV and return {(customer_id, month): total_amount}.

    Invalid rows are written to report_stream with their line number and reason.
    """
    totals: dict[tuple[str, str], Decimal] = defaultdict(lambda: Decimal("0"))
    valid_count = 0
    invalid_count = 0

    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)

        if reader.fieldnames is None:
            raise SystemExit(f"error: {path} is empty")

        missing = [c for c in REQUIRED_COLUMNS if c not in reader.fieldnames]
        if missing:
            raise SystemExit(
                f"error: {path} is missing required column(s): {', '.join(missing)}"
            )

        # DictReader consumes the header, so data starts at line 2.
        for line_no, row in enumerate(reader, start=2):
            try:
                customer_id, month, amount, _dt = validate_row(row)
            except ValueError as exc:
                invalid_count += 1
                order_hint = (row.get("order_id") or "").strip() or "?"
                print(
                    f"  line {line_no} (order_id={order_hint}): {exc}",
                    file=report_stream,
                )
                continue

            totals[(customer_id, month)] += amount
            valid_count += 1

    if invalid_count:
        print(
            f"\nSkipped {invalid_count} invalid row(s); kept {valid_count}.",
            file=report_stream,
        )
    else:
        print(f"All {valid_count} row(s) valid.", file=report_stream)

    return totals


def print_report(totals: dict, out_stream=sys.stdout) -> None:
    """Print revenue per customer per month, sorted by revenue (desc)."""
    if not totals:
        print("No valid rows to report.", file=out_stream)
        return

    # Sort by revenue descending, then customer_id, then month for stable output.
    rows = sorted(
        totals.items(),
        key=lambda item: (-item[1], item[0][0], item[0][1]),
    )

    cust_w = max(len("customer_id"), max(len(c) for (c, _m) in totals))
    header = f"{'customer_id':<{cust_w}}  {'month':<7}  {'revenue':>12}"
    print(header, file=out_stream)
    print("-" * len(header), file=out_stream)
    for (customer_id, month), revenue in rows:
        print(
            f"{customer_id:<{cust_w}}  {month:<7}  {revenue:>12,.2f}",
            file=out_stream,
        )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Revenue per customer per month from an orders CSV."
    )
    parser.add_argument(
        "path",
        nargs="?",
        default="orders.csv",
        help="path to the orders CSV (default: orders.csv)",
    )
    parser.add_argument(
        "--report-file",
        metavar="FILE",
        help="write the invalid-row report here instead of stderr",
    )
    args = parser.parse_args(argv)

    report_stream = sys.stderr
    report_fh = None
    if args.report_file:
        report_fh = open(args.report_file, "w", encoding="utf-8")
        report_stream = report_fh

    try:
        print("Invalid-row report:", file=report_stream)
        totals = aggregate(args.path, report_stream)
    except FileNotFoundError:
        print(f"error: file not found: {args.path}", file=sys.stderr)
        return 1
    finally:
        if report_fh is not None:
            report_fh.close()

    print_report(totals)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
