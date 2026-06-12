import os
import csv
import time
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

    Assembles the prompt using AUDIO_PROMPT_TEMPLATE,
    sends to 11Labs, writes the audio file.
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


def _next_offset(audio_tag_dir):
    """
    Return the next available 4-digit index for a tag's audio directory.

    Scans existing .mp3 files, pulls the trailing index off each filename,
    and returns highest + 1. The .isdigit() guard skips any legacy files that
    don't follow the _NNNN naming so they don't crash the int() parse.
    Returns 0 for a fresh/empty directory.
    """
    if not os.path.isdir(audio_tag_dir):
        return 0

    existing = [f for f in os.listdir(audio_tag_dir) if f.endswith(".mp3")]
    offset = 0
    found = False

    for f in existing:
        name = f.replace(".mp3", "")
        last = name.split("_")[-1]
        if not last.isdigit():
            continue
        num = int(last)
        found = True
        if num > offset:
            offset = num

    return offset + 1 if found else 0


def _open_manifest(manifest_path, manifest_fields):
    """
    Open the manifest in append mode. Writes the header only if the file is
    new or empty, so re-runs append to the existing manifest instead of
    clobbering prior batches. Returns (file_handle, DictWriter).
    """
    os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
    needs_header = (
        not os.path.exists(manifest_path) or os.path.getsize(manifest_path) == 0
    )
    f = open(manifest_path, "a", newline="")
    writer = csv.DictWriter(f, fieldnames=manifest_fields)
    if needs_header:
        writer.writeheader()
    return f, writer


def _manifest_row(row, relative_audio_path):
    """
    Build a lowercased manifest row: every input field lowercased, plus the
    appended `file` column holding the audio path relative to audio_output_dir.
    """
    out = {k: (v.lower() if isinstance(v, str) else v) for k, v in row.items()}
    out["file"] = relative_audio_path.lower()
    return out


def generate_batch(
    client, csv_filepath, audio_output_dir, manifest_path, max_files=None
):
    """
    Read a scenario CSV, generate audio for every row, and append a manifest
    row per generated file.

    Audio is nested per tag:
        <audio_output_dir>/<tag>/<tag>_<domain>_<idx>.mp3
    The index is a per-TAG counter that runs continuously across domains
    (musical 0000-0016, mechanical 0017-0033, ...). The manifest mirrors the
    input CSV columns and appends `file` (path relative to audio_output_dir),
    all lowercased, flushed per row, written only after a successful save.
    """
    os.makedirs(audio_output_dir, exist_ok=True)

    with open(csv_filepath, "r") as f:
        reader = csv.DictReader(f)
        input_fields = reader.fieldnames
        rows = list(reader)

    manifest_fields = input_fields + ["file"]
    print(f"Generating {len(rows)} sound effects..")

    manifest_file, manifest_writer = _open_manifest(manifest_path, manifest_fields)

    try:
        tag_offsets = {}

        for i, row in enumerate(rows):
            if max_files is not None and i >= max_files:
                break

            safe_tag = row["tag"].replace(" ", "_").lower()
            safe_domain = row["domain"].replace(" ", "_").lower()

            tag_dir = os.path.join(audio_output_dir, safe_tag)
            os.makedirs(tag_dir, exist_ok=True)

            # Seed each tag's counter once from whatever already exists on disk,
            # so a re-run resumes instead of overwriting.
            if safe_tag not in tag_offsets:
                tag_offsets[safe_tag] = _next_offset(tag_dir)

            idx = tag_offsets[safe_tag]
            filename = f"{safe_tag}_{safe_domain}_{idx:04d}.mp3"
            output_path = os.path.join(tag_dir, filename)
            relative_path = os.path.join(safe_tag, filename)

            print(f"\n[{i+1}/{len(rows)}]")
            generate_sound_effect(client, row["scenario"], row["tag"], output_path)

            # Manifest row only AFTER the audio file is successfully written.
            manifest_writer.writerow(_manifest_row(row, relative_path))
            manifest_file.flush()

            tag_offsets[safe_tag] += 1
            time.sleep(2)

    finally:
        manifest_file.close()

    print(f"\nBatch complete. Manifest: {manifest_path}")


if __name__ == "__main__":
    # Write paths follow the April convention:
    #   scenarios -> output/scenarios/<category>.csv   (deduped master)
    #   audio     -> output/audio/<category>/<tag>/...
    #   manifest  -> output/manifests/<category>.csv
    client = init_elevenlabs()
    generate_batch(
        client,
        csv_filepath="output/scenarios/valence_artificial.csv",
        audio_output_dir="output/audio/valence_artificial",
        manifest_path="output/manifests/valence_artificial.csv",
        max_files=100,
    )
