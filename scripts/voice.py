"""Turn each directed scene into audio with ElevenLabs Text to Dialogue.

One request per scene, with timestamps so the website can highlight each line
while it plays. Files go to audio/ and are meant to be committed: generate
once, never again. A scene whose text, voices and model have not changed is
skipped (cache key stored next to the audio).

    python scripts/voice.py              # dry run: characters and cost
    python scripts/voice.py --confirm    # generate
"""

import argparse
import base64
import hashlib
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs

ROOT = Path(__file__).resolve().parent.parent
AUDIO = ROOT / "audio"
VOICES = json.loads((ROOT / "data" / "voices.json").read_text())
PRICE_PER_1K = {"eleven_v4_turbo": 0.04, "eleven_v4": 0.08}
MAX_CHARS = 2000  # Text to Dialogue limit per request

RING_PROMPT = "A classic landline telephone ringing twice, clean recording, no background"
RING_SECONDS = 3.0


def build_inputs(scene: dict) -> tuple[list[dict], list[int]]:
    """Dialogue inputs, and for each input the index of its turn in the scene."""
    guest_voice = VOICES["guests"][scene["id"]]["voice_id"]
    inputs, turn_index = [], []
    for i, turn in enumerate(scene["turns"]):
        if turn["speaker"] not in ("waiter", "guest"):
            continue
        voice = VOICES["waiter"]["voice_id"] if turn["speaker"] == "waiter" else guest_voice
        inputs.append({"text": turn.get("performance", turn["text"]), "voice_id": voice})
        turn_index.append(i)
    return inputs, turn_index


def cache_key(inputs: list[dict]) -> str:
    blob = json.dumps({"inputs": inputs, "model": VOICES["model_id"]}, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm", action="store_true", help="spend ElevenLabs credits")
    parser.add_argument("--only", help="a single scene id")
    args = parser.parse_args()

    scenes = [json.loads(p.read_text()) for p in sorted((ROOT / "scenes").glob("*.json"))]
    if args.only:
        scenes = [s for s in scenes if s["id"] == args.only]

    jobs = []
    for scene in scenes:
        inputs, turn_index = build_inputs(scene)
        chars = sum(len(i["text"]) for i in inputs)
        if chars > MAX_CHARS:
            print(f"{scene['id']}: {chars} characters, over the {MAX_CHARS} limit. Shorten it.")
            return 1
        key = cache_key(inputs)
        meta = AUDIO / f"{scene['id']}.json"
        cached = meta.exists() and json.loads(meta.read_text()).get("cache_key") == key
        if not all("performance" in scene["turns"][i] for i in turn_index):
            print(f"{scene['id']}: no audio tags yet, run scripts/direct.py first.")
            return 1
        jobs.append((scene, inputs, turn_index, key, chars, cached))

    todo = [j for j in jobs if not j[5]]
    total = sum(j[4] for j in todo)
    price = PRICE_PER_1K.get(VOICES["model_id"], 0.08)
    for scene, *_, chars, cached in jobs:
        print(f"  {scene['id']:<12} {chars:>5} chars  {'cached, skipped' if cached else 'to generate'}")
    ring_needed = not (AUDIO / "ring.mp3").exists()
    print(f"Model {VOICES['model_id']}: {total} characters, about ${total / 1000 * price:.2f}"
          + (" + one phone ring sound effect" if ring_needed else ""))
    if not args.confirm:
        print("Dry run: nothing generated. Add --confirm.")
        return 0

    load_dotenv(ROOT / ".env")
    client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
    AUDIO.mkdir(exist_ok=True)

    if ring_needed:
        ring = client.text_to_sound_effects.convert(
            text=RING_PROMPT, duration_seconds=RING_SECONDS, output_format="mp3_44100_128")
        (AUDIO / "ring.mp3").write_bytes(b"".join(ring))
        print("  ring.mp3 written")

    for scene, inputs, turn_index, key, chars, _ in todo:
        result = client.text_to_dialogue.convert_with_timestamps(
            inputs=inputs, model_id=VOICES["model_id"],
            language_code=VOICES["language_code"], output_format="mp3_44100_128")
        (AUDIO / f"{scene['id']}.mp3").write_bytes(base64.b64decode(result.audio_base_64))
        lines = [
            {"turn": turn_index[s.dialogue_input_index],
             "speaker": scene["turns"][turn_index[s.dialogue_input_index]]["speaker"],
             "start": round(s.start_time_seconds, 3), "end": round(s.end_time_seconds, 3)}
            for s in result.voice_segments
        ]
        meta = {"scene": scene["id"], "model": VOICES["model_id"], "cache_key": key,
                "ring": "ring.mp3", "audio": f"{scene['id']}.mp3", "lines": lines}
        (AUDIO / f"{scene['id']}.json").write_text(json.dumps(meta, indent=2) + "\n")
        end = lines[-1]["end"] if lines else 0
        print(f"  {scene['id']}.mp3 written, {end:.1f} s, {len(lines)} lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
