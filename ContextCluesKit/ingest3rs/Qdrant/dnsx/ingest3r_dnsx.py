#!/usr/bin/env python3
"""Upload converted dnsx records to Qdrant with optional subdomain correlation."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from qdrant_client import QdrantClient, models
except ImportError:  # keep import/py_compile usable without runtime dependency installed
    QdrantClient = None  # type: ignore[assignment]
    models = None  # type: ignore[assignment]

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None  # type: ignore[assignment]

try:
    from correlation_engine import DNSCorrelationEngine, normalize_hostname
except ImportError:  # pragma: no cover
    try:
        from .correlation_engine import DNSCorrelationEngine, normalize_hostname
    except ImportError:
        DNSCorrelationEngine = None  # type: ignore[assignment]

        def normalize_hostname(hostname: Any) -> str:
            return str(hostname or "").strip().lower().rstrip(".")

DEFAULT_HOST = "localhost"
DEFAULT_PORT = 6333
DEFAULT_COLLECTION_NAME = "dnsx_records"
DEFAULT_VECTOR_SIZE = 384
DNS_TEXT_FIELDS = ("host", "status_code", "a", "aaaa", "cname", "mx", "ns", "txt", "soa", "srv", "ptr", "caa")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="ingest3r_dnsx.py",
        description="Ingest converted dnsx JSON records into Qdrant",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("input_file", help="Converted dnsx JSON file")
    parser.add_argument("collection", nargs="?", default=DEFAULT_COLLECTION_NAME, help="Qdrant collection name")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Qdrant host")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Qdrant port")
    parser.add_argument("--vector-size", type=int, default=DEFAULT_VECTOR_SIZE, help="Vector dimension")
    parser.add_argument("--batch-size", type=int, default=100, help="Qdrant upsert batch size")
    parser.add_argument("--skip-correlation", action="store_true", help="Do not correlate with subdomain collections")
    parser.add_argument(
        "--correlation-collections",
        nargs="+",
        help="Specific Qdrant collections to search for matching subdomains",
    )
    parser.add_argument("--embed", action="store_true", help="Use sentence-transformers if installed")
    return parser.parse_args()


def require_qdrant() -> None:
    if QdrantClient is None or models is None:
        raise RuntimeError("qdrant-client is required. Install with: pip install qdrant-client")


def load_dnsx_json(path: str) -> List[Dict[str, Any]]:
    input_path = Path(path)
    if not input_path.is_file():
        raise FileNotFoundError(f"JSON file not found: {input_path}")
    with input_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if isinstance(data, list):
        records = data
    elif isinstance(data, dict) and isinstance(data.get("records"), list):
        records = data["records"]
    elif isinstance(data, dict):
        records = [data]
    else:
        raise ValueError("Unsupported JSON root type; expected object or array")
    return [record if isinstance(record, dict) else {"value": record} for record in records]


def build_dnsx_text(record: Dict[str, Any]) -> str:
    parts: List[str] = []
    for field in DNS_TEXT_FIELDS:
        value = record.get(field)
        if value in (None, "", []):
            continue
        if isinstance(value, list):
            rendered = ",".join(str(item) for item in value[:10])
        else:
            rendered = str(value)
        parts.append(f"{field}:{rendered}")
    return " ".join(parts)[:2048] or "empty_dnsx_record"


def deterministic_vector(text: str, vector_size: int = DEFAULT_VECTOR_SIZE) -> List[float]:
    seed = text.encode("utf-8", errors="replace") or b"empty_dnsx_record"
    values: List[float] = []
    counter = 0
    while len(values) < vector_size:
        digest = hashlib.sha256(seed + counter.to_bytes(4, "big")).digest()
        values.extend((byte / 127.5) - 1.0 for byte in digest)
        counter += 1
    return values[:vector_size]


class DNSxIngestor:
    def __init__(self, client: Any, collection_name: str, vector_size: int = DEFAULT_VECTOR_SIZE, use_embeddings: bool = False):
        require_qdrant()
        self.client = client
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.model = None
        if use_embeddings and SentenceTransformer is not None:
            print("🧠 Loading sentence-transformers/all-MiniLM-L6-v2...")
            self.model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2", device="cpu")
        elif use_embeddings:
            print("⚠️ sentence-transformers not installed; using deterministic fallback vectors")
        self.ensure_collection()

    def ensure_collection(self) -> None:
        existing = {collection.name for collection in self.client.get_collections().collections}
        if self.collection_name in existing:
            print(f"✓ Using existing collection '{self.collection_name}'")
            return
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=models.VectorParams(size=self.vector_size, distance=models.Distance.COSINE),
        )
        print(f"✓ Created collection '{self.collection_name}' (vector_size={self.vector_size})")
        self.create_payload_indexes()

    def create_payload_indexes(self) -> None:
        for field in ("host", "normalized_host", "status_code", "source_tool", "correlation_status", "linked_collection"):
            try:
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name=field,
                    field_schema=models.PayloadSchemaType.KEYWORD,
                )
            except Exception as exc:
                print(f"⚠️ Could not create payload index for {field}: {exc}")

    def generate_embedding(self, record: Dict[str, Any]) -> List[float]:
        text = build_dnsx_text(record)
        if self.model is not None:
            embedding = self.model.encode([text], normalize_embeddings=True, show_progress_bar=False)[0]
            vector = embedding.tolist() if hasattr(embedding, "tolist") else list(embedding)
            if len(vector) == self.vector_size:
                return vector
            if len(vector) > self.vector_size:
                return vector[: self.vector_size]
            return vector + [0.0] * (self.vector_size - len(vector))
        return deterministic_vector(text, self.vector_size)

    def deterministic_point_id(self, record: Dict[str, Any]) -> int:
        """Return a stable Qdrant integer point ID for a DNS record identity.

        Converter-assigned IDs and input order are intentionally ignored so reruns,
        deletes, and mixed correlation modes cannot overwrite unrelated records.
        """
        normalized_host = normalize_hostname(record.get("normalized_host") or record.get("host"))
        identity = {
            "host": normalized_host,
            "source_tool": str(record.get("source_tool") or "dnsx"),
        }
        digest = hashlib.sha256(json.dumps(identity, sort_keys=True).encode("utf-8")).digest()
        return int.from_bytes(digest[:8], "big") & ((1 << 63) - 1)

    def flush_batch(self, points: List[Any], linked_updates: List[Dict[str, Any]], correlation_engine: Optional[Any]) -> None:
        self.upload_batch(points)
        if correlation_engine is None:
            return
        for record in linked_updates:
            correlation_engine.update_subdomain_with_dns_info(record)

    def ingest_records(
        self,
        dns_records: List[Dict[str, Any]],
        correlation_engine: Optional[Any] = None,
        batch_size: int = 100,
    ) -> Dict[str, int]:
        stats = {"total": len(dns_records), "inserted": 0, "updated": 0, "correlated": 0, "errors": 0}
        batch: List[Any] = []
        linked_updates: List[Dict[str, Any]] = []

        for index, original in enumerate(dns_records, start=1):
            try:
                record = dict(original)
                normalized_host = normalize_hostname(record.get("host"))
                if normalized_host:
                    record["normalized_host"] = normalized_host

                if correlation_engine is not None:
                    record = correlation_engine.correlate_dns_record(record)
                    if record.get("correlation_status") == "matched":
                        stats["correlated"] += 1
                    upsert_info = correlation_engine.prepare_upsert_operation(record, self.collection_name)
                    if upsert_info["operation"] == "update":
                        point_id = upsert_info["point_id"]
                        stats["updated"] += 1
                    else:
                        point_id = self.deterministic_point_id(record)
                        stats["inserted"] += 1
                else:
                    point_id = self.deterministic_point_id(record)
                    stats["inserted"] += 1

                record["id"] = point_id
                vector = self.generate_embedding(record)
                batch.append(models.PointStruct(id=point_id, vector=vector, payload=record))

                if correlation_engine is not None and record.get("correlation_status") == "matched":
                    linked_updates.append(record)
            except Exception as exc:
                print(f"⚠️ Failed to process dnsx record {index}: {exc}")
                stats["errors"] += 1
                continue

            if len(batch) >= batch_size:
                self.flush_batch(batch, linked_updates, correlation_engine)
                batch = []
                linked_updates = []

        if batch:
            self.flush_batch(batch, linked_updates, correlation_engine)
        return stats

    def upload_batch(self, points: List[Any]) -> None:
        self.client.upsert(collection_name=self.collection_name, points=points, wait=True)
        print(f"✓ Uploaded {len(points)} dnsx points")


def main() -> int:
    args = parse_args()
    try:
        require_qdrant()
        records = load_dnsx_json(args.input_file)
        client = QdrantClient(host=args.host, port=args.port)
        ingestor = DNSxIngestor(client, args.collection, args.vector_size, use_embeddings=args.embed)

        correlation_engine = None
        if not args.skip_correlation:
            if DNSCorrelationEngine is None:
                raise RuntimeError("correlation_engine.py must be available beside ingest3r_dnsx.py")
            correlation_engine = DNSCorrelationEngine(client, collections=args.correlation_collections)

        stats = ingestor.ingest_records(records, correlation_engine=correlation_engine, batch_size=args.batch_size)
    except Exception as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 1

    print("\n=== DNSX INGESTION COMPLETE ===")
    for key in ("total", "inserted", "updated", "correlated", "errors"):
        print(f"{key.title():<12} {stats[key]}")
    if correlation_engine is not None:
        print(f"Correlation {correlation_engine.get_stats()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
