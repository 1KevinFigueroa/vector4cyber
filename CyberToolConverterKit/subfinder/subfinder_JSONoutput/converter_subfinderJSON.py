import json
import argparse

def parse_args():
    parser = argparse.ArgumentParser(
        description="Read line-delimited JSON, add IDs, write to new JSON file."
    )
    parser.add_argument(
        "input_file",
        help="Path to input JSON lines file (one JSON object per line)."
    )
    parser.add_argument(
        "output_file",
        help="Path to output JSON file (array of objects with id field first)."
    )
    return parser.parse_args()

def main():
    args = parse_args()
    results = []
    next_id = 1

    with open(args.input_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)

            # Create a new dict with id first, then the rest of the fields
            new_obj = {"id": next_id}
            new_obj.update(obj)

            results.append(new_obj)
            next_id += 1

    with open(args.output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    main()