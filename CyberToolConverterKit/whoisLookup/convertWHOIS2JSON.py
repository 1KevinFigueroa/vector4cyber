#!/usr/bin/env python3
import argparse
import json
import whois
import sys
from datetime import datetime
from pathlib import Path

def whois_to_json(domain, entry_id):
    """
    Perform WHOIS lookup and return structured JSON data with ID.
    """
    try:
        w = whois.whois(domain)
        
        # Structured JSON output with ID
        result = {
            "id": entry_id,
            "domain": domain,
            "timestamp": datetime.now().isoformat(),
            "whois_data": {
                "domain_name": getattr(w, 'domain', None),
                "registrar": getattr(w, 'registrar', None),
                "creation_date": str(getattr(w, 'creation_date', None)),
                "expiration_date": str(getattr(w, 'expiration_date', None)),
                "updated_date": str(getattr(w, 'updated_date', None)),
                "name_servers": getattr(w, 'name_servers', None),
                "status": getattr(w, 'status', None),
                "emails": getattr(w, 'emails', None),
                "country": getattr(w, 'country', None),
                "state": getattr(w, 'state', None),
                "city": getattr(w, 'city', None),
                "organization": getattr(w, 'org', None),
                "registrant": {
                    "name": getattr(w, 'name', None),
                    "organization": getattr(w, 'registrant_organization', None),
                    "street": getattr(w, 'address', None),
                    "city": getattr(w, 'city', None),
                    "state": getattr(w, 'state', None),
                    "postal_code": getattr(w, 'postal_code', None),
                    "country": getattr(w, 'country', None)
                }
            },
            "raw_whois": getattr(w, 'text', None)
        }
        
        return result
        
    except Exception as e:
        return {
            "id": entry_id,
            "domain": domain,
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "whois_data": None,
            "raw_whois": None
        }

def main():
    parser = argparse.ArgumentParser(description="WHOIS Lookup to JSON with IDs")
    parser.add_argument("domains", nargs="+", help="Domain(s) to query")
    parser.add_argument("-o", "--output", required=True, help="Output JSON file")
    parser.add_argument("-t", "--timeout", type=int, default=10, help="Timeout (seconds)")
    
    args = parser.parse_args()
    
    # Collect all results with sequential IDs
    all_results = []
    entry_id = 1  # Start ID counter from 1
    
    print(f"Querying WHOIS for {len(args.domains)} domains...")
    
    for domain in args.domains:
        domain = domain.strip().lower()
        print(f"  [{entry_id}] Looking up {domain}...")
        result = whois_to_json(domain, entry_id)
        all_results.append(result)
        entry_id += 1  # Increment ID for next entry
    
    # Write to JSON file
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\nResults saved to: {output_path.absolute()}")
    print(f"Processed {len(all_results)} domains with IDs 1-{entry_id-1}")

if __name__ == "__main__":
    main()