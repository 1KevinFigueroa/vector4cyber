# dnsx Convert3r

Converts ProjectDiscovery `dnsx -json` JSONL output into Vector4Cyber JSON records.

```bash
python convert3r_dnsx.py dnsx_output.jsonl -o enriched_dnsx.json
```

The converter keeps the raw dnsx object in `raw_response`, assigns sequential `id` values, and normalizes DNS record fields (`a`, `aaaa`, `cname`, `mx`, `ns`, `txt`, `soa`, `srv`, `ptr`, `caa`) to lists.

No sample or dummy data is committed with this converter; create local test files outside the repo or in ignored paths when needed.
