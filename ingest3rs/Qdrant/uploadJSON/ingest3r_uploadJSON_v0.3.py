import json
import os
import random
import sys
from typing import List, Dict, Any

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct

# ---------------- Configuration ---------------- #

QDRANT_URL = "http://localhost:6333"   # Local Qdrant
DEFAULT_COLLECTION_NAME = "JSONFILENAME"
DEFAULT_VECTOR_SIZE = 384               # Fallback size if we can't infer


# ---------------- Helper functions ---------------- #

def generate_dummy_vector(size: int) -> List[float]:
    """
    Generate a dummy vector for each record.
    Replace this with a real embedding model in production.
    """
    return [random.uniform(-1.0, 1.0) for _ in range(size)]


def load_json(path: str) -> List[Dict[str, Any]]:
    """
    Load JSON file and ensure it is a list of dicts.
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        raise ValueError("JSON root must be an array or object")

    records = [obj for obj in data if isinstance(obj, dict)]
    if not records:
        raise ValueError("No valid objects found in JSON")

    return records


def infer_vector_size_from_records(records: List[Dict[str, Any]]) -> int:
    """
    Infer vector size from JSON records.
    - If a record has a 'vector' field that is a list of numbers, use its length.
    - Otherwise fall back to DEFAULT_VECTOR_SIZE.
    """
    for r in records:
        vec = r.get("vector")
        if isinstance(vec, list) and vec and all(isinstance(x, (int, float)) for x in vec):
            return len(vec)

    return DEFAULT_VECTOR_SIZE


# ---------------- Qdrant upload logic ---------------- #

def create_collection_if_needed(client: QdrantClient, name: str, vector_size: int) -> None:
    """
    Create a new collection with given name and vector size.
    If it already exists, it will be deleted and recreated fresh.
    """
    if client.collection_exists(name):
        client.delete_collection(name)

    client.create_collection(
        collection_name=name,
        vectors_config=VectorParams(
            size=vector_size,
            distance=Distance.COSINE,
        ),
    )
    print(f"✓ Created collection '{name}' with vector size {vector_size}")


def upload_json_to_qdrant(
    json_path: str,
    collection_name: str,
    qdrant_url: str = QDRANT_URL,
) -> None:
    """
    Main function: read JSON file, infer vector size, create collection, upload points.
    """
    records = load_json(json_path)
    print(f"✓ Loaded {len(records)} records from {json_path}")

    vector_size = infer_vector_size_from_records(records)
    print(f"✓ Using vector size: {vector_size}")

    client = QdrantClient(url=qdrant_url)
    print(f"✓ Connected to Qdrant at {qdrant_url}")

    create_collection_if_needed(client, collection_name, vector_size)

    points: List[PointStruct] = []

    for idx, record in enumerate(records, start=1):
        point_id = record.get("id", idx)

        record_vector = record.get("vector")
        if isinstance(record_vector, list) and len(record_vector) == vector_size:
            vector = record_vector
        else:
            vector = generate_dummy_vector(vector_size)

        payload = record

        points.append(
            PointStruct(
                id=point_id,
                vector=vector,
                payload=payload,
            )
        )

    op_info = client.upsert(
        collection_name=collection_name,
        points=points,
        wait=True,
    )
    print(f"✓ Upsert completed with status: {op_info.status}")
    print(f"✓ Uploaded {len(points)} points into collection '{collection_name}'")

    print("\nSample payloads:")
    for p in points[:3]:
        print(f"  ID={p.id}  payload={p.payload}")


# ---------------- CLI entrypoint ---------------- #

if __name__ == "__main__":
    # Expected:
    #   python upload_json_to_qdrant.py <collection_name> <path/to/file.json>

    if len(sys.argv) != 3:
        print("Error: missing arguments.")
        print("Usage: python upload_json_to_qdrant.py <collection_name> <path/to/file.json>")
        sys.exit(1)

    collection_name = sys.argv[1]
    json_file = sys.argv[2]

    if not os.path.exists(json_file):
        print(f"Error: JSON file '{json_file}' not found.")
        print("Usage: python upload_json_to_qdrant.py <collection_name> <path/to/file.json>")
        sys.exit(1)

    try:
        upload_json_to_qdrant(json_file, collection_name=collection_name)
        print("\nDone. You can now query Qdrant on collection:", collection_name)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)