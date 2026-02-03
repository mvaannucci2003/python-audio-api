from elevenlabs.client import ElevenLabs
from elevenlabs.play import play

client = ElevenLabs(api_key="")

audio = client.text_to_sound_effects.convert(
    text="a sound effect of audio played through a metal enclosure. With a 'tinny timbre'"
)

play(audio)
