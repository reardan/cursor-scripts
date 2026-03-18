#!/usr/bin/env python3
"""
Process Cursor usage-events CSV and report total tokens used in the last 30 days.
"""

import csv
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional


def parse_date(s: str) -> Optional[datetime]:
    """Parse ISO date string to datetime (timezone-aware)."""
    s = s.strip().strip('"')
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def safe_int(s: str) -> int:
    """Parse string to int, return 0 for empty or invalid."""
    s = (s or "").strip().strip('"').replace(",", "")
    if not s or s in ("-", "Free"):
        return 0
    try:
        return int(s)
    except ValueError:
        return 0


def main():
    csv_path = Path.home() / "Downloads" / "usage-events-2026-03-18.csv"
    if not csv_path.exists():
        print(f"File not found: {csv_path}")
        return 1

    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    total_tokens = 0
    input_tokens = 0
    output_tokens = 0
    cache_read = 0
    row_count = 0

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if "Total Tokens" not in (reader.fieldnames or []):
            print("Expected 'Total Tokens' column not found.")
            return 1

        for row in reader:
            date_str = row.get("Date", "")
            dt = parse_date(date_str)
            if dt is None or dt < cutoff:
                continue

            total_tokens += safe_int(row.get("Total Tokens", ""))
            input_tokens += safe_int(row.get("Input (w/ Cache Write)", ""))
            output_tokens += safe_int(row.get("Output Tokens", ""))
            cache_read += safe_int(row.get("Cache Read", ""))
            row_count += 1

    print("Usage summary (last 30 days)")
    print("=" * 40)
    print(f"Events in range:     {row_count:,}")
    print(f"Input tokens:        {input_tokens:,}")
    print(f"Output tokens:       {output_tokens:,}")
    print(f"Cache read:          {cache_read:,}")
    print(f"Total tokens:        {total_tokens:,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
