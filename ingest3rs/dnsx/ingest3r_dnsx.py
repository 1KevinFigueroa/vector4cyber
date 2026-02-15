#!/usr/bin/env python3
"""
dnsx Ingestor for Vector4Cyber

Uploads converted dnsx DNS records to Qdrant vector database with automatic
correlation to existing subdomain collections and latest-only tracking.

Usage:
    python ingest3r_dnsx.py <input_json> [collection_name]

Arguments:
    input_json      Path to converted dnsx JSON file
    collection_name Optional collection name (default: dnsx_records)

Features:
- Automatic correlation with subfinder/sublist3r/amass collections
- Latest-only tracking (upsert mode)
- Semantic embeddings using sentence-transformers
- Bidirectional linking between DNS and subdomain records
"""

import json
import argparse
import sys
from typing import List, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.http import models

# Import correlation engine
try:
    from correlation_engine import DNSCorrelationEngine
except ImportError:
    print("[ERROR] correlation_engine.py not found in the same directory")
    sys.exit(1)

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
        description="Ingest dnsx DNS records into Qdrant with auto-correlation"
    )
    parser.add_argument("input_file", help="Path to converted dnsx JSON file")
    parser.add_argument(
        "collection_name",
        nargs="?",
        default="dnsx_records",
        help="Qdrant collection name (default: dnsx_records)",
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
        help="Skip automatic correlation with subdomain collections",
    )
    parser.add_argument(
        "--correlation-collections",
        nargs="+",
        default=None,
        help="Specific collections to search for correlation (space-separated)",
    )
    return parser.parse_args()


