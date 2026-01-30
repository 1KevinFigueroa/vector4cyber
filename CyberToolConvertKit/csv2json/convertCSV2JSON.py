import csv
import json
import sys
from pathlib import Path


def csv_to_json_with_ids(csv_path: str, json_path: str) -> None:
    csv_file = Path(csv_path)
    if not csv_file.is_file():
        raise FileNotFoundError(f"CSV file not found: {csv_file}")

    records = []
    with csv_file.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=1):
            # Each row becomes a dict; add incremental id
            obj = {"id": idx}
            obj.update(row)
            records.append(obj)

    out_file = Path(json_path)
    with out_file.open("w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(records)} records to {out_file}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        script = Path(sys.argv[0]).name
        print(f"Usage: python {script} input.csv output.json")
        sys.exit(1)

    csv_input = sys.argv[1]
    json_output = sys.argv[2]
    csv_to_json_with_ids(csv_input, json_output)