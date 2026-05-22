#!/usr/bin/env python3
"""Convert ProjectDiscovery dnsx JSONL output to Vector4Cyber JSON records."""

from __future__ import annotations

import argparse
import json
import sys
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

DNS_RECORD_FIELDS = ("a", "aaaa", "cname", "mx", "ns", "txt", "soa", "srv", "ptr", "caa")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="convert3r_dnsx.py",
        description="Convert dnsx -json JSONL output to Vector4Cyber JSON records",
    )
    parser.add_argument("input_file", help="Path to dnsx JSONL output")
    parser.add_argument(
        "-o",
        "--output-file",
        dest="output_file",
        help="Output JSON path (default: enriched_<input>.json)",
    )
    parser.add_argument(
        "--timestamp",
        help="Override timestamp for converted records (defaults to current UTC time)",
    )
    return parser.parse_args()


def _as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def normalize_dns_records(record: Dict[str, Any]) -> Dict[str, List[Any]]:
    """Return dnsx DNS record fields with every value normalized to a list."""
    return {field: _as_list(record.get(field)) for field in DNS_RECORD_FIELDS}


def convert_dnsx_record(record: Dict[str, Any], record_id: int, timestamp: str) -> OrderedDict:
    """Convert one dnsx JSON object to the repo's enriched JSON shape."""
    converted: OrderedDict[str, Any] = OrderedDict()
    converted["id"] = record_id
    converted["host"] = str(record.get("host") or record.get("input") or "").strip()
    converted["resolver"] = _as_list(record.get("resolver"))
    converted["status_code"] = record.get("status_code", "UNKNOWN")
    converted["timestamp"] = timestamp
    converted["source_tool"] = "dnsx"

    for key, value in normalize_dns_records(record).items():
        converted[key] = value

    converted["raw_response"] = record
    return converted


def convert_dnsx_jsonl(lines: Iterable[str], timestamp: str | None = None) -> Tuple[List[OrderedDict], int]:
    """Convert JSONL text lines; return converted records and skipped-line count."""
    effective_timestamp = timestamp or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    records: List[OrderedDict] = []
    skipped = 0

    for line_num, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line:
            skipped += 1
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError as exc:
            print(f"⚠️ Skipping invalid JSON on line {line_num}: {exc}", file=sys.stderr)
            skipped += 1
            continue
        if not isinstance(parsed, dict):
            print(f"⚠️ Skipping non-object JSON on line {line_num}", file=sys.stderr)
            skipped += 1
            continue
        records.append(convert_dnsx_record(parsed, len(records) + 1, effective_timestamp))

    return records, skipped


def write_json_atomic(records: List[OrderedDict], output_file: str) -> None:
    output = Path(output_file)
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_name(output.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(records, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    tmp.replace(output)


def main() -> int:
    args = parse_args()
    input_path = Path(args.input_file)
    if not input_path.is_file():
        print(f"❌ Input file not found: {input_path}", file=sys.stderr)
        return 1

    output_file = args.output_file or f"enriched_{input_path.stem}.json"

    try:
        with input_path.open("r", encoding="utf-8") as handle:
            records, skipped = convert_dnsx_jsonl(handle, timestamp=args.timestamp)
        write_json_atomic(records, output_file)
    except OSError as exc:
        print(f"❌ File error: {exc}", file=sys.stderr)
        return 1

    found_types = sorted({field for record in records for field in DNS_RECORD_FIELDS if record.get(field)})
    print(f"✅ Converted {len(records)} dnsx records → {output_file}")
    print(f"ℹ️ Skipped {skipped} input lines")
    print(f"📊 DNS record types found: {', '.join(found_types) if found_types else 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
