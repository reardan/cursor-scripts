#!/usr/bin/env python3
"""
Process Cursor usage-events CSV and report total tokens used in the last 30 days.
Also estimates cost if the same usage had gone through Anthropic's raw API
(with prompt-cache pricing for cache reads).
"""

import csv
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

# Anthropic API $ per million tokens (input, cache_read, output). Cache = 90% off input.
ANTHROPIC_PRICING = {
    "opus": (5.00, 0.50, 25.00),   # Claude Opus 4.x
    "sonnet": (3.00, 0.30, 15.00), # Claude Sonnet 4.x
}


def model_tier(model: str) -> str:
    """Map CSV model name to pricing tier."""
    m = (model or "").strip().lower()
    if "opus" in m:
        return "opus"
    if "sonnet" in m or "composer" in m:
        return "sonnet"
    return "sonnet"  # default


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
    # Per-tier token counts for Anthropic cost: (input_wo_cache, cache_read, output)
    by_tier = defaultdict(lambda: {"input": 0, "cache": 0, "output": 0})

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
            inp = safe_int(row.get("Input (w/ Cache Write)", ""))
            inp_wo = safe_int(row.get("Input (w/o Cache Write)", ""))
            cache = safe_int(row.get("Cache Read", ""))
            out = safe_int(row.get("Output Tokens", ""))
            input_tokens += inp
            output_tokens += out
            cache_read += cache
            row_count += 1

            tier = model_tier(row.get("Model", ""))
            by_tier[tier]["input"] += inp_wo
            by_tier[tier]["cache"] += cache
            by_tier[tier]["output"] += out

    # Anthropic API cost estimate ($ per M tokens)
    anthropic_total = 0.0
    print("Usage summary (last 30 days)")
    print("=" * 40)
    print(f"Events in range:     {row_count:,}")
    print(f"Input tokens:        {input_tokens:,}")
    print(f"Output tokens:       {output_tokens:,}")
    print(f"Cache read:          {cache_read:,}")
    print(f"Total tokens:        {total_tokens:,}")
    print()
    print("Anthropic raw API cost estimate (with cache pricing)")
    print("=" * 40)
    for tier in sorted(by_tier.keys()):
        t = by_tier[tier]
        if t["input"] == 0 and t["cache"] == 0 and t["output"] == 0:
            continue
        inp_per_m, cache_per_m, out_per_m = ANTHROPIC_PRICING[tier]
        cost_inp = (t["input"] / 1_000_000) * inp_per_m
        cost_cache = (t["cache"] / 1_000_000) * cache_per_m
        cost_out = (t["output"] / 1_000_000) * out_per_m
        tier_total = cost_inp + cost_cache + cost_out
        anthropic_total += tier_total
        print(f"  {tier}: input ${cost_inp:.2f} + cache ${cost_cache:.2f} + output ${cost_out:.2f} = ${tier_total:.2f}")
    print("-" * 40)
    print(f"  Total (Anthropic API): ${anthropic_total:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
