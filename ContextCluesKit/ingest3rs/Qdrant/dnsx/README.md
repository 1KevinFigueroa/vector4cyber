# dnsx Qdrant Ingest3r

Uploads converted dnsx records to Qdrant and can correlate them with existing subdomain collections.

```bash
python ingest3r_dnsx.py enriched_dnsx.json dnsx_records
python ingest3r_dnsx.py enriched_dnsx.json dnsx_records --skip-correlation
python ingest3r_dnsx.py enriched_dnsx.json dnsx_records --correlation-collections Subfinder_json subfinder
```

By default, correlation searches common subdomain payload fields (`hostname`, `host`, `subdomain`, `domain`, `name`) in current Vector4Cyber-style collections such as `Subfinder_json`. Matched subdomain records are updated with latest DNS metadata and resolved IP fields.

Runtime dependency: `qdrant-client`. Embeddings are deterministic fallback vectors unless `--embed` is used and `sentence-transformers` is installed.
