#!/usr/bin/env python3
import json
import argparse
import re
from typing import List, Dict, Any

def parse_line(line: str) -> Dict[str, Any] | None:
    """
    Parse a line into structured data.
    Customize this function based on your file format.
    """
    line = line.strip()
    if not line:
        return None
    
    # Dirb standard entry
    dirb_pattern = r'\+\s+\[(.+?)\]\((.+?)\)\s+\(CODE:(\d+).*?SIZE:(\d+)\)'
    match = re.match(dirb_pattern, line)
    if match:
        return {
            "raw_line": line,
            "type": "dirb_entry",
            "url": match.group(1),
            "full_url": match.group(2),
            "status_code": int(match.group(3)),
            "size": int(match.group(4))
        }
    
    # Dirb directory
    dir_pattern = r'==> DIRECTORY:\s+\[(.+?)\]'
    match = re.match(dir_pattern, line)
    if match:
        return {
            "raw_line": line,
            "type": "directory",
            "url": match.group(1),
            "full_url": match.group(1)
        }
    
    # Generic key:value (e.g., "Name: Value")
    kv_pattern = r'^(.+?):\s*(.+)$'
    match = re.match(kv_pattern, line)
    if match:
        return {
            "raw_line": line,
            "type": "key_value",
            "key": match.group(1).strip(),
            "value": match.group(2).strip()
        }
    
    # Fallback: store as raw text
    return {
        "raw_line": line,
        "type": "raw_text"
    }

def txt_to_json(input_file: str, output_file: str):
    """Convert text file to JSON with sequential IDs starting at 1 for each array."""
    entries: List[Dict[str, Any]] = []
    
    try:
        with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                parsed = parse_line(line)
                if parsed:
                    parsed["line_number"] = line_num
                    entries.append(parsed)
    except FileNotFoundError:
        print(f"❌ Error: File '{input_file}' not found")
        return
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return
    
    # **CRITICAL**: Reset and assign sequential IDs starting from 1 at beginning of array
    for i, entry in enumerate(entries, 1):  # enumerate(start=1) ensures IDs start at 1
        entry["id"] = i
    
    # Write JSON array
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)
        print(f"✅ Converted {len(entries)} entries from '{input_file}'")
        print(f"📁 Saved to '{output_file}'")
        print(f"🔢 IDs assigned: 1 through {len(entries)}")
    except Exception as e:
        print(f"❌ Error writing JSON: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert text file to JSON with sequential IDs")
    parser.add_argument("input", help="Input text file path")
    parser.add_argument("-o", "--output", default="output.json", 
                       help="Output JSON file (default: output.json)")
    args = parser.parse_args()
    
    txt_to_json(args.input, args.output)