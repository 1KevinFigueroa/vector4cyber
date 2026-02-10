#!/usr/bin/env python3
import json
import argparse
from typing import List, Dict, Any

def parse_sublist3r_file(input_file: str) -> List[Dict[str, Any]]:
    """Parse sublist3r output file - one subdomain per line."""
    domains = []
    
    try:
        with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                domain = line.strip()
                if domain and not domain.startswith('#'):  # Skip comments/empty lines
                    domains.append({
                        "id": len(domains) + 1,
                        "line_number": line_num,
                        "domain": domain,
                        "raw_line": line.rstrip('\n')
                    })
    except FileNotFoundError:
        print(f"❌ File '{input_file}' not found")
        return []
    
    return domains

def write_json(domains: List[Dict[str, Any]], output_file: str):
    """Write domains as JSON array."""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(domains, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Saved {len(domains)} subdomains to {output_file}")

def main():
    parser = argparse.ArgumentParser(description="Convert sublist3r txt to JSON with IDs")
    parser.add_argument("input_file", help="Sublist3r output txt file")
    parser.add_argument("-o", "--output", default="sublist3r_domains.json", 
                       help="Output JSON file")
    args = parser.parse_args()
    
    domains = parse_sublist3r_file(args.input_file)
    
    if domains:
        write_json(domains, args.output)
        print(f"📊 Summary:")
        print(f"   Total domains: {len(domains)}")
    else:
        print("❌ No domains found in input file")

if __name__ == "__main__":
    main()