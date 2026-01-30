#!/usr/bin/env python3
"""
Load XML file into Qdrant Vector Database
Reads XML → Converts to JSON → Creates collection → Uploads points with embeddings
"""

import xmltodict
import json
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct
import random
import sys
import os

# Configuration
QDRANT_URL = "http://localhost:6333"
VECTOR_SIZE = 384  # From your earlier context
DEFAULT_XML_FILE = "<XML FILENAME>.xml"  # Replace <XML FILENAME> with the XML of choice

def generate_dummy_vector(size=31):
    """Generate dummy vector for demonstration (replace with real embeddings)"""
    return [random.uniform(-1.0, 1.0) for _ in range(size)]

def xml_to_qdrant(xml_file, collection_name="ransomware_db", vector_size=31):
    """Read XML file, parse to dict, upload to Qdrant collection"""
    
    # Connect to Qdrant
    client = QdrantClient(QDRANT_URL)
    print(f"✓ Connected to Qdrant at {QDRANT_URL}")
    
    # Delete existing collection (fresh start)
    try:
        client.delete_collection(collection_name)
        print(f"✓ Deleted existing collection '{collection_name}'")
    except:
        pass
    
    # Create new collection
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
    )
    print(f"✓ Created collection '{collection_name}' ({vector_size}-dim)")
    
    # Read and parse XML
    print(f"📖 Reading XML: {xml_file}")
    with open(xml_file, 'r', encoding='utf-8') as f:
        xml_content = f.read()
    
    # Convert XML to dict
    data_dict = xmltodict.parse(xml_content)
    print("✓ XML parsed to dictionary")
    
    # Extract ransomware entries (handles both RansomwareAttacks and Vulnerabilities)
    root_key = list(data_dict.keys())[0]
    entries = data_dict[root_key]
    
    if not isinstance(entries, list):
        entries = [entries] if isinstance(entries, dict) else []
    
    points = []
    for i, entry in enumerate(entries, 1):
        # Handle different XML structures (RansomwareAttacks or Vulnerabilities)
        if "Ransomware" in str(type(entry)):
            payload = {
                "rank": int(entry.get("@rank", i)),
                "name": entry.get("name", ""),
                "ransom_extension": entry.get("ransom_extension", ""),
                "description": entry.get("description", ""),
                "impact": entry.get("impact", ""),
                "first_seen": entry.get("first_seen", "")
            }
        elif "Vulnerability" in str(type(entry)):
            payload = {
                "rank": int(entry.get("@rank", i)),
                "name": entry.get("name", ""),
                "cwe": entry.get("cwe", ""),
                "cwe_description": entry.get("cwe_description", ""),
                "impact": entry.get("impact", ""),
                "type": entry.get("type", "")
            }
        else:
            # Generic payload extraction
            payload = {k: str(v) for k, v in entry.items() if k != "@rank"}
            payload["rank"] = int(entry.get("@rank", i))
        
        # Generate vector (replace with real embedding model in production)
        vector = generate_dummy_vector(vector_size)
        
        # Create Qdrant point
        point = PointStruct(
            id=i,
            vector=vector,
            payload=payload
        )
        points.append(point)
    
    # Batch upload to Qdrant
    if points:
        client.upsert(
            collection_name=collection_name,
            points=points,
            wait=True
        )
        print(f"✓ Uploaded {len(points)} points to '{collection_name}'!")
        
        # Show sample
        print("\n📋 Sample entries uploaded:")
        for point in points[:3]:
            print(f"  ID {point.id}: {point.payload['name']} ({point.payload['impact']})")
    else:
        print("⚠️ No entries found in XML")
    
    return client, collection_name

if __name__ == "__main__":
    # CLI usage
    xml_file = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_XML_FILE
    
    if not os.path.exists(xml_file):
        print(f"❌ Error: XML file '{xml_file}' not found!")
        print("Usage: python xml_to_qdrant.py top20_ransomware.xml")
        sys.exit(1)
    
    try:
        client, collection_name = xml_to_qdrant(xml_file)
        print(f"\n🎉 Success! Check Qdrant dashboard: http://localhost:6333/collections/{collection_name}")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)