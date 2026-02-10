#!/usr/bin/env python3
import json
import argparse
from typing import Dict, List, Any

def parse_dirb_output_comprehensive(path: str) -> Dict[str, Any]:
    entries: List[Dict[str, Any]] = []
    
    print(f"🔍 Reading ALL lines from: {path}")
    
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line_no, raw_line in enumerate(f, 1):
            line = raw_line.rstrip("\n").strip()
            if not line:  # Skip empty lines
                continue
                
            entry = {
                "id": len(entries) + 1,
                "line_number": line_no,
                "raw_line": line,
                "type": "unknown"
            }
            
            # 1. DIRB HIT: + [url](url) (CODE:xxx|SIZE:xxx)
            if line.startswith("+ ["):
                try:
                    # Extract [display_url]
                    start1 = line.find("[") + 1
                    end1 = line.find("]", start1)
                    display_url = line[start1:end1] if end1 > 0 else ""
                    
                    # Extract (full_url)
                    start2 = line.find("(", end1) + 1 if end1 > 0 else line.find("(") + 1
                    end2 = line.find(")", start2)
                    full_url = line[start2:end2] if end2 > 0 else ""
                    
                    # Extract CODE and SIZE
                    if "CODE:" in line and "SIZE:" in line:
                        code_start = line.find("CODE:") + 5
                        code_end = line.find("|", code_start)
                        size_start = line.find("SIZE:") + 5
                        
                        code = line[code_start:code_end].strip()
                        size = line[size_start:].strip()
                        
                        entry.update({
                            "type": "hit",
                            "url": display_url,
                            "full_url": full_url,
                            "status_code": code if code.isdigit() else None,
                            "size": size if size.isdigit() else None
                        })
                except:
                    pass
            
            # 2. DIRECTORY: ==> DIRECTORY: [url]
            elif "==> DIRECTORY:" in line:
                try:
                    start = line.find("[") + 1
                    end = line.find("]", start)
                    url = line[start:end] if end > 0 else ""
                    entry.update({
                        "type": "directory",
                        "url": url,
                        "full_url": url
                    })
                except:
                    pass
            
            # 3. METADATA lines
            elif ":" in line and not line.startswith("----"):
                parts = line.split(":", 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip()
                    entry.update({
                        "type": "metadata",
                        "key": key,
                        "value": value
                    })
            
            # 4. SCAN SCOPE
            elif "---- Scanning URL:" in line or "---- Entering directory:" in line:
                try:
                    start = line.find("[") + 1
                    end = line.find("]", start)
                    url = line[start:end] if end > 0 else ""
                    entry.update({
                        "type": "scope",
                        "url": url
                    })
                except:
                    pass
            
            # 5. WARNINGS
            elif line.startswith("(!) WARNING:"):
                entry["type"] = "warning"
            
            # 6. Everything else gets captured as "info"
            else:
                entry["type"] = "info"
            
            entries.append(entry)
    
    print(f"✅ Captured {len(entries)} TOTAL entries (every meaningful line)")
    return {
        "total_entries": len(entries),
        "results": entries
    }

def main():
    parser = argparse.ArgumentParser(description="Parse ALL dirb output to JSON")
    parser.add_argument("input", help="Dirb output file")
    parser.add_argument("-o", "--output", default="dirb_complete.json")
    args = parser.parse_args()

    try:
        data = parse_dirb_output_comprehensive(args.input)
        
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ SUCCESS: {args.output}")
        print(f"   📊 {len(data['results'])} total entries parsed!")
        print(f"   🎯 {len([e for e in data['results'] if e['type']=='hit'])} hits found")
        print(f"   📁 {len([e for e in data['results'] if e['type']=='directory'])} directories")
        
    except FileNotFoundError:
        print(f"❌ File '{args.input}' not found!")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()