<table align="center">
  <tr>
    <td align="center" width="50%">
      <a href="https://github.com/sullo/nikto">
        <img src="https://img.shields.io/badge/Open%20Source-ff0000?style=flat&logo=github&logoColor=black" alt="Nikto open-source tool" width="100">
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
        <img src="https://github.com/1KevinFigueroa/vector4cyber/blob/main/RTFM-Knowledge/img/appLogos/nikto.png" width="150" alt="Amass Logo">
      </a>
    </td>
    <td align="center" width="50%">
      <img src="https://github.com/1KevinFigueroa/vector4cyber/blob/main/RTFM-Knowledge/img/Vector4Cyber_extraSmalllogo.png" width="300" alt="Program Logo">
    </td>
  </tr>
</table>

# Converter Nikto JSON file  → JSON file to vectorized

Converting Subfinder results from a plain text file to a structured JSON format makes a significant difference when the data is being vectorized. Properly structured JSON with unique IDs is extremely useful for aggregating and correlating complex data in a vectorized workflow. High-quality, fast, and accurate data is critical for red team pipelines, security dashboards, and vector databases.

The problem with subfinder's output to a text file will be structured subdomains in a list. When the output in a JSON file 


### Nikto JSON file structure output example ❌
{"host":"www..com","ip":"","port":"443","banner":"cloudflare","vulnerabilities":[{"id": "999986","method":"GET","url":"","msg":"/: Retrieved via header: 1.1 8dd4c7f1d7b55b5ac0fc5b7f8532cf32.cloudfront.net (CloudFront)."},{"id": "999986","method":"GET","url":"","msg":"/: Retrieved x-powered-by header: Next.js."},{"id": "95","references": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Cookies","method":"GET","url":"","msg":"/: Cookie selected_country created without the httponly flag."},

### A JSON structure option to vectorized ✅
JSON file structure example:
"scan_info": {
    "target": " ",
    "scanner": "Nikto",
    "total_findings": 32,
    "timestamp": "",
    "input_file": " .json"
  },
  "findings": [
    {
      "id": 1,
      "target": "unknown",
      "url": "",
      "method": "GET",
      "message": "/: Retrieved via header: 1.1 8dd4c7f1d7b55b5ac0fc5b7f8532cf32.cloudfront.net (CloudFront).",
      "osvdb": "",
      "id_nikto": "999986",
      "risk": "medium",
      "severity": ""
    },

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