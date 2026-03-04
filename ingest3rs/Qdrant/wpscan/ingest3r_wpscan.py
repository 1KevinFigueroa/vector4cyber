#!/usr/bin/env python3
"""
WPScan JSON → Qdrant ingester

Example root object (single scan result):
{
  "id": 1,
  "banner": {...},
  "target_url": "...",
  "target_ip": "...",
  "interesting_findings": [...],
  "main_theme": {...},
  "vuln_api": {...},
  "trace": [...],
  ...
}
"""

import argparse
import json
import os
from typing import List, Dict, Any

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct

DEFAULT_HOST = "localhost"
DEFAULT_PORT = 6333
DEFAULT_VECTOR_SIZE = 384


def make_dummy_vector(size: int = DEFAULT_VECTOR_SIZE) -> List[float]:
    """Simple deterministic dummy vector for each WPScan entry."""
    # You can later replace this with a real embedding (e.g., from target_url + findings)
    return [0.0] * size


def load_wpscan_json(path: str) -> List[Dict[str, Any]]:
    """
    Load WPScan JSON file and normalize to a list of scan records.

    Supports:
    - A single object (one scan)
    - A list of objects (multiple scans)
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"❌ JSON file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        scans = data
    elif isinstance(data, dict):
        scans = [data]
    else:
        raise ValueError("❌ Unsupported JSON root type (expected object or array)")

    print(f"✓ Loaded {len(scans)} WPScan record(s) from '{path}'")
    return scans


def build_summary(scan: Dict[str, Any]) -> str:
    """Build a short textual summary for potential embedding."""
    target = scan.get("target_url") or scan.get("effective_url") or ""
    ip = scan.get("target_ip", "")
    banner = scan.get("banner", {})
    version = banner.get("version", "")
    findings = scan.get("interesting_findings", [])

    findings_types = sorted(set(f.get("type", "") for f in findings if isinstance(f, dict)))
    return f"WPScan on {target} ({ip}) v{version} findings: {', '.join(findings_types)}"


def upload_wpscan_to_qdrant(
    json_path: str,
    collection: str,
    vector_size: int = DEFAULT_VECTOR_SIZE,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
) -> None:
    """Read WPScan JSON and upload to Qdrant."""
    # Connect to Qdrant
    client = QdrantClient(host=host, port=port)
    print(f"✓ Connected to Qdrant at {host}:{port}")

    scans = load_wpscan_json(json_path)
    if not scans:
        print("❌ No WPScan records to upload")
        return

    # Recreate collection
    if client.collection_exists(collection):
        print(f"Collection '{collection}' exists. Recreating...")
        client.delete_collection(collection)

    client.create_collection(
        collection_name=collection,
        vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
    )
    print(f"✓ Created collection '{collection}' (vector_size={vector_size})")

    points: List[PointStruct] = []
    for idx, scan in enumerate(scans, start=1):
        point_id = scan.get("id", idx)

        # Build a summary string for future embeddings (currently unused)
        _summary = build_summary(scan)

        # You can swap make_dummy_vector for an embedding of `_summary`
        vector = make_dummy_vector(vector_size)

        # Flatten key fields into payload but keep full record as well
        payload: Dict[str, Any] = {
            "id": point_id,
            "target_url": scan.get("target_url"),
            "target_ip": scan.get("target_ip"),
            "effective_url": scan.get("effective_url"),
            "start_time": scan.get("start_time"),
            "stop_time": scan.get("stop_time"),
            "elapsed": scan.get("elapsed"),
            "requests_done": scan.get("requests_done"),
            "cached_requests": scan.get("cached_requests"),
            "scan_aborted": scan.get("scan_aborted"),
            "summary": _summary,
            # Optionally keep the full scan object under a nested key
            "raw": scan,
        }

        points.append(
            PointStruct(
                id=point_id,
                vector=vector,
                payload=payload,
            )
        )

    if not points:
        print("❌ No valid points to upload")
        return

    client.upsert(collection_name=collection, points=points, wait=True)
    print(f"✅ Uploaded {len(points)} WPScan record(s) to '{collection}'")

    # Quick verification
    count = client.count(collection_name=collection)
    print(f"📊 Verified: {count.count} points in collection '{collection}'")


def main():
    parser = argparse.ArgumentParser(
        description="Ingest WPScan JSON results into Qdrant"
    )
    parser.add_argument(
        "--collection",
        required=True,
        help="Qdrant collection name",
    )
    parser.add_argument(
        "--vector-size",
        type=int,
        default=DEFAULT_VECTOR_SIZE,
        help=f"Vector dimension size (default: {DEFAULT_VECTOR_SIZE})",
    )
    parser.add_argument(
        "json_path",
        help="Path to WPScan JSON output file",
    )

    args = parser.parse_args()

    upload_wpscan_to_qdrant(
        json_path=args.json_path,
        collection=args.collection,
        vector_size=args.vector_size,
    )


if __name__ == "__main__":
    main()