class DNSxIngestor:
    """Main ingestor class for dnsx data."""

    def __init__(self, client: QdrantClient, collection_name: str, vector_size: int):
        self.client = client
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.model = None

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

            # Create payload indexes for efficient querying
            self._create_payload_indexes()
        else:
            print(f"[INFO] Using existing collection: {self.collection_name}")

    def _create_payload_indexes(self):
        """Create indexes on frequently queried fields."""
        indexed_fields = [
            "host",
            "a",
            "mx",
            "cname",
            "linked_subdomain_id",
            "timestamp",
            "correlation_status",
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

    def generate_embedding(self, dns_record: Dict[str, Any]) -> List[float]:
        """
        Generate vector embedding for DNS record.

        Uses sentence-transformers if available, otherwise simple hash-based.
        """
        # Build text representation
        text_parts = [dns_record.get("host", "")]

        # Add DNS record types
        if dns_record.get("a"):
            text_parts.append(f"A:{','.join(dns_record['a'])}")
        if dns_record.get("aaaa"):
            text_parts.append(f"AAAA:{','.join(dns_record['aaaa'])}")
        if dns_record.get("cname"):
            text_parts.append(f"CNAME:{','.join(dns_record['cname'])}")
        if dns_record.get("mx"):
            text_parts.append(f"MX:{','.join(dns_record['mx'])}")
        if dns_record.get("ns"):
            text_parts.append(f"NS:{','.join(dns_record['ns'])}")
        if dns_record.get("txt"):
            text_parts.append(
                f"TXT:{','.join(dns_record['txt'][:2])}"
            )  # Limit TXT records

        text = " ".join(text_parts)

        if self.model:
            # Use sentence-transformers
            embedding = self.model.encode(text)
            return embedding.tolist()
        else:
            # Fallback: Simple hash-based embedding
            import hashlib
            import numpy as np

            # Create deterministic embedding from hash
            hash_bytes = hashlib.sha256(text.encode()).digest()
            # Expand to vector size using repeated hashing
            vector = []
            for i in range(self.vector_size):
                byte_val = hash_bytes[i % len(hash_bytes)]
                # Normalize to -1 to 1 range
                vector.append((byte_val / 127.5) - 1)

            return vector

    def ingest_records(
        self,
        dns_records: List[Dict[str, Any]],
        correlation_engine: DNSCorrelationEngine = None,
        batch_size: int = 100,
    ) -> Dict[str, Any]:
        """
        Ingest DNS records into Qdrant with optional correlation.

        Args:
            dns_records: List of DNS records from converter
            correlation_engine: Optional correlation engine for auto-linking
            batch_size: Number of records to process per batch

        Returns:
            Statistics dictionary
        """
        stats = {
            "total": len(dns_records),
            "inserted": 0,
            "updated": 0,
            "correlated": 0,
            "errors": 0,
        }

        points_to_upsert = []
        next_id = 1

        # Get current max ID from collection for new inserts
        if correlation_engine:
            try:
                existing_count = self.client.count(
                    collection_name=self.collection_name
                ).count
                next_id = existing_count + 1
            except:
                next_id = 1

        for i, record in enumerate(dns_records):
            try:
                # Step 1: Correlate with subdomains (if enabled)
                if correlation_engine:
                    record = correlation_engine.correlate_dns_record(record)
                    if record.get("correlation_status") == "matched":
                        stats["correlated"] += 1
                        # Update subdomain with DNS info
                        correlation_engine.update_subdomain_with_dns_info(record)

                # Step 2: Prepare for upsert
                if correlation_engine:
                    upsert_info = correlation_engine.prepare_upsert_operation(
                        record, self.collection_name
                    )

                    if upsert_info["operation"] == "update":
                        point_id = upsert_info["point_id"]
                        stats["updated"] += 1
                    else:
                        point_id = next_id
                        next_id += 1
                        stats["inserted"] += 1
                else:
                    # No correlation - just use sequential IDs
                    point_id = record.get("id", i + 1)
                    stats["inserted"] += 1

                # Step 3: Generate embedding
                vector = self.generate_embedding(record)

                # Step 4: Create point
                point = models.PointStruct(id=point_id, vector=vector, payload=record)
                points_to_upsert.append(point)

                # Step 5: Batch upload
                if len(points_to_upsert) >= batch_size:
                    self._upload_batch(points_to_upsert)
                    print(f"[PROGRESS] Processed {i + 1}/{len(dns_records)} records")
                    points_to_upsert = []

            except Exception as e:
                print(f"[ERROR] Failed to process record {i}: {e}")
                stats["errors"] += 1
                continue

        # Upload remaining points
        if points_to_upsert:
            self._upload_batch(points_to_upsert)

        return stats

    def _upload_batch(self, points: List[models.PointStruct]):
        """Upload a batch of points to Qdrant."""
        try:
            self.client.upsert(collection_name=self.collection_name, points=points)
        except Exception as e:
            print(f"[ERROR] Batch upload failed: {e}")
            raise


def main():
    args = parse_args()

    print(f"[INFO] Starting dnsx ingestor")
    print(f"[INFO] Input file: {args.input_file}")
    print(f"[INFO] Collection: {args.collection_name}")
    print(f"[INFO] Qdrant: {args.host}:{args.port}")

    # Load DNS records
    try:
        with open(args.input_file, "r", encoding="utf-8") as f:
            dns_records = json.load(f)
        print(f"[INFO] Loaded {len(dns_records)} DNS records")
    except Exception as e:
        print(f"[ERROR] Failed to load input file: {e}")
        return 1

    # Connect to Qdrant
    try:
        client = QdrantClient(host=args.host, port=args.port)
        print(f"[INFO] Connected to Qdrant")
    except Exception as e:
        print(f"[ERROR] Failed to connect to Qdrant: {e}")
        return 1

    # Initialize ingestor
    ingestor = DNSxIngestor(
        client=client,
        collection_name=args.collection_name,
        vector_size=args.vector_size,
    )

    # Initialize correlation engine (if enabled)
    correlation_engine = None
    if not args.skip_correlation:
        correlation_collections = (
            args.correlation_collections or DNSCorrelationEngine.DEFAULT_COLLECTIONS
        )
        correlation_engine = DNSCorrelationEngine(
            client, collections=correlation_collections
        )
        print(
            f"[INFO] Auto-correlation enabled for collections: {', '.join(correlation_collections)}"
        )
    else:
        print("[INFO] Auto-correlation disabled")

    # Ingest records
    try:
        stats = ingestor.ingest_records(
            dns_records=dns_records,
            correlation_engine=correlation_engine,
            batch_size=args.batch_size,
        )

        print("\n" + "=" * 50)
        print("INGESTION COMPLETE")
        print("=" * 50)
        print(f"Total records:    {stats['total']}")
        print(f"Inserted:         {stats['inserted']}")
        print(f"Updated:          {stats['updated']}")
        print(f"Correlated:       {stats['correlated']}")
        print(f"Errors:           {stats['errors']}")

        if correlation_engine:
            corr_stats = correlation_engine.get_stats()
            print("\nCORRELATION STATS:")
            print(f"Matched:          {corr_stats['matched']}")
            print(f"Unmatched:        {corr_stats['unmatched']}")
            print(f"Subdomains updated: {corr_stats['updated']}")

        print("=" * 50)

    except Exception as e:
        print(f"[ERROR] Ingestion failed: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
