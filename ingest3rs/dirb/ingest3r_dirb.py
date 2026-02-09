#!/usr/bin/env python3
import json
import argparse
from typing import List, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct
import numpy as np

def load_dirb_json(json_file: str) -> List[Dict[str, Any]]:
    """Load parsed dirb JSON file."""
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get('results', [])

def create_dummy_vector(dim: int = 128) -> List[float]:
    """Generate a dummy vector for dirb entries (replace with real embeddings later)."""
    return list(np.random.rand(dim).astype(np.float32))

def import_to_qdrant(json_file: str, collection_name: str, qdrant_url: str = "http://localhost:6333"):
    """Import dirb results into new Qdrant collection."""
    
    # Connect to Qdrant
    client = QdrantClient(url=qdrant_url)
    
    # Create collection if it doesn't exist
    try:
        client.recreate_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=128, distance=Distance.COSINE)
        )
        print(f"✅ Collection '{collection_name}' created/recreated")
    except Exception as e:
        print(f"❌ Collection creation failed: {e}")
        return
    
    # Load dirb data
    entries = load_dirb_json(json_file)
    if not entries:
        print("❌ No entries found in JSON file")
        return
    
    print(f"📥 Loading {len(entries)} entries...")
    
    # Convert to Qdrant points
    points = []
    for entry in entries:
        # Use 'id' field or line_number as point ID
        point_id = entry.get('id') or entry.get('line_number')
        
        # Create payload from all fields
        payload = {k: v for k, v in entry.items() if k not in ['id', 'line_number']}
        payload['raw_line'] = entry.get('raw_line', '')
        
        point = PointStruct(
            id=point_id,
            vector=create_dummy_vector(),
            payload=payload
        )
        points.append(point)
    
    # Batch upsert
    client.upsert(
        collection_name=collection_name,
        points=points,
        wait=True
    )
    
    print(f"✅ Successfully imported {len(points)} points to '{collection_name}'")
    
    # Verify
    count = client.count(collection_name=collection_name)
    print(f"📊 Collection '{collection_name}' now contains {count.count} points")

def main():
    parser = argparse.ArgumentParser(description="Import dirb JSON to Qdrant collection")
    parser.add_argument("json_file", help="Path to dirb JSON file (from previous parser)")
    parser.add_argument("collection", help="Qdrant collection name")
    parser.add_argument("--url", default="http://localhost:6333", help="Qdrant URL")
    args = parser.parse_args()
    
    import_to_qdrant(args.json_file, args.collection, args.url)

if __name__ == "__main__":
    main()