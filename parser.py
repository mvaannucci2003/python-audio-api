import csv
import io
from config import DOMAINS, CATEGORIES

EXPECTED_COLUMNS = ["category", "tag", "domain", "source", "environment", "scenario"]


def extract_csv_text(raw_response):
    """Extracts just the CSV data from the API response

    Model might include:
    - Preamble text before the CSV
    - Markdown code fences
    - Trailing commentary after the CSV

    Strategy:
    - Stip code fences if present
    - Find lines that match CSV structure
    - include the header line if present
    """
    lines = raw_response.strip().split("\n")
    csv_lines = []

    for line in lines:
        stripped = line.strip()

        if not stripped or stripped.startswith("```"):
            continue

        if stripped.startswith("category,") or any(
            stripped.startswith(cat) for cat in CATEGORIES.keys()
        ):
            csv_lines.append(stripped)
    return "\n".join(csv_lines)


def parse_rows(csv_text):
    """Parse the CSV text into a list of dictionaries

    Uses python's csv module with io.StringsIO to read
    the string as if it were a file

    Returns a list of dicts
    [{'category': "...", "tag": "...", "domain": "...", ...}, ...]
    """
    reader = csv.DictReader(io.StringIO(csv_text))
    rows = []

    for row in reader:
        # normalizes domain capitalization to match the config
        if "domain" in row:
            row["domain"] = row["domain"].strip().title()
        # strips whitespace
        row = {key: value.strip() for key, value in row.items()}

        rows.append(row)

    return rows


def validate(rows, category, tags):
    """
    Check that the parsed output meets expectations.

    Checks:
    1. Expected row count
    2. Every domain is represented for each tag
    3. All rows have the correct category
    4. No duplicate scenarios

    Prints warnings for any issues found.
    Returns True if all checks pass, False otherwise
    """
    expected_count = len(tags) * len(DOMAINS)
    is_valid = True

    if len(rows) != expected_count:
        print(f" Warning: Expected {expected_count} rows, got {len(rows)}")
        is_valid = False

    for tag in tags:
        tag_rows = [r for r in rows if r.get("tag") == tag]
        tag_domains = {r.get("domain") for r in tag_rows}
        missing = set(DOMAINS) - tag_domains

        if missing:
            print(f" Warning: Tag '{tag}' missing domains: {missing}")
            is_valid = False

    for row in rows:
        if row.get("category") != category:
            print(f" Warning: Unexpected category '{row.get("category")}' in row")
            is_valid = False

    scenarios = [r.get("scenario") for r in rows]
    if len(scenarios) != len(set(scenarios)):
        print(" Warning: Duplicate scenarios detected")
        is_valid = False

    if is_valid:
        print(f" Valid: {len(rows)} rows, all checks passed")

    return is_valid


if __name__ == "__main__":
    test_raw = """category,tag,domain,source,environment,scenario
Brightness/Spectral,bright,musical,struck brass cymbal,windy clifftop,a heavy mallet striking a large brass cymbal on a windy clifftop
Brightness/Spectral,bright,mechanical,metal gears grinding,busy industrial shipyard,two interlocking steel gears grinding against each other in a busy industrial shipyard
Brightness/Spectral,bright,environmental,hailstone hitting metal,open desert,a single large hailstone hitting a corrugated metal roof in the open desert
Brightness/Spectral,bright,organic,crisp dry leaves crushing,dense autumn forest,a heavy boot stepping down on a pile of crisp dry leaves in a dense autumn forest
Brightness/Spectral,bright,domestic,glass breaking,busy metro station,a tempered glass bottle shattering on the concrete floor of a busy metro station
Brightness/Spectral,bright,electronic,short circuit spark,damp underground cave,a live electrical wire sparking against a damp cave wall
Brightness/Spectral,dark,musical,cello bow stroke,quiet pine forest,a heavy horsehair bow dragging slowly across the thickest cello string in a quiet pine forest
Brightness/Spectral,dark,mechanical,thick oil hydraulic press,abandoned basement,a massive hydraulic press compressing thick rubber seals in an abandoned basement
Brightness/Spectral,dark,environmental,deep mud shifting,riverbank,heavy wet earth sliding down a saturated riverbank during a rainstorm
Brightness/Spectral,dark,organic,large animal breathing,remote mountain peak,a large mammal exhaling through its nostrils on a cold remote mountain peak
Brightness/Spectral,dark,domestic,heavy woolen rug dragging,empty warehouse,a thick industrial woolen rug being dragged across an empty warehouse floor
Brightness/Spectral,dark,electronic,power transformer hum,narrow alleyway,a large electrical transformer vibrating inside a concrete box in a narrow alleyway"""

    # Step 1: Extract CSV from raw response
    csv_text = extract_csv_text(test_raw)
    print(" Extracted CSV ")
    print(csv_text)
    print()

    # Step 2: Parse into row dictionaries
    rows = parse_rows(csv_text)
    print(" Parsed Rows ")
    for row in rows:
        print(row)
    print()

    # Step 3: Validate against expected structure
    print(" Validation ")
    validate(rows, "Brightness/Spectral", ["bright", "dark"])
