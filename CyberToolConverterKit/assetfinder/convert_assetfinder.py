#!/usr/bin/env python3
import json
import argparse
from typing import List, Dict, Any

def parse_assetfinder_file(input_file: str) -> List[Dict[str, Any]]:
    """
    Parse assetfinder output file - one domain/subdomain per line.
    Identical format to subfinder/sublist3r output.
    """
    entries = []
    
    with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
        for line_num, line in enumerate(f, 1):
            raw_line = line.rstrip('\n')
            domain = raw_line.strip()
            
            # Skip empty lines and comments
            if not domain or domain.startswith('#'):
                continue
            
            entries.append({
                "id": len(entries) + 1,
                "line_number": line_num,
                "domain": domain,
                "raw_line": raw_line
            })
    
    return entries

def write_json(entries: List[Dict[str, Any]], output_file: str):
    """Write parsed entries to JSON file."""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Saved {len(entries)} assetfinder domains to {output_file}")

def main():
    parser = argparse.ArgumentParser(
        description="Parse assetfinder output → structured JSON with IDs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  convert_assetfinder.py assetfinder_yandex.txt
  convert_assetfinder.py assetfinder_yandex.txt -o yandex_assetfinder.json
        """
    )
    parser.add_argument("input", help="Assetfinder output text file (one domain per line)")
    parser.add_argument("-o", "--output", default="assetfinder_parsed.json",
                       help="Output JSON file (default: assetfinder_parsed.json)")
    args = parser.parse_args()
    
    entries = parse_assetfinder_file(args.input)
    
    if entries:
        print(f"📊 Parsed {len(entries)} domains")
        write_json(entries, args.output)
    else:
        print("❌ No valid domains found")

if __name__ == "__main__":
    main()
