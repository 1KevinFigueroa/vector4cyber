import json
import xmltodict
import sys
from pathlib import Path


def xml_to_json(xml_path: str, json_path: str) -> None:
    xml_file = Path(xml_path)
    if not xml_file.is_file():
        raise FileNotFoundError(f"XML file not found: {xml_file}")

    # Read and parse XML into a Python dict
    with xml_file.open("r", encoding="utf-8") as f:
        data_dict = xmltodict.parse(f.read())

    # Convert dict to pretty JSON string
    json_str = json.dumps(data_dict, indent=2)

    # Write JSON to output file
    out_file = Path(json_path)
    with out_file.open("w", encoding="utf-8") as f:
        f.write(json_str)

    print(f"Converted '{xml_file}' -> '{out_file}'")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: python {Path(sys.argv[0]).name} input.xml output.json")
        sys.exit(1)

    xml_input = sys.argv[1]
    json_output = sys.argv[2]
    xml_to_json(xml_input, json_output)