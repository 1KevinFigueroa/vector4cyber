# dnsx Ingestor for Vector4Cyber

Uploads converted dnsx DNS records to Qdrant vector database with automatic correlation to existing subdomain collections and latest-only tracking.

## Features

- ✅ **Automatic Correlation**: Links DNS records to existing subdomains in subfinder/sublist3r/amass collections
- ✅ **Latest-Only Tracking**: Upsert mode prevents duplicates, keeps most recent DNS data
- ✅ **Semantic Embeddings**: Uses sentence-transformers (all-MiniLM-L6-v2) for vector similarity search
- ✅ **Bidirectional Linking**: Updates both DNS records and subdomain records with cross-references
- ✅ **Payload Indexes**: Optimized for fast querying by hostname, IP, and correlation status
- ✅ **Batch Processing**: Efficient batch uploads for large datasets
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
python ingest3r_dnsx.py dns_enriched.json
```

### With Custom Collection Name

```bash
python ingest3r_dnsx.py dns_enriched.json my_dns_collection
```

### With Custom Qdrant Connection

```bash
python ingest3r_dnsx.py dns_enriched.json --host 192.168.1.100 --port 6333
```

### Skip Correlation (Upload Only)

```bash
python ingest3r_dnsx.py dns_enriched.json --skip-correlation
```

### Target Specific Collections for Correlation

```bash
python ingest3r_dnsx.py dns_enriched.json --correlation-collections subfinder my_custom_subdomains
```

### Adjust Batch Size

```bash
python ingest3r_dnsx.py dns_enriched.json --batch-size 50
```

## Complete Workflow Example

```bash
# Step 1: Discover subdomains
subfinder -d example.com -o subs.txt

# Step 2: Convert subdomains
python ../../CyberToolConverterKit/subfinder/subfinder_TXToutput/convert_subfinderTXToutput.py subs.txt subs.json

# Step 3: Ingest subdomains into Qdrant
python ../sublist3r/ingest3r_sublist3r.py subs.json subdomains_collection

# Step 4: Run dnsx enrichment
cat subs.txt | dnsx -json -o dnsx_output.jsonl

# Step 5: Convert dnsx output
python ../../CyberToolConverterKit/dnsx/convert_dnsxJSON.py dnsx_output.jsonl dns_enriched.json

# Step 6: Ingest with auto-correlation
python ingest3r_dnsx.py dns_enriched.json

# Output:
# [INFO] Starting dnsx ingestor
# [INFO] Loaded 150 DNS records
# [INFO] Connected to Qdrant
# [INFO] Auto-correlation enabled for collections: subdomains_collection, subfinder, sublist3r, amass
# [CORRELATION] Matched 'www.example.com' to subdomains_collection ID 42
# [UPDATE] Updated subdomain ID 42 with DNS info
# ...
# ==================================================
# INGESTION COMPLETE
# ==================================================
# Total records:    150
# Inserted:         75
# Updated:          75
# Correlated:       142
# Errors:           0
#
# CORRELATION STATS:
# Matched:          142
# Unmatched:        8
# Subdomains updated: 142
# ==================================================
```

## How Correlation Works

### 1. Subdomain Matching

For each DNS record, the ingestor searches for a matching hostname across configured subdomain collections:

```python
# Searches in order:
1. subdomains_collection
2. subfinder
3. sublist3r
4. amass
```

### 2. Bidirectional Linking

When a match is found:

**DNS Record gets:**
```json
{
  "linked_subdomain_id": 42,
  "linked_collection": "subdomains_collection",
  "correlation_status": "matched",
  "resolved_ips": ["93.184.216.34"]
}
```

**Subdomain Record gets:**
```json
{
  "latest_dns_record_id": 15,
  "latest_dns_timestamp": "2025-01-15T10:30:00Z",
  "resolved_ips": ["93.184.216.34"],
  "dns_correlation_status": "active"
}
```

### 3. Latest-Only Tracking (Upsert)

If a DNS record for a hostname already exists:
- **Update** the existing record with new data
- **Keep the same point ID** (prevents duplicates)
- **Preserve correlation links** (if any)

If no existing record:
- **Insert** new record with next available ID

## Vector Embeddings

### Text Representation

The ingestor creates a text representation of each DNS record for embedding:

```
"{host} A:{a_records} AAAA:{aaaa_records} CNAME:{cname} MX:{mx_records} NS:{ns_records} TXT:{txt_records}"
```

Example:
```
"mail.example.com A:93.184.216.35 MX:mail.example.com TXT:v=spf1 include:_spf.example.com ~all"
```

### Embedding Models

- **Primary**: `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions)
- **Fallback**: SHA-256 hash-based deterministic vectors

