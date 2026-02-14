# Subdomain Text → JSON Converter

Convert subdomains from a plain text file into structured JSON with IDs for use in pipelines, dashboards, or vector databases.

---

## Overview

Many recon tools (like `sublist3r`, `subfinder`, `amass`, etc.) output parser to come...

**one subdomain per line** to a text file. This repository provides a simple Python script that:

- Reads a text file containing subdomains
- Cleans and normalizes each line
- Assigns a unique ID to every entry
- Writes everything to a JSON file

Example use cases:

- Feeding subdomains into a **vector database** (Qdrant, Milvus, etc.)
- Building recon dashboards
- Correlating subdomains with WHOIS, DNS, or vulnerability scan data

---

## Input Format

The script expects a text file with **one subdomain per line**, for example:

```text
