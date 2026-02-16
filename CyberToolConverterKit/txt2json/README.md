<table align="center">
  <tr>
    <td align="center" width="50%">
      <a href=" ">
        <img src="https://img.shields.io/badge/TXT2JSON-active-00ff00?style=flat&logo=simple-icons&logoColor=white" alt="File Type" width="100">
      </a>
    </td>
    <td align="center" width="50%">
      <a href="https://github.com/1KevinFigueroa/vector4cyber/blob/main/LICENSE">
        <img src="https://img.shields.io/badge/License-Apache%202.0-brightgreen?labelColor=gray&logo=github" alt="Apache 2.0 License">
      </a>
    </td>
  </tr>
  <tr>
    <td align="center" width="50%">
      <a href="">
        <img src="https://github.com/1KevinFigueroa/vector4cyber/blob/main/RTFM-Knowledge/img/appLogos/txt.png" width="150" alt="Amass Logo">
      </a>
    </td>
    <td align="center" width="50%">
      <img src="https://github.com/1KevinFigueroa/vector4cyber/blob/main/RTFM-Knowledge/img/Vector4Cyber_extraSmalllogo.png" width="300" alt="Program Logo">
    </td>
  </tr>
</table>

# Converter  Plain Text → JSON file vectorized

Convert a plain text file into structured JSON with IDs for use in pipelines, dashboards, or vector databases.

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
