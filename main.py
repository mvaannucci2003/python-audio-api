import os
import csv
from config import CATEGORIES, OUTPUT_DIR
from gemini_client import init_chat, send_rules, send_query
from parser import extract_csv_text, parse_rows, validate

# CSV column headers for output files
OUTPUT_COLUMNS = ["category", "tag", "domain", "source", "environment", "scenario"]


def write_csv(rows, filepath):
    """Write validated rows to a CSV file."""
    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def run():
    """Main Function"""
    # Step 1: init and send rules
    client, chat = init_chat()
    send_rules(chat)

    # check if out directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Step 2: Iterate through categories
    for category, tags in CATEGORIES.items():
        print(f"\n- Generating: {category} -")

        # Send query to gemini
        raw = send_query(chat, category, tags)

        # Extract and parse
        csv_text = extract_csv_text(raw)
        rows = parse_rows(csv_text)

        is_valid = validate(rows, category, tags)

        if not is_valid:
            print(f" Skipping write for {category} - fix issues first")
            continue

        # Write to file - one CSV per category
        # Think about filename '/' breaks file paths
        safe_name = category.replace("/", "_").replace(" ", "_").lower()
        filepath = os.path.join(OUTPUT_DIR, f"{safe_name}.csv")

        write_csv(rows, filepath)
        print(f"  Saved to {filepath}")
        break  # placeholder for testing
    print("\n= Generation Complete =")


if __name__ == "__main__":
    run()
