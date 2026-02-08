import os
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs.play import play

load_dotenv()

key = os.environ.get("ELEVEN_API_KEY")

client = ElevenLabs(api_key=key)


def generate_sound_effect(prompt, filename):
    print(f"Working: {prompt}")

    audio = client.text_to_sound_effects.convert(
        text=prompt, duration_seconds=2, prompt_influence=0.75
    )

    with open(filename, "wb") as f:
        for chunk in audio:
            if chunk:
                f.write(chunk)
    print(f"Saved to {filename}")


if __name__ == "__main__":
    sound_to_make = [
        (
            "The idle rumble of a vintage car engine in a closed garage, with a warm quality",
            "warm_timbre.mp3",
        )
    ]

    for text, fname in sound_to_make:
        generate_sound_effect(text, fname)
