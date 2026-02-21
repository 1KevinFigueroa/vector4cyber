# Nuclei Ingestor for Vector4Cyber

Uploads Nuclei vulnerability scan results to Qdrant vector database with automatic correlation to existing host and subdomain collections.

## Features

- ✅ **Automatic Correlation**: Links vulnerability findings to existing records in dnsx/nmap/whois collections
- ✅ **Semantic Embeddings**: Uses sentence-transformers (all-MiniLM-L6-v2) for vector similarity search
- ✅ **Vulnerability Tracking**: Severity-weighted risk scoring and CVE/CWE extraction
- ✅ **Upsert Mode**: Prevents duplicates, updates existing vulnerabilities
- ✅ **Payload Indexes**: Optimized for fast querying by template, host, severity, and CVE/CWE
- ✅ **Batch Processing**: Efficient batch uploads for large scan results
- ✅ **Fallback Embeddings**: Simple hash-based vectors if sentence-transformers not available

## Installation

### Required Dependencies

```bash
pip install qdrant-client
```

### Optional Dependencies (Recommended)

```bash
pip install sentence-transformers
```

Without sentence-transformers, the ingestor will use simple hash-based embeddings (less semantic meaning but functional).

## Usage

### Basic Usage

```bash
python ingest3r_nuclei.py nuclei_results.json
```

### With Custom Collection Name

```bash
python ingest3r_nuclei.py nuclei_results.json my_vulnerabilities
```

### With Custom Qdrant Connection

```bash
python ingest3r_nuclei.py nuclei_results.json --host 192.168.1.100 --port 6333
```

### Skip Correlation (Upload Only)

```bash
python ingest3r_nuclei.py nuclei_results.json --skip-correlation
```

### Omit Raw Request/Response (Save Space)

```bash
python ingest3r_nuclei.py nuclei_results.json --omit-raw
```

### Adjust Batch Size

```bash
python ingest3r_nuclei.py nuclei_results.json --batch-size 200
```

## Complete Workflow Example

```bash
# Step 1: Run nuclei scan with JSON output
nuclei -l targets.txt -o nuclei_results.json

# Or use -json-export for explicit JSON output
nuclei -l targets.txt -json-export nuclei_results.json

# Step 2: Ingest results into Qdrant
python ingest3r_nuclei.py nuclei_results.json

# Output:
# [INFO] Starting nuclei ingestor
# [INFO] Loaded 247 nuclei results
# [INFO] Connected to Qdrant
# [PROGRESS] Processed 100/247 results
# [PROGRESS] Processed 200/247 results
# ==================================================
# INGESTION COMPLETE
# ==================================================
# Total results:    247
# Inserted:         247
# Updated:          0
# Correlated:       189
# Errors:           0
#
# BY SEVERITY:
#   CRITICAL   12
#   HIGH       45
#   MEDIUM     98
#   LOW        67
#   INFO       25
# ==================================================
```

## Nuclei Output Format

The ingestor expects Nuclei JSON output. Use either:

```bash
# Default JSON output
nuclei -u https://example.com -o results.json

# Or explicit JSON export
nuclei -u https://example.com -json-export results.json
```

Each line in the JSON file is a separate JSON object containing:

```json
{
  "template-id": "CVE-2021-44228",
  "info": {
    "name": "Apache Log4j2 Remote Code Execution (Log4Shell)",
    "severity": "critical",
    "description": "Apache Log4j2...",
    "tags": ["cve", "cve2021", "log4j", "rce", "oast"]
  },
  "type": "http",
  "host": "example.com",
  "url": "https://example.com/api",
  "matched-at": "X-Api-Header: ${jndi:ldap://...",
  "timestamp": "2025-01-15T10:30:00Z",
  "request": "...",
  "response": "..."
}
```

## Vector Embeddings

### Text Representation

The ingestor creates a semantic text representation for embedding:

```
"Vulnerability: Apache Log4j2 Remote Code Execution
Template: CVE-2021-44228
Description: Apache Log4j2...
Severity: critical
Type: http
Host: example.com
URL: https://example.com/api
CVE: CVE-2021-44228"
```

### Embedding Models

- **Primary**: `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions)
- **Fallback**: SHA-256 hash-based deterministic vectors

### Vector Configuration

- **Size**: 384 (configurable with `--vector-size`)
- **Distance**: Cosine similarity
- **Collection**: `nuclei_results` (configurable)

## Payload Indexes

The ingestor automatically creates indexes on these fields for efficient querying:

| Field | Type | Purpose |
|-------|------|---------|
| `template_id` | Keyword | Find vulnerabilities by template |
| `host` | Keyword | Find vulnerabilities for a host |
| `url` | Keyword | Find vulnerabilities at specific URL |
| `severity` | Keyword | Filter by severity level |
| `type` | Keyword | Filter by protocol type |
| `matched_at` | Keyword | Search by matched content |
| `timestamp` | Keyword | Time-based filtering |
| `cve_id` | Keyword | Find by CVE identifier |
| `cwe_id` | Keyword | Find by CWE identifier |
| `correlation_status` | Keyword | Filter correlated results |
| `ip` | Keyword | Find by IP address |

## Query Examples

### Find All Vulnerabilities for a Host

```python
from qdrant_client import QdrantClient
from qdrant_client.http import models

