#!/usr/bin/env python3
import json
import argparse
import random
from typing import List, Dict, Any

from qdrant_client import QdrantClient, models


def load_subdomains_json(path: str) -> List[Dict[str, Any]]:
    """Load subdomains JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    if isinstance(data, list):
        return data
    elif isinstance(data, dict) and "results" in data:
        return data["results"]
    else:
        raise ValueError("Expected list of domains or {'results': [...]}")


def make_dummy_vector(dim: int = 128) -> List[float]:
    """Dummy vector (replace with sentence-transformer embeddings later)."""
    return [random.random() for _ in range(dim)]


def ensure_collection(client: QdrantClient, collection_name: str, dim: int):
    """Create/recreate collection."""
    try:
        client.recreate_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=dim,
                distance=models.Distance.COSINE,
            ),
        )
        print(f"✅ Collection '{collection_name}' created")
    except Exception as e:
        print(f"❌ Collection error: {e}")
        return False
    return True


def upload_subdomains(
    client: QdrantClient,
    collection_name: str,
    domains: List[Dict[str, Any]],
    dim: int,
):
    """Upload subdomains as Qdrant points."""
    points = []
    
    for domain_entry in domains:
        # Use 'id' field or generate from line_number
        point_id = domain_entry.get("id") or domain_entry.get("line_number")
        if not point_id:
            continue
        
        payload = {
            "domain": domain_entry.get("domain"),
            "raw_line": domain_entry.get("raw_line", ""),
            "line_number": domain_entry.get("line_number"),
        }
        
        points.append(
            models.PointStruct(
                id=point_id,
                vector=make_dummy_vector(dim),
                payload=payload,
            )
        )
    
    if not points:
        print("❌ No valid domains to upload")
        return
    
    client.upsert(
        collection_name=collection_name,
        points=points,
        wait=True,
    )
    print(f"✅ Uploaded {len(points)} subdomains to '{collection_name}'")


def verify_upload(client: QdrantClient, collection_name: str):
    """Verify collection contents."""
    try:
        count = client.count(collection_name=collection_name)
        print(f"📊 Verified: {count.count} points in '{collection_name}'")
        
        # Show first 3 points
        points = client.scroll(
            collection_name=collection_name,
            limit=3,
            with_payload=True,
            with_vectors=False,
        )[0]
        print("🔍 Sample points:")
        for p in points:
            print(f"   ID {p.id}: {p.payload.get('domain')}")
    except Exception as e:
        print(f"❌ Verification failed: {e}")


def main():
    parser = argparse.ArgumentParser(description="Upload subdomains JSON to Qdrant")
    parser.add_argument("json_file", help="Path to subdomains JSON file")
    parser.add_argument("collection", help="Qdrant collection name")
    parser.add_argument("--url", default="http://localhost:6333", help="Qdrant URL")
    parser.add_argument("--dim", type=int, default=128, help="Vector dimension")
    args = parser.parse_args()
    
    # Load data
    domains = load_subdomains_json(args.json_file)
    print(f"📥 Loaded {len(domains)} domains from {args.json_file}")
    
    # Connect & create collection
    client = QdrantClient(url=args.url)
    if not ensure_collection(client, args.collection, args.dim):
        return
    
    # Upload
    upload_subdomains(client, args.collection, domains, args.dim)
    
    # Verify
    verify_upload(client, args.collection)


if __name__ == "__main__":
    main()