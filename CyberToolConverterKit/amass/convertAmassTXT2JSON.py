import argparse
import json


def parse_file(input_file, output_file):
    data = []
    entry_id = 1  # start IDs from 1

    with open(input_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue  # skip empty lines

            parts = line.split("-->")
            if len(parts) != 3:
                # optionally log or handle malformed lines
                continue

            left = parts[0].strip()
            relation = parts[1].strip()
            right = parts[2].strip()

            record = {
                "id": entry_id,
                "source": left,
                "relation": relation,
                "target": right
            }
            data.append(record)
            entry_id += 1

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def main():
    parser = argparse.ArgumentParser(
        description="Convert relationship lines from a text file into JSON."
    )
    parser.add_argument(
        "input_file",
        help="Path to the input text file (lines using '-->' as delimiter)."
    )
    parser.add_argument(
        "output_file",
        help="Path to the output JSON file."
    )

    args = parser.parse_args()

    parse_file(args.input_file, args.output_file)


if __name__ == "__main__":
    main()