<table align="center">
  <tr>
    <td align="center" width="50%">
      <a href="https://github.com/wpscanteam/wpscan">
        <img src="https://img.shields.io/badge/Open%20Source-10000000?style=flat&logo=github&logoColor=black" alt="WPscan open-source tool" width="100">
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
        <img src="https://github.com/1KevinFigueroa/vector4cyber/blob/main/RTFM-Knowledge/img/appLogos/wpscan.png" width="150" alt="dirsearch Logo">
      </a>
    </td>
    <td align="center" width="50%">
      <img src="https://github.com/1KevinFigueroa/vector4cyber/blob/main/RTFM-Knowledge/img/Vector4Cyber_extraSmalllogo.png" width="300" alt="Program Logo">
    </td>
  </tr>
</table>

# Converter WPscan results  → JSON Converter vectorized

Converting DIBR results from a plain text file to a structured JSON format makes a significant difference when the data is being vectorized. Properly structured JSON with unique IDs is extremely useful for aggregating and correlating complex data in a vectorized workflow. High-quality, fast, and accurate data is critical for red team pipelines, security dashboards, and vector databases.

The problem with subfinder's output to a text file will be structured subdomains in a list. When the output in a JSON file

### Usage

ingest3r_wpscan.py [-h] --collection COLLECTION [--vector-size VECTOR_SIZE] json_path

### WPScan JSON file structure output example ❌
"banner": {
    "description": "WordPress Security Scanner by the WPScan Team",
    "version": "3.8.25",
    "authors": [
      "@_WPScan_",
      "@ethicalhack3r",
      "@erwan_lr",
      "@firefart"
    ],
    "sponsor": "Sponsored by Automattic - <https://automattic.com/>"
  },
  "start_time": 1772106955,
  "start_memory": 56958976,
  "target_url": "<https://wordpress.com/>",
  "target_ip": "192.0.78.9",
  "effective_url": "<https://wordpress.com/>",
  "interesting_findings": [
    {
      "url": "https://wordpress.com/",
      "to_s": "Headers",
      "type": "headers",
      "found_by": "Headers (Passive Detection)",
      "confidence": 100,
      "confirmed_by": {

      },
      "references": {

      },
      "interesting_entries": [
        "server: nginx",
        "x-hacker: Want root?  Visit join.a8c.com/hacker and mention this header.",
        "host-header: WordPress.com",
        "x-ac: 1.dca _dca BYPASS",
        "alt-svc: h3=\":443\"; ma=86400",
        "server-timing: a8c-cdn, dc;desc=dca, cache;desc=BYPASS;dur=11.0"
      ]

### A JSON structure option to vectorized ✅

JSON file structure example:
{
    "id": 1,
    "banner": {
      "description": "WordPress Security Scanner by the WPScan Team",
      "version": "3.8.25",
      "authors": [
        "@_WPScan_",
        "@ethicalhack3r",
        "@erwan_lr",
        "@firefart"
      ],
      "sponsor": "Sponsored by Automattic - <https://automattic.com/>"
    },
    "start_time": 1772106955,
    "start_memory": 56958976,
    "target_url": "<https://wordpress.com/>",
    "target_ip": "192.0.78.9",
    "effective_url": "<https://wordpress.com/>",
    "interesting_findings": [
      {
        "url": "https://wordpress.com/",
        "to_s": "Headers",
        "type": "headers",
        "found_by": "Headers (Passive Detection)",
        "confidence": 100,
        "confirmed_by": {},
        "references": {},
        "interesting_entries": [
          "server: nginx",
          "x-hacker: Want root?  Visit join.a8c.com/hacker and mention this header.",
          "host-header: WordPress.com",
          "x-ac: 1.dca_dca BYPASS",
          "alt-svc: h3=\":443\"; ma=86400",
          "server-timing: a8c-cdn, dc;desc=dca, cache;desc=BYPASS;dur=11.0"
        ]

With a plain text file, two important pieces of information are missing: the original input and the source from which the data was obtained. From a cybersecurity perspective, these small but crucial data points are essential for traceability, context, and confident decision-making during analysis.

## Overview

From a high-level architecture perspective, the shift from flat-file ingestion to structured JSON isn't just a formatting preference; it’s the difference between a "data swamp" and a high-fidelity Cyber Threat Intelligence (CTI) pipeline.

In the world of vector databases—specifically Qdrant, Milvus, and Weaviate, context is the currency of accuracy. Here is the breakdown of why parsers is the "missing link" for these systems.

- Reads a text file containing subdomains
- Cleans and normalizes each line
- Assigns a unique, stable ID to every entry
- Serializes the result as JSON for downstream automation

Typical use cases:

- Ingesting into a **vector database** (Qdrant, Milvus, Weaviate, more coming soon etc.) for semantic search and correlation made easier
- Powering recon dashboards or graphs (e.g., host → vuln → service relationships)
- Joining subdomains with WHOIS, DNS, HTTP fingerprinting, or vulnerability scan data
