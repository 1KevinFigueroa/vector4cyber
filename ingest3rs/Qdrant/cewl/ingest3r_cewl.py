#!/usr/bin/env python3
import argparse
import json
import os
from typing import List, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct

DEFAULT_VECTOR_SIZE = 384
DEFAULT_HOST = "localhost"
DEFAULT_PORT = 6333

def generate_word_embedding(word: str, size: int = DEFAULT_VECTOR_SIZE) -> List[float]:
    vec = [0.0] * size
    for i, char in enumerate(word.lower()):
        if i >= size:
            break
        vec[i] = (ord(char) - ord('a')) / 25.0 if char.isalpha() else ord(char) % 256 / 255.0
    return vec

def load_word_json(json_file: str) -> List[Dict[str, Any]]:
    if not os.path.exists(json_file):
        raise FileNotFoundError(f"JSON file not found: {json_file}")
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    elif isinstance(data, dict):
        return [data]
    else:
        raise ValueError("JSON root must be an object or array")

def upload_words_to_qdrant(json_path: str, collection: str, vector_size: int) -> None:
    client = QdrantClient(host=DEFAULT_HOST, port=DEFAULT_PORT)
    print(f"✅ Connected to Qdrant at {DEFAULT_HOST}:{DEFAULT_PORT}")

    words = load_word_json(json_path)
    print(f"✅ Loaded {len(words)} word entries from {json_path}")

    if client.collection_exists(collection):
        print(f"Collection '{collection}' exists. Recreating...")
        client.delete_collection(collection)

    client.create_collection(
        collection_name=collection,
        vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
    )
    print(f"✅ Created collection '{collection}' (vector_size={vector_size})")

    points: List[PointStruct] = []
    for item in words:
        word_id = item.get("id")
        if word_id is None:
            continue
        word = item.get("word", "")
        vector = generate_word_embedding(word, vector_size)
        payload = {
            "id": word_id,
            "word": word,
            "lowercase": item.get("lowercase", ""),
            "length": item.get("length", 0),
            "line_number": item.get("line_number", 0),
        }
        points.append(PointStruct(id=word_id, vector=vector, payload=payload))

    if not points:
        print("❌ No valid points to upload")
        return

    client.upsert(collection_name=collection, points=points, wait=True)
    print(f"✅ Uploaded {len(points)} points to '{collection}'")

def main():
    parser = argparse.ArgumentParser(
        description="Upload word JSON to Qdrant (1 word = 1 point)"
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
        help="Path to word JSON file",
    )

    args = parser.parse_args()

    upload_words_to_qdrant(
        json_path=args.json_path,
        collection=args.collection,
        vector_size=args.vector_size,
    )

if __name__ == "__main__":
    main()
