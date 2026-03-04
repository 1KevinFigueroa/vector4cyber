#!/usr/bin/env python3
"""
Dirsearch JSON → Qdrant ingester

Example dirsearch JSON item:
{
    "id": 1,
    "status": 200,
    "size": " ",
    "url": " ",
    "redirect_to": " "
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
    """Simple dummy vector for each dirsearch entry (replace with real embeddings later)."""
    # Deterministic vector based on size only, for now
    return [0.0] * size


def load_dirsearch_json(path: str) -> List[Dict[str, Any]]:
    """Load dirsearch JSON file and return a list of result entries."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"❌ JSON file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Support both: list of entries OR wrapped structure
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        # If you later wrap results under some key, handle it here
        if "results" in data and isinstance(data["results"], list):
            items = data["results"]
        else:
            items = [data]
    else:
        raise ValueError("❌ Unsupported JSON root type (expected list or object)")

    print(f"✓ Loaded {len(items)} dirsearch entries from '{path}'")
    return items


def upload_dirsearch_to_qdrant(
    json_path: str,
    collection: str,
    vector_size: int = DEFAULT_VECTOR_SIZE,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
) -> None:
    """Read dirsearch JSON and upload to Qdrant."""
    # Connect to Qdrant
    client = QdrantClient(host=host, port=port)
    print(f"✓ Connected to Qdrant at {host}:{port}")

    # Load JSON data
    entries = load_dirsearch_json(json_path)
    if not entries:
        print("❌ No entries to upload")
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

    # Prepare points
    points: List[PointStruct] = []
    for idx, item in enumerate(entries, start=1):
        point_id = item.get("id", idx)

        payload = {
            "id": point_id,
            "status": item.get("status"),
            "size": item.get("size"),
            "url": item.get("url"),
            "redirect_to": item.get("redirect_to"),
            # Preserve any extra keys
            **{k: v for k, v in item.items() if k not in ("id", "vector")}
        }

        points.append(
            PointStruct(
                id=point_id,
                vector=make_dummy_vector(vector_size),
                payload=payload,
            )
        )

    if not points:
        print("❌ No valid points to upload")
        return

    # Upload
    client.upsert(
        collection_name=collection,
        points=points,
        wait=True,
    )
    print(f"✅ Uploaded {len(points)} dirsearch entries to '{collection}'")

    # Quick verification
    count = client.count(collection_name=collection)
    print(f"📊 Verified: {count.count} points in collection '{collection}'")


def main():
    parser = argparse.ArgumentParser(
        description="Ingest dirsearch JSON results into Qdrant"
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
        help="Path to dirsearch JSON output file",
    )

    args = parser.parse_args()

    upload_dirsearch_to_qdrant(
        json_path=args.json_path,
        collection=args.collection,
        vector_size=args.vector_size,
    )


if __name__ == "__main__":
    main()
