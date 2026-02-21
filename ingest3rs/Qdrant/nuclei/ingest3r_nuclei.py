#!/usr/bin/env python3
import argparse
import json
import uuid

from qdrant_client import QdrantClient, models


def parse_args():
    parser = argparse.ArgumentParser(
        description="Load Nuclei JSON results into a new Qdrant collection."
    )
    parser.add_argument(
        "json_file",
        help="Path to Nuclei JSON/JSONL output file",
    )
    parser.add_argument(
        "collection_name",
        help="Name of the Qdrant collection to create and populate",
    )
    parser.add_argument(
        "--qdrant-url",
        default="http://localhost:6333",
        help="Qdrant URL (default: http://localhost:6333)",
    )
    parser.add_argument(
        "--vector-size",
        type=int,
        default=4,
        help="Dimension of placeholder vectors (default: 4)",
    )
    return parser.parse_args()


def ensure_collection(client: QdrantClient, collection_name: str, dim: int):
    # Create collection if it does not exist
    collections = [c.name for c in client.get_collections().collections]
    if collection_name in collections:
        raise RuntimeError(f"Collection '{collection_name}' already exists.")

    client.recreate_collection(
        collection_name=collection_name,
        vectors_config=models.VectorParams(size=dim, distance=models.Distance.COSINE),
    )


def load_nuclei_results(path: str):
    """
    Supports:
      - single JSON object
      - JSON array
      - JSONL (one JSON object per line)
    """
    results = []
    with open(path, "r", encoding="utf-8") as f:
        content = f.read().strip()

    if not content:
        return results

    # Try JSON array or single object first
    try:
        data = json.loads(content)
        if isinstance(data, list):
            results = data
        else:
            results = [data]
        return results
    except json.JSONDecodeError:
        pass

    # Fallback: treat as JSONL
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                results.append(obj)
            except json.JSONDecodeError:
                # Skip malformed lines
                continue
    return results


def main():
    args = parse_args()

    client = QdrantClient(url=args.qdrant_url)

    # Create a fresh collection
    ensure_collection(client, args.collection_name, args.vector_size)

    nuclei_results = load_nuclei_results(args.json_file)
    if not nuclei_results:
        print("No Nuclei results found in the file.")
        return

    points = []
    for item in nuclei_results:
        # Use UUIDs for point IDs
        point_id = str(uuid.uuid4())

        # Placeholder vector (replace with real embeddings if desired)
        vector = [0.0] * args.vector_size

        # Store the full Nuclei record as payload
        payload = item

        points.append(
            models.PointStruct(
                id=point_id,
                vector=vector,
                payload=payload,
            )
        )

    client.upsert(
        collection_name=args.collection_name,
        points=points,
        wait=True,
    )

    print(f"Inserted {len(points)} points into collection '{args.collection_name}'.")


if __name__ == "__main__":
    main()