#!/usr/bin/env python3
"""
dnsx JSON Converter for Vector4Cyber

Converts ProjectDiscovery dnsx JSONL output to standardized JSON format
with correlation support for Vector4Cyber pipeline.

Usage:
    python convert_dnsxJSON.py input.jsonl output.json

Input: dnsx -json output (JSON Lines format)
Output: Standardized JSON array with ids and correlation fields
"""

import json
import argparse
from datetime import datetime
from typing import Dict, List, Any


def parse_args():
    parser = argparse.ArgumentParser(
        description="Convert dnsx JSONL output to Vector4Cyber standardized JSON format"
    )
    parser.add_argument(
        "input_file", help="Path to dnsx JSONL output file (one JSON object per line)"
    )
    parser.add_argument("output_file", help="Path to output JSON file")
    parser.add_argument(
        "--timestamp",
        help="Override timestamp (ISO format). Defaults to current time",
        default=None,
    )
    return parser.parse_args()


def normalize_dns_records(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize dnsx record to ensure all DNS types are lists and standardized.

    Handles all dnsx DNS record types:
    - a, aaaa, cname, mx, ns, txt, soa, srv, ptr, caa
    """
    normalized = {}

    # DNS record types that should always be lists
    dns_types = ["a", "aaaa", "cname", "mx", "ns", "txt", "soa", "srv", "ptr", "caa"]

    for dns_type in dns_types:
        value = record.get(dns_type)
        if value is None:
            normalized[dns_type] = []
        elif isinstance(value, list):
            normalized[dns_type] = value
        else:
            # Single value should be wrapped in list
            normalized[dns_type] = [value]

    return normalized


def convert_dnsx_record(
    record: Dict[str, Any], record_id: int, timestamp: str
) -> Dict[str, Any]:
    """
    Convert a single dnsx record to Vector4Cyber standardized format.
    """
    # Normalize DNS records
    dns_data = normalize_dns_records(record)

    # Build standardized record
    converted = {
        "id": record_id,
        "host": record.get("host", ""),
        "resolver": record.get("resolver", []),
        "status_code": record.get("status_code", "UNKNOWN"),
        "timestamp": timestamp,
        "source_tool": "dnsx",
    }

    # Add normalized DNS records
    converted.update(dns_data)

    # Preserve raw response for traceability
    converted["raw_response"] = record

    return converted


def main():
    args = parse_args()

    # Use provided timestamp or current time
    timestamp = args.timestamp or datetime.utcnow().isoformat() + "Z"

    results = []
    next_id = 1

    print(f"[INFO] Converting dnsx JSONL file: {args.input_file}")

    try:
        with open(args.input_file, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    record = json.loads(line)
                except json.JSONDecodeError as e:
                    print(f"[WARNING] Skipping invalid JSON on line {line_num}: {e}")
                    continue

                # Convert record
                converted = convert_dnsx_record(record, next_id, timestamp)
                results.append(converted)
                next_id += 1

    except FileNotFoundError:
        print(f"[ERROR] Input file not found: {args.input_file}")
        return 1
    except Exception as e:
        print(f"[ERROR] Failed to process input file: {e}")
        return 1

    # Write output
    try:
        with open(args.output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)

        print(f"[SUCCESS] Converted {len(results)} DNS records to: {args.output_file}")

        # Print summary statistics
        record_types_found = set()
        for record in results:
            for dns_type in [
                "a",
                "aaaa",
                "cname",
                "mx",
                "ns",
                "txt",
                "soa",
                "srv",
                "ptr",
                "caa",
            ]:
                if record.get(dns_type):
                    record_types_found.add(dns_type)

        print(f"[INFO] DNS record types found: {', '.join(sorted(record_types_found))}")

    except Exception as e:
        print(f"[ERROR] Failed to write output file: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
