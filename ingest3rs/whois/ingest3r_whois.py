#/usr/bin/env python3
import json
import argparse
import random
from typing import List, Dict, Any

from qdrant_client import QdrantClient, models


def load_whois_json(path: str) -> List[Dict[str, Any]]:
    """Load list of WHOIS records from JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("Top-level JSON must be a list of objects")
    return data


def make_dummy_vector(dim: int = 16) -> List[float]:
    """Create a dummy vector for now (replace with real embeddings later)."""
    return [random.random() for _ in range(dim)]


def ensure_collection(client: QdrantClient, collection_name: str, dim: int):
    """Create/recreate collection with a single dense vector."""
    client.recreate_collection(
        collection_name=collection_name,
        vectors_config=models.VectorParams(
            size=dim,
            distance=models.Distance.COSINE,
        ),
    )


def upload_whois_records(
    client: QdrantClient,
    collection_name: str,
    records: List[Dict[str, Any]],
    dim: int,
):
    points: List[models.PointStruct] = []

    for rec in records:
        point_id = rec.get("id")  # use existing id
        if point_id is None:
            continue

        # Payload: keep everything except maybe very large raw blobs if you want
        payload = {
            "domain": rec.get("domain"),
            "timestamp": rec.get("timestamp"),
            "whois_data": rec.get("whois_data"),
            "raw_whois": rec.get("raw_whois"),
        }

        points.append(
            models.PointStruct(
                id=point_id,
                vector=make_dummy_vector(dim),
                payload=payload,
            )
        )

    if not points:
        print("No points to upload.")
        return

    client.upsert(
        collection_name=collection_name,
        points=points,
        wait=True,
    )
    print(f"Uploaded {len(points)} WHOIS records to collection '{collection_name}'")


def main():
    parser = argparse.ArgumentParser(
        description="Upload WHOIS JSON records into a local Qdrant collection"
    )
    parser.add_argument("json_path", help="Path to JSON file with WHOIS records")
    parser.add_argument(
        "--collection",
        required=True,
        help="Qdrant collection name to create/populate",
    )
    parser.add_argument(
        "--url",
        default="http://localhost:6333",
        help="Qdrant URL (default: http://localhost:6333)",
    )
    parser.add_argument(
        "--dim",
        type=int,
        default=16,
        help="Vector dimension to use (default: 16)",
    )
    args = parser.parse_args()

    records = load_whois_json(args.json_path)
    print(f"Loaded {len(records)} records from {args.json_path}")

    client = QdrantClient(url=args.url)

    ensure_collection(client, args.collection, args.dim)
    upload_whois_records(client, args.collection, records, args.dim)


if __name__ == "__main__":
    main()