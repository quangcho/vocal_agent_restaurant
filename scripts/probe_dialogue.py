"""Check whether ElevenLabs Text to Dialogue accepts an Eleven v4 model.

Free by default: it only lists models and voices. The paid call (about 100
characters, well under one cent) runs only with --confirm.

    python scripts/probe_dialogue.py                 # free: models + voices
    python scripts/probe_dialogue.py --confirm       # one tiny dialogue
    python scripts/probe_dialogue.py --confirm --model eleven_v4
"""

import argparse
import base64
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs.core.api_error import ApiError


WAITER_LINE = "Gino Pizza, good evening! What can I get you?"
GUEST_LINE = "[curious] Hi! Do you have anything vegetarian?"

# Voices picked from the first probe: Bella (waiter) and Roger (guest).
WAITER_VOICE = "hpp4J3VqNfWAUOO0d1Us"  # Bella - Professional, Bright, Warm
GUEST_VOICE = "CwhRBWXzGAHq8TQ4Fs17"   # Roger - Laid-Back, Casual, Resonant


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="eleven_v4_turbo")
    parser.add_argument("--waiter-voice", default=WAITER_VOICE, help="voice_id for the waiter (default: Bella)")
    parser.add_argument("--guest-voice", default=GUEST_VOICE, help="voice_id for the guest (default: Roger)")
    parser.add_argument("--waiter-tag", default="[warm, light Italian accent]",
                        help='audio tag before the waiter line, e.g. "[warm, light Italian accent]"')
    parser.add_argument("--confirm", action="store_true", help="spend credits on one tiny request")
    args = parser.parse_args()

    load_dotenv()
    key = os.getenv("ELEVENLABS_API_KEY")
    if not key:
        print("ELEVENLABS_API_KEY is missing: copy .env.example to .env and fill it in.")
        return 1
    client = ElevenLabs(api_key=key)

    print("Models on this account (free call):")
    for m in client.models.list():
        if "v4" in m.model_id or "v3" in m.model_id:
            print(f"  {m.model_id:<22} tts={m.can_do_text_to_speech} alpha={m.requires_alpha_access}")

    voices = client.voices.search(category="premade", page_size=10).voices
    print("\nPremade voices (free call):")
    for v in voices:
        print(f"  {v.voice_id}  {v.name}")
    inputs = [
        {"text": f"{args.waiter_tag} {WAITER_LINE}".strip(),
         "voice_id": args.waiter_voice},
        {"text": GUEST_LINE, "voice_id": args.guest_voice},
    ]
    chars = sum(len(i["text"]) for i in inputs)
    print(f"\nPlanned request: model={args.model}, {chars} characters.")
    for i in inputs:
        print(f"  {i['voice_id']}: {i['text']}")

    if not args.confirm:
        print("Dry run: nothing generated. Add --confirm to send the request.")
        return 0

    try:
        result = client.text_to_dialogue.convert_with_timestamps(
            inputs=inputs, model_id=args.model, language_code="en"
        )
    except ApiError as err:
        print(f"\nREJECTED ({err.status_code}): {err.body}")
        return 2

    out = Path("out")
    out.mkdir(exist_ok=True)

    audio = out / f"probe_{args.model}.mp3"
    audio.write_bytes(base64.b64decode(result.audio_base_64))
    segments = [s.model_dump() for s in result.voice_segments]
    (out / f"probe_{args.model}.json").write_text(json.dumps(segments, indent=2))
    print(f"\nACCEPTED: {audio} written, {len(segments)} voice segments:")
    for s in segments:
        print(f"  input {s['dialogue_input_index']}: {s['start_time_seconds']:.2f}s -> {s['end_time_seconds']:.2f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
