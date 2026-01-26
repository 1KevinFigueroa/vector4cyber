#!/usr/bin/env python3
"""
Convert text file of domains/subdomains into structured JSON format.
Input: one domain per line
Output: [{"id": 1, "hostname": "<domain>"}, {"id": 2, "hostname": "<domain>"}, ...]

Usage: python domains_to_json.py input_domains.txt output.json
"""

import json
import sys
import os
from typing import List, Dict

def domains_to_json(input_file: str, output_file: str = None) -> None:
    """
    Read domains from text file, assign sequential IDs, write to JSON.
    """
    # Read domains from file (one per line)
    print(f"📖 Reading domains from: {input_file}")
    with open(input_file, 'r', encoding='utf-8') as f:
        domains = [line.strip() for line in f.readlines() if line.strip()]
    
    print(f"✓ Found {len(domains)} domains")
    
    # Create structured JSON records
    records = []
    for i, domain in enumerate(domains, start=1):
        records.append({
            "id": i,
            "hostname": domain
        })
    
    # Write to JSON file
    if output_file is None:
        base_name = os.path.splitext(input_file)[0]
        output_file = f"{base_name}.json"
    
    print(f"💾 Writing JSON to: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Created JSON with {len(records)} records")
    print("\n📋 Sample output:")
    for record in records[:5]:
        print(f"  {json.dumps(record)}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python domains_to_json.py input_domains.txt [output.json]")
        print("Default output: input_domains.json")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not os.path.exists(input_file):
        print(f"❌ Error: File '{input_file}' not found!")
        sys.exit(1)
    
    try:
        domains_to_json(input_file, output_file)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()