MODEL_NAME = "gemini-3-flash-preview"
OUTPUT_DIR = "output/scenarios"
SCENARIOS_PER_TAG_PER_DOMAIN = 18
# Environmential Definitions
DOMAINS = [
    "Musical",
    "Mechanical",
    "Environmental",
    "Organic",
    "Domestic",
    "Electronic",
]
# Category/Tag Mapping
CATEGORIES = {
    "Brightness/Spectral": ["bright", "dark", "brilliant", "dull"],
    "Warmth/Body": ["warm", "cold", "full", "thin", "rich", "woody"],
    "Attack/Transient": ["punchy", "snappy", "thumping", "smacking", "percussive"],
    "Density/Complexity": ["sparse", "thick", "saturated", "cluttered"],
    "Space/Dimension": ["wide", "narrow", "deep", "shallow", "distant", "present"],
    "Energy/Dynamics": [
        "powerful",
        "aggressive",
        "intense",
        "explosive",
        "energetic",
        "compressed",
        "surging",
        "pulsing",
    ],
    "Clarity/Definition": [
        "clear",
        "muddy",
        "focused",
        "transparent",
        "intelligible",
        "distinct",
    ],
    "Pitch/Register": [
        "tinny",
        "hissing",
        "thunderous",
        "treble-heavy",
        "bassy",
        "rumbling",
    ],
    "Modulation/Movement": [
        "vibrating",
        "wobbling",
        "shimmering",
        "fluttering",
        "morphing",
    ],
    "Emotional/Subjective": [
        "haunting",
        "natural",
        "artificial",
        "organic",
        "synthetic",
        "robotic",
        "retro",
        "lo-fi",
        "hi-fi",
    ],
    "Material/Source": [
        "metallic",
        "wooden",
        "plastic",
        "rubbery",
        "crystalline",
        "icy",
        "watery",
        "earthy",
    ],
    "Processing": [
        "distorted",
        "overdriven",
        "filtered",
        "effected",
        "chorused",
        "quantized",
    ],
}

# Rule Prompt step 1
RULES_PROMPT = f"""
You are a scenario generator for a text-to-audio research project. Your job is to generate concise physical scenarios that will be inserted into a fixed prompt template. You do NOT generate the full prompt — only the scenario data.
The prompt template (for your reference only — do not output this): "A sound effect of [scenario]. With a '[tag]' quality."
Output format: CSV with columns: category, tag, domain, source, environment, scenario
Scenario formatting: The scenario field must be a lowercase noun phrase that reads grammatically after "A sound effect of." Example: "a ceramic plate shattering on a marble floor in a quiet library" No capitalization, no trailing period, no tag references.
Rules for scenario generation:
1.	The scenario must describe a PHYSICAL EVENT that causally produces or explains the timbral quality — not a poetic location or atmospheric backdrop.
2.	Each scenario's sound-producing source MUST belong to the specified domain:
o	Musical: instruments, tonal bodies, resonant objects designed for sound production
o	Mechanical: machines, engines, gears, tools, industrial equipment
o	Environmental: weather, water, wind, geological phenomena, fire
o	Organic: animal vocalizations, human body sounds, wood/plant material interactions
o	Domestic: kitchen objects, household items, furniture, appliances
o	Electronic: circuits, speakers, electrical discharge, buzzing, feedback
3.	The domain constrains the SOUND SOURCE only — environments should still be highly diverse and independent of the domain. No clustering around studios, rooms, or halls. Use forests, busy streets, meadows, industrial sites, underwater, rooftops, farmland, deserts, caves, kitchens, shipyards, etc.
4.	The scenario must NEVER explicitly describe sonic or spectral characteristics (e.g., "low-frequency," "high-pitched," "choked click," "rapid overlapping sine waves"). The physical event should naturally and causally produce the timbral quality, but the TAG is the ONLY element that names the timbral characteristic.
5.	The scenario's physical event must be TEMPORALLY COMPATIBLE with the timbral descriptor. Descriptor implying sharp transients (e.g., "brilliant," "crisp," "punchy," "sharp") require fast-onset events such as impacts, cracks, strikes, or snaps — not gradual processes like ignition, heating, or flowing. Descriptors implying sustained or evolving qualities (e.g., "shimmering," "warm," "rich") may use sustained or transient events but must involve physical processes that allow the quality to be perceivable over time.
6.	Generate exactly {SCENARIOS_PER_TAG_PER_DOMAIN} scenario per tag per domain ({SCENARIOS_PER_TAG_PER_DOMAIN * 6} rows per tag).
7.	Scenario uniqueness is mandatory across the ENTIRE output, including across different tags within the same category.
Tags within a category often share semantic space.
This makes cross-tag scenario collisions likely. Before generating a scenario for any tag, verify that the same event has not already been used for a different tag in the same category.
If two tags could plausibly share the same scenario, they MUST use distinct events. No two rows in the output may have identical or near-identical scenario text, regardless of whether they differ in tag, domain, or any other column.
Confirm you understand these rules, then wait for generation queries.
"""

# Query Template step 2
QUERY_TEMPLATE = "Generate scenarios for:\nCategory: {category}\nTags: {tags}"

# Audio Prompt Template (for Audio LLM)
AUDIO_PROMPT_TEMPLATE = "A sound effect of {scenario}. With a '{tag}' quality."
