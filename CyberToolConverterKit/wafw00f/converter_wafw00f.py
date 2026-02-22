#!/usr/bin/env python3
import argparse
import json
import os

def parse_args():
    parser = argparse.ArgumentParser(description="Parse Wafw00f JSON and add sequential IDs")
    parser.add_argument("input_file", help="Input Wafw00f JSON file")
    parser.add_argument("output_file", help="Output JSON file with IDs")
    return parser.parse_args()

def parse_wafw00f_json(wafw00f_data):
    """Parse Wafw00f JSON structure and extract WAF findings with IDs"""
    parsed_findings = []
    
    # Handle array of results
    if isinstance(wafw00f_data, list):
        results = wafw00f_data
    else:
        results = [wafw00f_data]
    
    for i, result in enumerate(results, 1):
        finding = {
            "id": i,
            "url": result.get("url", "unknown"),
            "detected": result.get("detected", False),
            "firewall": result.get("firewall", ""),
            "manufacturer": result.get("manufacturer", ""),
            "confidence": result.get("confidence", 0),
            "scan_date": result.get("timestamp", "")
        }
        parsed_findings.append(finding)
    
    return parsed_findings

def main():
    args = parse_args()
    
    # Check if input file exists
    if not os.path.exists(args.input_file):
        print(f"❌ Error: Input file '{args.input_file}' not found!")
        return
    
    # Read Wafw00f JSON
    try:
        with open(args.input_file, 'r') as f:
            wafw00f_data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON in '{args.input_file}': {e}")
        return
    
    # Parse and add IDs
    findings = parse_wafw00f_json(wafw00f_data)
    
    # Create output structure
    output = {
        "scan_info": {
            "scanner": "Wafw00f",
            "total_findings": len(findings),
            "input_file": args.input_file
        },
        "findings": findings
    }
    
    # Write to output file
    try:
        with open(args.output_file, 'w') as f:
            json.dump(output, f, indent=2)
        print(f"✅ Parsed {len(findings)} WAF findings from {args.input_file}")
        print(f"📄 Saved to {args.output_file}")
    except Exception as e:
        print(f"❌ Error writing to '{args.output_file}': {e}")

if __name__ == "__main__":
    main()