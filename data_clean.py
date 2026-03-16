import os
import csv
from parser import EXPECTED_COLUMNS


def find_batch_files(category, scenarios_dir):
    """
    Scan the scenario directory and return a list of full file paths
    for all batch CSVs belonging to the given category.

    Excludes the master CSV that does not contain a 'batch' name
    """
    batch_files = []

    for filename in os.listdir(scenarios_dir):
        if (
            filename.startswith(category)
            and filename.endswith(".csv")
            and "batch" in filename
        ):
            full_path = os.path.join(scenarios_dir, filename)
            batch_files.append(full_path)

    return batch_files


def load_and_merge(category, scenarios_dir):
    """
    Load existing master (if it exists) and all batch files
    for the given category. Returns one combined list of row dicts"""
    all_rows = []
    master_path = os.path.join(scenarios_dir, f"{category}.csv")

    # Load master first
    if os.path.exists(master_path):
        with open(master_path, "r") as f:
            reader = csv.DictReader(f)
            master_rows = list(reader)
            print(f"Loaded {len(master_rows)} rows from master")
            all_rows.extend(master_rows)

    # Load batch files
    batch_files = find_batch_files(category, scenarios_dir)

    for filepath in batch_files:
        with open(filepath, "r") as f:
            reader = csv.DictReader(f)
            batch_rows = list(reader)
            print(f"Loaded {len(batch_rows)} rows from {os.path.basename(filepath)}")
            all_rows.extend(batch_rows)

    print(f"Total rows before deduplication: {len(all_rows)}")
    return all_rows


def deduplicate(rows):
    """
    Removes duplicate scenarios, keeping the first occurence.
    Returns the cleaned master file.
    """
    seen = set()
    cleaned = []

    for row in rows:
        scenario = row.get("scenario")
        if scenario not in seen:
            seen.add(scenario)
            cleaned.append(row)

    removed = len(rows) - len(cleaned)
    print(f"Removed {removed} duplicates, {len(cleaned)} unique rows remaining")
    return cleaned
