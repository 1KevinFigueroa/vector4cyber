# Convert CSV file  → JSON file vectorized

Converting structed CSV file result file and a structured JSON format makes a significant difference when the data is being vectorized. Properly structured JSON with unique IDs is extremely useful for aggregating and correlating complex data in a vectorized workflow. High-quality, fast, and accurate data is critical for red team pipelines, security dashboards, and vector databases.

The problem with subfinder's output to a text file will be structured subdomains in a list. When the output in a JSON file 

### CSV file structure output example ❌

example.com, IP address, port

### A JSON structure option to vectorized ✅
JSON file structure example:
{"id": 1, "host": "example.com", "input": "example.com", "source": " "}

With a plain text file, two important pieces of information are missing: the original input and the source from which the data was obtained. From a cybersecurity perspective, these small but crucial data points are essential for traceability, context, and confident decision-making during analysis.

## Overview
From a high-level architecture perspective, the shift from flat-file ingestion to structured JSON isn't just a formatting preference; it’s the difference between a "data swamp" and a high-fidelity Cyber Threat Intelligence (CTI) pipeline.

In the world of vector databases—specifically Qdrant, Milvus, and Weaviate, context is the currency of accuracy. Here is the breakdown of why parsers is the "missing link" for these systems.

- Reads a text file containing subdomains 
- Cleans and normalizes each line
- Assigns a unique, stable ID to every entry
- Serializes the result as JSON for downstream automation

Typical use cases:

- Ingesting subdomains into a **vector database** (Qdrant, Milvus, Weaviate, more coming soon etc.) for semantic search and correlation made easier
- Powering recon dashboards or graphs (e.g., host → vuln → service relationships)
- Joining subdomains with WHOIS, DNS, HTTP fingerprinting, or vulnerability scan data