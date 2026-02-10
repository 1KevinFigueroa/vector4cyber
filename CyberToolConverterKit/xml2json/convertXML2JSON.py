import xmltodict
import json
import sys
import os

def xml_file_to_json(input_file, output_file=None):
    """
    Read XML file and convert to pretty-printed JSON file
    """
    # Default output filename if not provided
    if output_file is None:
        base_name = os.path.splitext(input_file)[0]
        output_file = f"{base_name}.json"
    
    try:
        # Read XML file
        print(f"Reading XML from: {input_file}")
        with open(input_file, 'r', encoding='utf-8') as xml_file:
            xml_content = xml_file.read()
        
        # Parse XML to dictionary
        print("Parsing XML to dictionary...")
        data_dict = xmltodict.parse(xml_content)
        
        # Convert to formatted JSON
        json_str = json.dumps(data_dict, indent=2, ensure_ascii=False)
        
        # Write JSON file
        print(f"Writing JSON to: {output_file}")
        with open(output_file, 'w', encoding='utf-8') as json_file:
            json_file.write(json_str)
        
        print(f"✓ Successfully converted {input_file} → {output_file}")
        print("\nPreview (first 500 chars):")
        print(json_str[:500] + "..." if len(json_str) > 500 else json_str)
        
    except FileNotFoundError:
        print(f"Error: XML file '{input_file}' not found.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error processing XML: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    # Usage: python xml_to_json.py [input_file] [output_file]
    if len(sys.argv) < 2:
        input_file = "vulnerabilities.xml"
        print("No input file specified. Using 'vulnerabilities.xml'")
    else:
        input_file = sys.argv[1]
    
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    xml_file_to_json(input_file, output_file)