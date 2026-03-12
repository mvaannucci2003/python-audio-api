import os
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from config import AUDIO_PROMPT_TEMPLATE

load_dotenv()


def init_elevenlabs():
    """Creates and returns the ElevenLabs client"""
    api_key = os.environ.get("ELEVENLABS_API_KEY")

    if not api_key:
        raise ValueError("ELEVENLABS_API_KEY environment variable is not set")

    client = ElevenLabs(api_key=api_key)
    return client


def generate_sound_effect(client, scenario, tag, output_path):
    """
    Generate a sound effect from a scenario and tag.

    Assembles the promt using AUDIO_PROMPT_TEMPLATE,
    sneds to 11Labs, writes the audio file.
    """
    prompt = AUDIO_PROMPT_TEMPLATE.format(scenario=scenario, tag=tag)

    print(f" Prompt: {prompt}")

    result = client.text_to_sound_effects.convert(
        text=prompt,
        duration_seconds=2,
        prompt_influence=0.7,
    )

    audio_bytes = b"".join(result)

    with open(output_path, "wb") as f:
        f.write(audio_bytes)

    print(f" Saved to {output_path}")


def generate_batch(client, csv_filepath, audio_output_dir):
    """
    Reads a scenario CSV and generates audio for every row.
    - Read each row form the CSV
    - Call generate_sound_effect for each row
    - Add a small delay between API calls to avoid rate limits
    """
    import csv
    import time

    os.makedirs(audio_output_dir, exist_ok=True)

    with open(csv_filepath, "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"Generating {len(rows)} sound effects..")

    for i, row in enumerate(rows):
        # Build filename from row data
        safe_tag = row["tag"].replace(" ", "_")
        safe_domain = row["domain"].replace(" ", "_").lower()
        filename = f"{safe_tag}_{safe_domain}.mp3"
        output_path = os.path.join(audio_output_dir, filename)

        print(f"\n[{i+1}/{len(rows)}]")
        generate_sound_effect(client, row["scenario"], row["tag"], output_path)

        # pause between requests to make sure rate limit errors don't occur
        time.sleep(2)

        if (
            i >= 2
        ):  # placeholder to make sure we don't use all the free credits available
            break
    print(f"\nBatch complete: {len(rows)} files generated")


if __name__ == "__main__":
    import csv

    client = init_elevenlabs()
    generate_batch(
        client,
        "output/scenarios/brightness_spectral.csv",
        "output/audio/brightness_spectral",
    )

    # Read one row from generated CSV
    with open("output/scenarios/brightness_spectral.csv", "r") as f:
        reader = csv.DictReader(f)
        row = next(reader)

    # Generate audio for that single row
    os.makedirs("output/audio", exist_ok=True)
    output_path = f"output/audio/test_{row['tag']}_{row['domain']}.mp3"

    generate_sound_effect(client, row["scenario"], row["tag"], output_path)
