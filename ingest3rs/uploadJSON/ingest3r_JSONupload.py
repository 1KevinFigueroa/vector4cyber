import json
import os
import random
import sys
from typing import List, Dict, Any

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct  # [web:94][web:168]

# ---------------- Configuration ---------------- #

QDRANT_URL = "http://localhost:6333"   # Local Qdrant
COLLECTION_NAME = "<COLLECTION NAME>"     # Change this value to reflect Qdrant Collection
VECTOR_SIZE = 384                       # Adjust to your embedding dimension
DEFAULT_JSON_FILE = "<CHANGE NAME>.json" # CHANGE THIS JSON FILE NAME BEGIN UPLOADED 


# ---------------- Helper functions ---------------- #

def generate_dummy_vector(size: int = VECTOR_SIZE) -> List[float]:
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
        # Single object -> wrap into list
        data = [data]
    if not isinstance(data, list):
        raise ValueError("JSON root must be an array or object")

    # Ensure each element is a dict
    records = [obj for obj in data if isinstance(obj, dict)]
    if not records:
        raise ValueError("No valid objects found in JSON")

    return records


# ---------------- Qdrant upload logic ---------------- #

def create_collection_if_needed(client: QdrantClient, name: str, vector_size: int) -> None:
    """
    Create a new collection with given name and vector size.
    If it already exists, it will be deleted and recreated fresh.
    """
    if client.collection_exists(name):
        client.delete_collection(name)  # start clean [web:165][web:170]

    client.create_collection(
        collection_name=name,
        vectors_config=VectorParams(
            size=vector_size,
            distance=Distance.COSINE
        ),
    )  # [web:94][web:168]
    print(f"✓ Created collection '{name}' with vector size {vector_size}")


def upload_json_to_qdrant(
    json_path: str,
    collection_name: str = COLLECTION_NAME,
    vector_size: int = VECTOR_SIZE,
    qdrant_url: str = QDRANT_URL,
) -> None:
    """
    Main function: read JSON file, create collection, upload points.
    """
    # Connect to Qdrant
    client = QdrantClient(url=qdrant_url)  # [web:170][web:171]
    print(f"✓ Connected to Qdrant at {qdrant_url}")

    # Create / reset collection
    create_collection_if_needed(client, collection_name, vector_size)

    # Load JSON records
    records = load_json(json_path)
    print(f"✓ Loaded {len(records)} records from {json_path}")

    points: List[PointStruct] = []

    for idx, record in enumerate(records, start=1):
        # Use explicit 'id' if present, otherwise auto index
        point_id = record.get("id", idx)

        # Vector (dummy)
        vector = generate_dummy_vector(vector_size)

        # Payload is the full JSON object
        payload = record

        points.append(
            PointStruct(
                id=point_id,
                vector=vector,
                payload=payload,
            )
        )

    # Upsert in one batch for small/medium datasets [web:54][web:166][web:167]
    op_info = client.upsert(
        collection_name=collection_name,
        points=points,
        wait=True,
    )
    print(f"✓ Upsert completed with status: {op_info.status}")
    print(f"✓ Uploaded {len(points)} points into collection '{collection_name}'")

    # Show a small preview
    print("\nSample payloads:")
    for p in points[:3]:
        print(f"  ID={p.id}  payload={p.payload}")


# ---------------- CLI entrypoint ---------------- #

if __name__ == "__main__":
    if len(sys.argv) > 1:
        json_file = sys.argv[1]
    else:
        json_file = DEFAULT_JSON_FILE
        print(f"No JSON file specified, defaulting to '{json_file}'")

    if not os.path.exists(json_file):
        print(f"Error: JSON file '{json_file}' not found.")
        print("Usage: python upload_json_to_qdrant.py path/to/file.json")
        sys.exit(1)

    try:
        upload_json_to_qdrant(json_file)
        print("\nDone. You can now query Qdrant on collection:", COLLECTION_NAME)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)