<table align="center">
  <tr>
    <td align="center" width="50%">
      <a href=" ">
        <img src="https://img.shields.io/badge/Python%20WHOIS-active-%23FF5F1F?style=flat&logo=simple-icons&logoColor=white" alt="File Type" width="100">
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
        <img src="https://github.com/1KevinFigueroa/vector4cyber/blob/main/RTFM-Knowledge/img/appLogos/whois.png" width="150" alt="Amass Logo">
      </a>
    </td>
    <td align="center" width="50%">
      <img src="https://github.com/1KevinFigueroa/vector4cyber/blob/main/RTFM-Knowledge/img/Vector4Cyber_extraSmalllogo.png" width="300" alt="Program Logo">
    </td>
  </tr>
</table>

# Convert Python WHOIS query → JSON file vectorized

Converting Python WHOIS results from a plain text file to a structured JSON format makes a significant difference when the data is being vectorized. Properly structured JSON with unique IDs is extremely useful for aggregating and correlating complex data in a vectorized workflow. High-quality, fast, and accurate data is critical for red team pipelines, security dashboards, and vector databases.

The problem with subfinder's output to a text file will be structured subdomains in a list. When the output in a JSON file 

### Subfinder TEXT file structure output example ❌

example.com

### Subfinder JSON file structure output example ❌
{"host":"aleksandr-kulishov.yandex.ru","input":"yandex.ru","source":"reconeer"}

### A JSON structure option to vectorized ✅
JSON file structure example:
{
    "id": ,
    "domain": " ",
    "timestamp": " ",
    "whois_data": {
      "domain_name": "",
      "registrar": "RU-CENTER-RU",
      "creation_date": "1997-09-23 09:45:07+00:00",
      "expiration_date": "2026-09-30 21:00:00+00:00",
      "updated_date": "None",
      "name_servers": [
        " ",
        " "
      ],
      "status": "REGISTERED, DELEGATED, VERIFIED",
      "emails": null,
      "country": null,
      "state": null,
      "city": null,
      "organization": "null",
      "registrant": {
        "name": null,
        "organization": null,
        "street": null,
        "city": null,
        "state": null,
        "postal_code": null,
        "country": null
      }
    },
    "raw_whois": "% TCI Whois Service. Terms of use:\n% <https://tcinet.ru/documents/whois_ru_rf.pdf> (in Russian)\n% <https://tcinet.ru/documents/whois_su.pdf> (in Russian)\n\ndomain:                 REGISTERED, DELEGATED, VERIFIED\norg:   \ntaxpayer-id:   7736207543\nregistrar:     RU-CENTER-RU\nadmin-contact: <https://www.nic.ru/whois\ncreated>:       1997-09-23T09:45:07Z\npaid-till:     2026-09-30T21:00:00Z\nfree-date:     2026-11-01\nsource:        TCI\n\nLast updated on 2026-01-25T03:43:01Z\n\n"
  }

With a plain text file, two important pieces of information are missing: the original input and the source from which the data was obtained. From a cybersecurity perspective, these small but crucial data points are essential for traceability, context, and confident decision-making during analysis.

## Overview
From a high-level architecture perspective, the shift from flat-file ingestion to structured JSON isn't just a formatting preference; it’s the difference between a "data swamp" and a high-fidelity Cyber Threat Intelligence (CTI) pipeline.

In the world of vector databases—specifically Qdrant, Milvus, and Weaviate, context is the currency of accuracy. Here is the breakdown of why parsers is the "missing link" for these systems.

- Reads a text file containing subdomains (e.g., from `subfinder -silent -o subs.txt`)
- Cleans and normalizes each line
- Assigns a unique, stable ID to every entry
- Serializes the result as JSON for downstream automation

Typical use cases:

- Ingesting subdomains into a **vector database** (Qdrant, Milvus, Weaviate, more coming soon etc.) for semantic search and correlation made easier
- Powering recon dashboards or graphs (e.g., host → vuln → service relationships)
- Joining subdomains with WHOIS, DNS, HTTP fingerprinting, or vulnerability scan data