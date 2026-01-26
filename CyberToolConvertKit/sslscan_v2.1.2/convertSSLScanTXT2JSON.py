#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path

def parse_sslscan_file(input_file: str, output_file: str):
    """Parse 270 sslscan entries with Heartbleed section."""
    
    with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Split blocks by "Connected to" pattern (look-ahead keeps full match)
    blocks = re.split(r'(?=Connected to \S+)', content)
    
    results = []
    entry_id = 1
    
    print(f"DEBUG: Found {len([b for b in blocks if b.strip()])} raw blocks")
    
    for block_idx, block_text in enumerate(blocks, 1):
        block_text = block_text.strip()
        if not block_text or not block_text.startswith('Connected to'):
            continue
            
        parsed = parse_single_sslscan_block(block_text, entry_id)
        
        # Only add valid entries (must have target)
        if parsed.get('target'):
            results.append(parsed)
            print(f"✅ [{entry_id}] {parsed['target']} (IP: {parsed.get('ip', 'N/A')})")
            entry_id += 1
        else:
            print(f"⚠️  Block {block_idx} skipped (no target found)")
    
    # Write JSON
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n🎉 SUCCESS: Parsed {len(results)}/{entry_id-1} entries")
    print(f"📁 Saved to: {output_file}")

def parse_single_sslscan_block(block_text: str, entry_id: int) -> dict:
    """Parse ONE complete sslscan block with Heartbleed support."""
    result = {
        "id": entry_id,
        "ip": None,
        "target": None,
        "port": 443,
        "sni": None,
        "protocols": {},
        "heartbleed": {},
        "ciphers": [],
        "certificate": {}
    }
    
    # 1. IP from "Connected to 87.250.250.16"
    ip_match = re.search(r'Connected to\s+(\S+)', block_text)
    result["ip"] = ip_match.group(1) if ip_match else None
    
    # 2. Target/Port/SNI from header
    header_match = re.search(r'Testing SSL server\s+(.+?)\s+on port\s+(\d+)\s+using SNI name\s+(.+?)(?=\n|$)', block_text, re.DOTALL)
    if header_match:
        result["target"] = header_match.group(1).strip()
        result["port"] = int(header_match.group(2))
        result["sni"] = header_match.group(3).strip()
    
    # 3. Protocols (SSLv2, TLSv1.0, etc.)
    proto_matches = re.findall(r'^(\w+(?:v?\d+\.?\d*))\s+(enabled|disabled)', block_text, re.MULTILINE)
    for proto, status in proto_matches:
        result["protocols"][proto] = status
    
    # 4. HEARTBLEED SECTION - CRITICAL FIX
    heartbleed_matches = re.findall(r'^(\w+(?:v?\d+\.?\d*))\s+(not vulnerable to heartbleed)', block_text, re.MULTILINE)
    for proto, status in heartbleed_matches:
        result["heartbleed"][proto] = status
    
    # Also catch vulnerable heartbleed (if any)
    vuln_heartbleed = re.search(r'(\w+(?:v?\d+\.?\d*))\s+(vulnerable to heartbleed)', block_text, re.MULTILINE)
    if vuln_heartbleed:
        result["heartbleed"][vuln_heartbleed.group(1)] = vuln_heartbleed.group(2)
    
    # 5. Ciphers
    cipher_matches = re.findall(r'^(Preferred|Accepted)\s+(\w+(?:v\d+\.\d+))\s+\d+\s+bits\s+(.+?)(?=\s+Curve|$)', block_text, re.MULTILINE)
    for status, proto, cipher in cipher_matches:
        result["ciphers"].append({
            "status": status,
            "protocol": proto,
            "cipher": cipher.strip()
        })
    
    # 6. Certificate details
    cert_patterns = {
        'signature_algorithm': r'Signature Algorithm:\s+(.+)',
        'rsa_key_strength': r'RSA Key Strength:\s+(.+)',
        'ecc_curve_name': r'ECC Curve Name:\s+(.+)',
        'ecc_key_strength': r'ECC Key Strength:\s+(.+)',
        'subject': r'Subject:\s+(.+)',
        'issuer': r'Issuer:\s+(.+)',
        'not_valid_before': r'Not valid before:\s+(.+)',
        'not_valid_after': r'Not valid after:\s+(.+)'
    }
    
    for key, pattern in cert_patterns.items():
        match = re.search(pattern, block_text)
        if match:
            result["certificate"][key] = match.group(1).strip()
    
    # 7. Altnames
    altnames_match = re.search(r'Altnames:\s+(.+?)(?=\n\nIssuer:|\n\nNot|$)', block_text, re.DOTALL)
    if altnames_match:
        altnames = [name.strip() for name in altnames_match.group(1).split(',') if name.strip()]
        result["certificate"]["altnames"] = altnames
    
    return result

def main():
    parser = argparse.ArgumentParser(description="Parse sslscan multi-entry text file")
    parser.add_argument("input_file", help="sslscan text file")
    parser.add_argument("output_file", help="Output JSON file")
    args = parser.parse_args()
    
    parse_sslscan_file(args.input_file, args.output_file)

if __name__ == "__main__":
    main()