#!/usr/bin/env python3
"""
Nuclei Ingestor for Vector4Cyber

Uploads Nuclei vulnerability scan results to Qdrant vector database with automatic
correlation to existing host and subdomain collections.

Usage:
    python ingest3r_nuclei.py <input_json> [collection_name]

Arguments:
    input_json        Path to nuclei JSON output file (from -o or -json-export flag)
    collection_name   Optional collection name (default: nuclei_results)

Features:
- Automatic correlation with dnsx/nmap/whois collections
- Semantic embeddings using sentence-transformers
- Vulnerability severity indexing
- CVE/CWE reference tracking
- Request/response storage for evidence
"""

import json
import argparse
import sys
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models

# Try to import sentence-transformers, fallback to simple embeddings if not available
try:
    from sentence_transformers import SentenceTransformer

    USE_SENTENCE_TRANSFORMERS = True
except ImportError:
    USE_SENTENCE_TRANSFORMERS = False
    print(
        "[WARNING] sentence-transformers not installed. Using simple hash-based embeddings."
    )
    print("[INFO] Install with: pip install sentence-transformers")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Ingest nuclei vulnerability scan results into Qdrant"
    )
    parser.add_argument("input_file", help="Path to nuclei JSON output file")
    parser.add_argument(
        "collection_name",
        nargs="?",
        default="nuclei_results",
        help="Qdrant collection name (default: nuclei_results)",
    )
    parser.add_argument(
        "--host", default="localhost", help="Qdrant host (default: localhost)"
    )
    parser.add_argument(
        "--port", type=int, default=6333, help="Qdrant port (default: 6333)"
    )
    parser.add_argument(
        "--vector-size",
        type=int,
        default=384,
        help="Vector size for embeddings (default: 384)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Batch size for uploads (default: 100)",
    )
    parser.add_argument(
        "--skip-correlation",
        action="store_true",
        help="Skip automatic correlation with host/subdomain collections",
    )
    parser.add_argument(
        "--omit-raw",
        action="store_true",
        help="Omit request/response data from payload (saves space)",
    )
    return parser.parse_args()


