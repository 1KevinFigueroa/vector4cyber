#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct
import numpy as np
from typing import List, Dict

def create_simple_embedding(text: str, dim: int = 128) -> List[float]:
    """
    Simple hash-based embedding for demo purposes.
    In production, use sentence-transformers or OpenAI embeddings.
    """
    # Simple character n-gram based embedding
    vec = np.zeros(dim)
    for i, char in enumerate(text.lower()):
        if i >= dim:
            break
        vec[i] = (ord(char) % 256) / 255.0
    return vec.tolist()

def upload_to_qdrant(json_file: str, collection_name: str = "sslscan_results"):
    """Parse sslscan JSON and upload to local Qdrant."""
    
    # Connect to local Qdrant (default: http://localhost:6333)
    client = QdrantClient("localhost", port=6333)
    
    print(f"Connecting to Qdrant at localhost:6333...")
    
    # Read JSON results
    with open(json_file, 'r') as f:
        sslscan_data = json.load(f)
    
    print(f"Loaded {len(sslscan_data)} sslscan entries")
    
    # Create collection if it doesn't exist
    try:
        if client.collection_exists(collection_name):
            print(f"Collection '{collection_name}' exists. Deleting...")
            client.delete_collection(collection_name)
        
        # Create new collection with 128-dim vectors
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=128, distance=Distance.COSINE)
        )
        print(f"Created collection '{collection_name}'")
        
    except Exception as e:
        print(f"Error creating collection: {e}")
        return
    
    # Prepare points for upload
    points = []
    
    for entry in sslscan_data:
        entry_id = entry["id"]
        
        # Create text summary for embedding
        summary = (
            f"{entry.get('target', 'N/A')} "
            f"{entry.get('ip', 'N/A')} "
            f"TLS protocols: {list(entry.get('protocols', {}).keys())} "
            f"Ciphers: {len(entry.get('ciphers', []))} "
            f"Subject: {entry['certificate'].get('subject', 'N/A')}"
        )
        
        # Generate simple embedding
        vector = create_simple_embedding(summary)
        
        # Full payload with all sslscan data
        payload = {
            "id": entry["id"],
            "ip": entry.get("ip"),
            "target": entry.get("target"),
            "port": entry.get("port", 443),
            "sni": entry.get("sni"),
            "protocols": entry.get("protocols", {}),
            "ciphers_count": len(entry.get("ciphers", [])),
            "weak_protocols": sum(1 for k, v in entry.get("protocols", {}).items() if v == "enabled" and "TLSv1.0" in k or "TLSv1.1" in k),
            "certificate_subject": entry["certificate"].get("subject"),
            "certificate_issuer": entry["certificate"].get("issuer"),
            "certificate_altnames_count": len(entry["certificate"].get("altnames", [])),
            "summary": summary,
            **entry.get("certificate", {})
        }
        
        point = PointStruct(
            id=entry_id,
            vector=vector,
            payload=payload
        )
        points.append(point)
    
    # Upload in batches to avoid memory issues
    batch_size = 50
    for i in range(0, len(points), batch_size):
        batch = points[i:i + batch_size]
        client.upsert(
            collection_name=collection_name,
            points=batch
        )
        print(f"Uploaded batch {i//batch_size + 1} ({len(batch)} points)")
    
    print(f"\n✅ SUCCESS: Uploaded {len(points)} sslscan entries to Qdrant!")
    print(f"Collection: '{collection_name}'")
    print(f"Access at: http://localhost:6333/dashboard")
    
    # Verify upload
    count = client.count(collection_name=collection_name)
    print(f"Verification: {count.count} points in collection")

def main():
    parser = argparse.ArgumentParser(description="Upload sslscan JSON to Qdrant")
    parser.add_argument("json_file", help="Path to sslscan JSON file")
    parser.add_argument("--collection", default="sslscan_results", help="Qdrant collection name")
    
    args = parser.parse_args()
    
    # Verify Qdrant is running
    try:
        client = QdrantClient("localhost", port=6333)
        client.get_collections()
        print("✅ Qdrant connection OK")
    except:
        print("❌ Qdrant not running at localhost:6333")
        print("Start with: docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant")
        return
    
    upload_to_qdrant(args.json_file, args.collection)

if __name__ == "__main__":
    main()