### Vector Configuration

- **Size**: 384 (configurable with `--vector-size`)
- **Distance**: Cosine similarity
- **Collection**: `dnsx_records` (configurable)

## Payload Indexes

The ingestor automatically creates indexes on these fields for efficient querying:

| Field | Type | Purpose |
|-------|------|---------|
| `host` | Keyword | Find DNS records by hostname |
| `a` | Keyword | Find records by IPv4 address |
| `mx` | Keyword | Find records by mail server |
| `cname` | Keyword | Find CNAME chains |
| `linked_subdomain_id` | Keyword | Cross-collection joins |
| `timestamp` | Keyword | Time-based filtering |
| `correlation_status` | Keyword | Filter matched/unmatched |

## Query Examples

### Find All DNS Records for a Host

```python
from qdrant_client import QdrantClient

client = QdrantClient("localhost", port=6333)

results = client.scroll(
    collection_name="dnsx_records",
    scroll_filter=models.Filter(
        must=[
            models.FieldCondition(
                key="host",
                match=models.MatchValue(value="www.example.com")
            )
        ]
    )
)
```

### Find Subdomains Resolving to an IP

```python
results = client.scroll(
    collection_name="dnsx_records",
    scroll_filter=models.Filter(
        must=[
            models.FieldCondition(
                key="a",
                match=models.MatchValue(value="93.184.216.34")
            )
        ]
    )
)
```

### Find CNAME Takeover Candidates

```python
results = client.scroll(
    collection_name="dnsx_records",
    scroll_filter=models.Filter(
        must=[
            models.FieldCondition(
                key="cname",
                match=models.MatchText(text="herokudns.com")
            )
        ]
    )
)
```

### Semantic Search for Similar DNS Configurations

```python
# Find DNS records similar to "mail servers with SPF"
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
query_vector = model.encode("mail servers with SPF records")

results = client.search(
    collection_name="dnsx_records",
    query_vector=query_vector.tolist(),
    limit=10
)
```

## Command-Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `input_file` | Path to converted dnsx JSON file | (required) |
| `collection_name` | Qdrant collection name | `dnsx_records` |
| `--host` | Qdrant server host | `localhost` |
| `--port` | Qdrant server port | `6333` |
| `--vector-size` | Vector embedding size | `384` |
| `--batch-size` | Records per batch upload | `100` |
| `--skip-correlation` | Disable auto-correlation | `False` |
| `--correlation-collections` | Specific collections to search | All default |

## Dependencies

- `qdrant-client` (required)
- `sentence-transformers` (optional, recommended)
- `correlation_engine.py` (must be in same directory)

## Troubleshooting

### "correlation_engine.py not found"

Ensure `correlation_engine.py` is in the same directory as `ingest3r_dnsx.py`.

### "Failed to connect to Qdrant"

- Verify Qdrant is running: `docker ps | grep qdrant`
- Check host/port: default is `localhost:6333`
- Test connection: `curl http://localhost:6333/collections`

### No Correlations Found

- Ensure subdomain collections exist in Qdrant
- Check that hostnames match exactly (case-sensitive)
- Verify subdomains were ingested before running dnsx ingestor

### Slow Performance

- Increase `--batch-size` (default 100, try 500)
- Ensure payload indexes were created
- Check Qdrant server resources

## Architecture

```
dns_enriched.json
       │
       ▼
┌─────────────────┐
│  ingest3r_dnsx  │
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
     │    ┌─────────┐ ┌───────────┐
     │    │subfinder│ │sublist3r  │
     │    │amass    │ │subdomains │
     │    └─────────┘ └───────────┘
     │
     ▼
┌─────────────────┐
│  dnsx_records   │
│  (Qdrant)       │
│  Upsert Mode    │
└─────────────────┘
```

## See Also

- [Converter Documentation](../../CyberToolConverterKit/dnsx/README.md)
- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [dnsx Documentation](https://docs.projectdiscovery.io/opensource/dnsx/usage)
- [sentence-transformers](https://www.sbert.net/)