class NucleiIngestor:
    """Main ingestor class for nuclei vulnerability scan data."""

    # Common collections to search for host correlation
    CORRELATION_COLLECTIONS = [
        "dnsx_records",
        "nmap_results",
        "whois_records",
        "subdomains_collection",
    ]

    # Severity weights for risk scoring
    SEVERITY_WEIGHTS = {
        "critical": 10,
        "high": 7,
        "medium": 5,
        "low": 3,
        "info": 1,
        "unknown": 0,
    }

    def __init__(self, client: QdrantClient, collection_name: str, vector_size: int):
        self.client = client
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.model = None
        self.stats = {
            "total": 0,
            "inserted": 0,
            "updated": 0,
            "correlated": 0,
            "errors": 0,
            "by_severity": {},
        }

        # Initialize embedding model
        if USE_SENTENCE_TRANSFORMERS:
            print("[INFO] Loading sentence-transformers model: all-MiniLM-L6-v2")
            self.model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

        # Ensure collection exists
        self._ensure_collection()

    def _ensure_collection(self):
        """Create collection if it doesn't exist."""
        collections = [c.name for c in self.client.get_collections().collections]

        if self.collection_name not in collections:
            print(f"[INFO] Creating collection: {self.collection_name}")
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=self.vector_size, distance=models.Distance.COSINE
                ),
            )
            self._create_payload_indexes()
        else:
            print(f"[INFO] Using existing collection: {self.collection_name}")

    def _create_payload_indexes(self):
        """Create indexes on frequently queried fields."""
        indexed_fields = [
            "template_id",
            "host",
            "url",
            "severity",
            "type",
            "matched_at",
            "timestamp",
            "cve_id",
            "cwe_id",
            "correlation_status",
            "ip",
        ]

        for field in indexed_fields:
            try:
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name=field,
                    field_schema=models.PayloadSchemaType.KEYWORD,
                )
                print(f"[INFO] Created index on field: {field}")
            except Exception as e:
                print(f"[WARNING] Could not create index on {field}: {e}")

    def generate_embedding(self, nuclei_result: Dict[str, Any]) -> List[float]:
        """
        Generate vector embedding for nuclei vulnerability result.

        Creates a semantic representation combining:
        - Template ID and name
        - Vulnerability description
        - Severity and type
        - Matched content
        - CVE/CWE references
        """
        # Build text representation for embedding
        text_parts = []

        # Template info
        info = nuclei_result.get("info", {})
        if info.get("name"):
            text_parts.append(f"Vulnerability: {info['name']}")
        if nuclei_result.get("template_id"):
            text_parts.append(f"Template: {nuclei_result['template_id']}")

        # Description
        if info.get("description"):
            text_parts.append(f"Description: {info['description']}")

        # Severity and type
        severity = info.get("severity", "unknown")
        vuln_type = nuclei_result.get("type", "unknown")
        text_parts.append(f"Severity: {severity}")
        text_parts.append(f"Type: {vuln_type}")

        # Target
        if nuclei_result.get("host"):
            text_parts.append(f"Host: {nuclei_result['host']}")
        if nuclei_result.get("url"):
            text_parts.append(f"URL: {nuclei_result['url']}")

        # Matched content (truncated for embedding)
        matched = nuclei_result.get("matched_at", "")
        if matched:
            text_parts.append(f"Matched: {matched[:200]}")

        # Extracted results
        extracted = nuclei_result.get("extracted_results", [])
        if extracted:
            text_parts.append(f"Extracted: {', '.join(str(e) for e in extracted[:5])}")

        # CVE/CWE references
        tags = info.get("tags", [])
        if tags:
            cve_tags = [t for t in tags if t.lower().startswith("cve")]
            cwe_tags = [t for t in tags if t.lower().startswith("cwe")]
            if cve_tags:
                text_parts.append(f"CVE: {', '.join(cve_tags[:3])}")
            if cwe_tags:
                text_parts.append(f"CWE: {', '.join(cwe_tags[:3])}")

        text = " ".join(text_parts)

        if self.model:
            # Use sentence-transformers
            embedding = self.model.encode(text)
            return embedding.tolist()
        else:
            # Fallback: Simple hash-based embedding
            return self._hash_based_embedding(text)

    def _hash_based_embedding(self, text: str) -> List[float]:
        """Generate deterministic hash-based embedding."""
        hash_bytes = hashlib.sha256(text.encode()).digest()
        vector = []
        for i in range(self.vector_size):
            byte_val = hash_bytes[i % len(hash_bytes)]
            vector.append((byte_val / 127.5) - 1)
        return vector

    def _parse_jsonl(self, file_path: str) -> List[Dict[str, Any]]:
        """Parse nuclei JSON output file."""
        results = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    result = json.loads(line)
                    result["_source_line"] = line_num
                    results.append(result)
                except json.JSONDecodeError as e:
                    print(f"[WARNING] Failed to parse line {line_num}: {e}")
                    self.stats["errors"] += 1
        return results

    def _normalize_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize and enrich nuclei result for storage."""
        normalized = {}

        # Core identifiers
        normalized["template_id"] = result.get("template-id", "")
        normalized["template_path"] = result.get("template-path", "")
        normalized["template_url"] = result.get("template-url", "")

        # Info block
        info = result.get("info", {})
        normalized["name"] = info.get("name", "")
        normalized["description"] = info.get("description", "")
        normalized["severity"] = info.get("severity", "unknown").lower()
        normalized["author"] = info.get("author", "")
        normalized["reference"] = info.get("reference", [])
        normalized["tags"] = info.get("tags", [])

        # Classification
        normalized["type"] = result.get("type", "")
        normalized["matcher_name"] = result.get("matcher-name", "")
        normalized["extractor_name"] = result.get("extractor-name", "")

        # Target information
        normalized["host"] = result.get("host", "")
        normalized["port"] = result.get("port", "")
        normalized["scheme"] = result.get("scheme", "")
        normalized["url"] = result.get("url", "")
        normalized["path"] = result.get("path", "")
        normalized["ip"] = result.get("ip", "")

        # Match details
        normalized["matched_at"] = result.get("matched-at", "")
        normalized["extracted_results"] = result.get("extracted-results", [])
        normalized["matched_line"] = result.get("matched-line", [])

        # Timestamp
        timestamp = result.get("timestamp")
        if timestamp:
            normalized["timestamp"] = timestamp
        else:
            normalized["timestamp"] = datetime.utcnow().isoformat()

        # Calculate risk score
        normalized["risk_score"] = self.SEVERITY_WEIGHTS.get(normalized["severity"], 0)

        # Extract CVE/CWE from tags
        tags = info.get("tags", [])
        normalized["cve_id"] = self._extract_cve(tags)
        normalized["cwe_id"] = self._extract_cwe(tags)

        # Store metadata
        normalized["metadata"] = result.get("meta", {})

        # Correlation fields (populated later)
        normalized["correlation_status"] = "pending"
        normalized["linked_record_id"] = None
        normalized["linked_collection"] = None

        return normalized

    def _extract_cve(self, tags: List[str]) -> Optional[str]:
        """Extract CVE ID from tags."""
        for tag in tags:
            if tag.lower().startswith("cve-"):
                return tag.upper()
        return None

    def _extract_cwe(self, tags: List[str]) -> Optional[str]:
        """Extract CWE ID from tags."""
        for tag in tags:
            if tag.lower().startswith("cwe-"):
                return tag.upper()
        return None

    def _find_correlated_record(self, host: str) -> Optional[Dict[str, Any]]:
        """Search for correlated records in host collections."""
        for collection in self.CORRELATION_COLLECTIONS:
            try:
                collections = [
                    c.name for c in self.client.get_collections().collections
                ]
                if collection not in collections:
                    continue

                # Try to find by host
                results = self.client.scroll(
                    collection_name=collection,
                    scroll_filter=models.Filter(
                        should=[
                            models.FieldCondition(
                                key="host", match=models.MatchValue(value=host)
                            ),
                            models.FieldCondition(
                                key="hostname", match=models.MatchValue(value=host)
                            ),
                        ]
                    ),
                    limit=1,
                    with_payload=True,
                    with_vectors=False,
                )

                if results[0]:
                    point = results[0][0]
                    return {
                        "id": point.id,
                        "payload": point.payload,
                        "collection": collection,
                    }
            except Exception as e:
                print(f"[WARNING] Error searching collection {collection}: {e}")
                continue

        return None

    def _find_existing_vulnerability(
        self, template_id: str, host: str
    ) -> Optional[int]:
        """Check if vulnerability already exists for this host."""
        try:
            results = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="template_id",
                            match=models.MatchValue(value=template_id),
                        ),
                        models.FieldCondition(
                            key="host", match=models.MatchValue(value=host)
                        ),
                    ]
                ),
                limit=1,
                with_payload=True,
                with_vectors=False,
            )

            if results[0]:
                return results[0][0].id
        except Exception:
            pass

        return None

    def ingest_results(
        self,
        results: List[Dict[str, Any]],
        skip_correlation: bool = False,
        omit_raw: bool = False,
        batch_size: int = 100,
    ) -> Dict[str, Any]:
        """
        Ingest nuclei results into Qdrant.

        Args:
            results: List of nuclei JSONL results
            skip_correlation: Skip auto-correlation with host collections
            omit_raw: Omit request/response data
            batch_size: Number of records to process per batch

        Returns:
            Statistics dictionary
        """
        self.stats["total"] = len(results)
        points_to_upsert = []
        next_id = 1

        # Get current max ID
        try:
            existing_count = self.client.count(
                collection_name=self.collection_name
            ).count
            next_id = existing_count + 1
        except Exception:
            next_id = 1

        for i, result in enumerate(results):
            try:
                # Normalize the result
                normalized = self._normalize_result(result)

                # Add raw request/response if not omitted
                if not omit_raw:
                    normalized["request"] = result.get("request", "")
                    normalized["response"] = result.get("response", "")
                    normalized["curl_command"] = result.get("curl-command", "")

                # Correlate with existing records
                if not skip_correlation and normalized.get("host"):
                    correlated = self._find_correlated_record(normalized["host"])
                    if correlated:
                        normalized["correlation_status"] = "matched"
                        normalized["linked_record_id"] = correlated["id"]
                        normalized["linked_collection"] = correlated["collection"]
                        self.stats["correlated"] += 1

                # Check for existing vulnerability (for upsert)
                existing_id = self._find_existing_vulnerability(
                    normalized["template_id"], normalized["host"]
                )

                if existing_id:
                    point_id = existing_id
                    self.stats["updated"] += 1
                else:
                    point_id = next_id
                    next_id += 1
                    self.stats["inserted"] += 1

                # Track severity stats
                severity = normalized["severity"]
                self.stats["by_severity"][severity] = (
                    self.stats["by_severity"].get(severity, 0) + 1
                )

                # Generate embedding
                vector = self.generate_embedding(normalized)

                # Create point
                point = models.PointStruct(
                    id=point_id, vector=vector, payload=normalized
                )
                points_to_upsert.append(point)

                # Batch upload
                if len(points_to_upsert) >= batch_size:
                    self._upload_batch(points_to_upsert)
                    print(f"[PROGRESS] Processed {i + 1}/{len(results)} results")
                    points_to_upsert = []

            except Exception as e:
                print(f"[ERROR] Failed to process result {i}: {e}")
                self.stats["errors"] += 1
                continue

        # Upload remaining points
        if points_to_upsert:
            self._upload_batch(points_to_upsert)

        return self.stats

    def _upload_batch(self, points: List[models.PointStruct]):
        """Upload a batch of points to Qdrant."""
        try:
            self.client.upsert(collection_name=self.collection_name, points=points)
        except Exception as e:
            print(f"[ERROR] Batch upload failed: {e}")
            raise


def main():
    args = parse_args()

    print(f"[INFO] Starting nuclei ingestor")
    print(f"[INFO] Input file: {args.input_file}")
    print(f"[INFO] Collection: {args.collection_name}")
    print(f"[INFO] Qdrant: {args.host}:{args.port}")

    # Connect to Qdrant
    try:
        client = QdrantClient(host=args.host, port=args.port)
        print(f"[INFO] Connected to Qdrant")
    except Exception as e:
        print(f"[ERROR] Failed to connect to Qdrant: {e}")
        return 1

    # Initialize ingestor
    ingestor = NucleiIngestor(
        client=client,
        collection_name=args.collection_name,
        vector_size=args.vector_size,
    )

    # Parse JSONL file
    try:
        results = ingestor._parse_jsonl(args.input_file)
        print(f"[INFO] Loaded {len(results)} nuclei results")
    except Exception as e:
        print(f"[ERROR] Failed to load input file: {e}")
        return 1

    if not results:
        print("[WARNING] No results found in input file")
        return 0

    # Ingest results
    try:
        stats = ingestor.ingest_results(
            results=results,
            skip_correlation=args.skip_correlation,
            omit_raw=args.omit_raw,
            batch_size=args.batch_size,
        )

        print("\n" + "=" * 50)
        print("INGESTION COMPLETE")
        print("=" * 50)
        print(f"Total results:    {stats['total']}")
        print(f"Inserted:         {stats['inserted']}")
        print(f"Updated:          {stats['updated']}")
        print(f"Correlated:       {stats['correlated']}")
        print(f"Errors:           {stats['errors']}")

        if stats["by_severity"]:
            print("\nBY SEVERITY:")
            for severity, count in sorted(
                stats["by_severity"].items(),
                key=lambda x: ingestor.SEVERITY_WEIGHTS.get(x[0], 0),
                reverse=True,
            ):
                print(f"  {severity.upper():<10} {count}")

        print("=" * 50)

    except Exception as e:
        print(f"[ERROR] Ingestion failed: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