client = QdrantClient("localhost", port=6333)

results = client.scroll(
    collection_name="nuclei_results",
    scroll_filter=models.Filter(
        must=[
            models.FieldCondition(
                key="host",
                match=models.MatchValue(value="example.com")
            )
        ]
    )
)
```

### Find Critical Vulnerabilities

```python
results = client.scroll(
    collection_name="nuclei_results",
    scroll_filter=models.Filter(
        must=[
            models.FieldCondition(
                key="severity",
                match=models.MatchValue(value="critical")
            )
        ]
    )
)
```

### Find by CVE ID

```python
results = client.scroll(
    collection_name="nuclei_results",
    scroll_filter=models.Filter(
        must=[
            models.FieldCondition(
                key="cve_id",
                match=models.MatchValue(value="CVE-2021-44228")
            )
        ]
    )
)
```

### Semantic Search for Similar Vulnerabilities

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
query_vector = model.encode("SQL injection vulnerabilities in login forms")

results = client.search(
    collection_name="nuclei_results",
    query_vector=query_vector.tolist(),
    limit=10
)
```

### Find High-Risk Hosts (Multiple Critical/High Vulns)

```python
# Scroll through all results and aggregate by host
results = client.scroll(
    collection_name="nuclei_results",
    scroll_filter=models.Filter(
        should=[
            models.FieldCondition(key="severity", match=models.MatchValue(value="critical")),
            models.FieldCondition(key="severity", match=models.MatchValue(value="high"))
        ]
    ),
    with_payload=True
)

# Aggregate by host
host_risk = {}
for point in results[0]:
    host = point.payload.get("host", "unknown")
    if host not in host_risk:
        host_risk[host] = {"critical": 0, "high": 0, "risk_score": 0}
    
    severity = point.payload.get("severity")
    if severity == "critical":
        host_risk[host]["critical"] += 1
        host_risk[host]["risk_score"] += 10
    elif severity == "high":
        host_risk[host]["high"] += 1
        host_risk[host]["risk_score"] += 7

# Sort by risk score
sorted_hosts = sorted(host_risk.items(), key=lambda x: x[1]["risk_score"], reverse=True)
```

## Correlation Logic

The ingestor automatically correlates vulnerability findings with:

1. **dnsx_records**: Matches by hostname
2. **nmap_results**: Matches by host
3. **whois_records**: Matches by domain
4. **subdomains_collection**: Matches by hostname

When correlation succeeds, the vulnerability record includes:

```json
{
  "correlation_status": "matched",
  "linked_record_id": 42,
  "linked_collection": "dnsx_records"
}
```

## Command-Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `input_file` | Path to nuclei JSON file | (required) |
| `collection_name` | Qdrant collection name | `nuclei_results` |
| `--host` | Qdrant server host | `localhost` |
| `--port` | Qdrant server port | `6333` |
| `--vector-size` | Vector embedding size | `384` |
| `--batch-size` | Records per batch upload | `100` |
| `--skip-correlation` | Disable auto-correlation | `False` |
| `--omit-raw` | Omit request/response data | `False` |

## Dependencies

- `qdrant-client` (required)
- `sentence-transformers` (optional, recommended)

## Troubleshooting

### "Failed to connect to Qdrant"

- Verify Qdrant is running: `docker ps | grep qdrant`
- Check host/port: default is `localhost:6333`
- Test connection: `curl http://localhost:6333/collections`

### No Correlations Found

- Ensure host collections exist in Qdrant (dnsx_records, nmap_results, etc.)
- Check that hostnames match exactly
- Verify host collections were ingested before running nuclei ingestor

### Slow Performance

- Increase `--batch-size` (default 100, try 500)
- Ensure payload indexes were created
- Use `--omit-raw` if you don't need request/response data
- Check Qdrant server resources

### Memory Issues with Large Scans

- Use `--omit-raw` to reduce payload size
- Split large JSONL files into smaller batches
- Increase batch size for fewer upsert operations

## Architecture

```
nuclei_results.json
        │
        ▼
┌─────────────────┐
│ ingest3r_nuclei │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌────────┐  ┌──────────────────┐
│Embed   │  │Correlation Engine│
│384-dim │  └────────┬─────────┘
│Cosine  │           │
└────┬───┘     ┌─────┴─────┐
     │         ▼           ▼
     │    ┌────────┐  ┌────────┐
     │    │dnsx    │  │nmap    │
     │    │records │  │results │
     │    └────────┘  └────────┘
     │
     ▼
┌─────────────────┐
│  nuclei_results │
│  (Qdrant)       │
│  Upsert Mode    │
└─────────────────┘
```

## See Also

- [Nuclei Documentation](https://docs.projectdiscovery.io/opensource/nuclei/overview)
- [Nuclei Templates](https://github.com/projectdiscovery/nuclei-templates)
- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [sentence-transformers](https://www.sbert.net/)
