# dnsx Converter for Vector4Cyber

Converts ProjectDiscovery dnsx JSONL output to standardized Vector4Cyber JSON format.

## Overview

This converter processes dnsx DNS resolution output and prepares it for ingestion into the Vector4Cyber vector database pipeline. It supports all dnsx DNS record types and maintains correlation capabilities with existing subdomain data.

## Features

- ✅ Supports all dnsx DNS record types: A, AAAA, CNAME, MX, NS, TXT, SOA, SRV, PTR, CAA
- ✅ Normalizes DNS records to consistent list format
- ✅ Adds sequential IDs for Vector4Cyber compatibility
- ✅ Preserves raw dnsx response for traceability
- ✅ Handles multiple resolvers
- ✅ Timestamp tracking
- ✅ Correlation-ready (prepares `linked_subdomain_id` field for ingestor)

## Installation

No additional dependencies required. Uses Python standard library only.

## Usage

### Basic Usage

```bash
# Run dnsx to get JSON output
cat subdomains.txt | dnsx -json -o dnsx_output.jsonl

# Convert to Vector4Cyber format
python convert_dnsxJSON.py dnsx_output.jsonl dns_enriched.json
```

### With Custom Timestamp

```bash
python convert_dnsxJSON.py dnsx_output.jsonl dns_enriched.json --timestamp "2025-01-15T10:30:00Z"
```

## Input Format

Expected input is JSON Lines (JSONL) format from `dnsx -json`:

```jsonl
{"host":"www.example.com","resolver":["1.1.1.1:53"],"a":["93.184.216.34"],"status_code":"NOERROR"}
{"host":"mail.example.com","resolver":["8.8.8.8:53"],"mx":["mail.example.com"],"status_code":"NOERROR"}
```

## Output Format

Standardized JSON array with correlation fields:

```json
[
  {
    "id": 1,
    "host": "www.example.com",
    "resolver": ["1.1.1.1:53"],
    "status_code": "NOERROR",
    "timestamp": "2025-01-15T10:30:00Z",
    "source_tool": "dnsx",
    "a": ["93.184.216.34"],
    "aaaa": [],
    "cname": [],
    "mx": [],
    "ns": [],
    "txt": [],
    "soa": [],
    "srv": [],
    "ptr": [],
    "caa": [],
    "raw_response": { ... }
  }
]
```

## Workflow Integration

```bash
# Step 1: Discover subdomains
subfinder -d example.com -o subs.txt

# Step 2: Convert subdomains
python ../subfinder/subfinder_TXToutput/convert_subfinderTXToutput.py subs.txt subs.json

# Step 3: Ingest subdomains
python ../../ingest3rs/sublist3r/ingest3r_sublist3r.py subs.json subdomains_collection

# Step 4: Run dnsx enrichment
cat subs.txt | dnsx -json -o dnsx_output.jsonl

# Step 5: Convert dnsx output
python convert_dnsxJSON.py dnsx_output.jsonl dns_enriched.json

# Step 6: Ingest with auto-correlation
python ../../ingest3rs/dnsx/ingest3r_dnsx.py dns_enriched.json
```

## DNS Record Types Supported

| Type | Description | Example |
|------|-------------|---------|
| A | IPv4 address | `"a": ["93.184.216.34"]` |
| AAAA | IPv6 address | `"aaaa": ["2606:2800:220:1::1"]` |
| CNAME | Canonical name | `"cname": ["alias.example.com"]` |
| MX | Mail exchange | `"mx": ["mail.example.com"]` |
| NS | Name server | `"ns": ["ns1.example.com"]` |
| TXT | Text record | `"txt": ["v=spf1 ..."]` |
| SOA | Start of authority | `"soa": [{"ns": "ns1..."}]` |
| SRV | Service locator | `"srv": [...]` |
| PTR | Pointer (reverse DNS) | `"ptr": ["host.example.com"]` |
| CAA | Certification Authority Authorization | `"caa": [...]` |

## Error Handling

- Invalid JSON lines are skipped with warnings
- Missing DNS record types are normalized to empty lists
- File not found errors are reported clearly

## Notes

- Output is always an array of objects (not JSONL)
- All DNS record fields are normalized to arrays (even single values)
- Raw response is preserved for debugging and audit trails
- IDs are sequential starting from 1

## See Also

- [dnsx Documentation](https://docs.projectdiscovery.io/opensource/dnsx/usage)
- [Vector4Cyber Ingestor](../../ingest3rs/dnsx/) - For uploading converted data to Qdrant
