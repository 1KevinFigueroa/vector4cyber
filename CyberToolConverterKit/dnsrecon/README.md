<table align="center">
  <tr>
    <td align="center" width="50%">
      <a href="https://github.com/darkoperator/dnsrecon">
        <img src="https://img.shields.io/badge/Open%20Source-10000000?style=flat&logo=github&logoColor=black" alt="DNSRecon open-source tool" width="100">
      </a>
    </td>
    <td align="center" width="50%">
      <a href="https://github.com/1KevinFigueroa/vector4cyber/blob/main/LICENSE">
        <img src="https://img.shields.io/badge/License-Apache%202.0-brightgreen?labelColor=gray&logo=github" alt="Apache 2.0">
    </a>
      </a>
    </td>
  </tr>
  <tr>
    <td align="center" width="50%">
      <a href="">
        <img src="https://github.com/1KevinFigueroa/vector4cyber/blob/main/RTFM-Knowledge/img/appLogos/dnsrecon.png" width="300" alt="Amass Logo">
      </a>
    </td>
    <td align="center" width="50%">
      <img src="https://github.com/1KevinFigueroa/vector4cyber/blob/main/RTFM-Knowledge/img/Vector4Cyber_extraSmalllogo.png" width="300" alt="Program Logo">
    </td>
  </tr>
</table>


# Converter DNSRecon results  → JSON Converter vectorized

Converting DNSRecon results from a plain text file to a structured JSON format makes a significant difference when the data is being vectorized. Properly structured JSON with unique IDs is extremely useful for aggregating and correlating complex data in a vectorized workflow. High-quality, fast, and accurate data is critical for red team pipelines, security dashboards, and vector databases.

The problem with subfinder's output to a text file will be structured subdomains in a list. When the output in a JSON file.

### Usage:
convert_dnsrecon.py [-h] input_csv output_json

### DNSRecon CSV file structure output example ❌
MX, , ,,, MX, , ,,, A, , ,,, A, , ,,, AAAA, , ,,, AAAA, , ,,, TXT, ,,,,'dropbox-domain-verification= '

### A JSON structure option to vectorized ✅
JSON file structure example:
"scan_info": { "input_file": "dnsrecon.csv", "total_records": 39, "headers": [ "Type", "Name", "Address", "Target", "Port", "String" ] }, "records": [ { "id": 1, "type": "SOA", "name": "alina.ns.cloudflare.com", "address": " ", "target": "", "port": "", "string": "" },

With a plain text file, two important pieces of information are missing: the original input and the source from which the data was obtained. From a cybersecurity perspective, these small but crucial data points are essential for traceability, context, and confident decision-making during analysis.

## Overview
From a high-level architecture perspective, the shift from flat-file ingestion to structured JSON isn't just a formatting preference; it’s the difference between a "data swamp" and a high-fidelity Cyber Threat Intelligence (CTI) pipeline.

In the world of vector databases—specifically Qdrant, Milvus, and Weaviate, context is the currency of accuracy. Here is the breakdown of why parsers is the "missing link" for these systems.

- Reads a text file containing subdomains
- Cleans and normalizes each line
- Assigns a unique, stable ID to every entry
- Serializes the result as JSON for downstream automation

Typical use cases:

- Ingesting subdomains into a **vector database** and allow a user to select vector sizing (Qdrant, Milvus, Weaviate, more coming soon etc.) for semantic search and correlation made easier
- Powering recon dashboards or graphs (e.g., host → vuln → service relationships)
- Joining subdomains with WHOIS, DNS, HTTP fingerprinting, or vulnerability scan data