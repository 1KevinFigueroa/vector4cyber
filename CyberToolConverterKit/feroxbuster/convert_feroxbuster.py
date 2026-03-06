#!/usr/bin/env python3
import json
import argparse
from typing import List, Dict, Any

def parse_feroxbuster_json(input_file: str) -> List[Dict[str, Any]]:
    """
    Parse feroxbuster JSON output file (newline-delimited JSON).
    Each line is a JSON object with fields like type, url, status, etc.
    """
    entries = []
    
    with open(input_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                # Parse each line as a separate JSON object
                entry = json.loads(line)
                
                # Skip non-response entries (logs, stats, etc.)
                if entry.get("type") != "response":
                    continue
                
                # Add ID and line number
                enriched = {
                    "id": len(entries) + 1,
                    "line_number": line_num,
                    "original_json": entry,
                    **entry  # Spread original fields
                }
                
                entries.append(enriched)
                
            except json.JSONDecodeError as e:
                print(f"⚠️ Skipping invalid JSON on line {line_num}: {e}")
                continue
    
    return entries

def write_json(entries: List[Dict[str, Any]], output_file: str):
    """Write parsed entries to a new JSON file."""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Saved {len(entries)} Feroxbuster responses to {output_file}")

def main():
    parser = argparse.ArgumentParser(
        description="Parse feroxbuster JSON output → structured JSON with IDs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  convert_feroxbuster.py feroxbuster_yandex.json
  convert_feroxbuster.py feroxbuster_yandex.json -o yandex_ferox.json
        """
    )
    parser.add_argument("input", help="Feroxbuster JSON output file (--json)")
    parser.add_argument("-o", "--output", default="feroxbuster_parsed.json",
                       help="Output JSON file (default: feroxbuster_parsed.json)")
    args = parser.parse_args()
    
    entries = parse_feroxbuster_json(args.input)
    
    if entries:
        print(f"📊 Parsed {len(entries)} response entries")
        write_json(entries, args.output)
        
        # Summary stats
        codes = [e.get('status', 'unknown') for e in entries]
        print(f"   HTTP 200: {codes.count(200)}")
        print(f"   HTTP 301/302: {codes.count(301) + codes.count(302)}")
        print(f"   HTTP 403: {codes.count(403)}")
    else:
        print("❌ No valid response entries found")

if __name__ == "__main__":
    main()
