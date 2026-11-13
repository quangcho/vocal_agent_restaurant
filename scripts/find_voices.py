"""Browse the ElevenLabs Voice Library. Free: no audio is generated.

Each result has a preview link you can open in a browser to listen.

    python scripts/find_voices.py --accent italian
    python scripts/find_voices.py --accent italian --gender male --search waiter
"""

import argparse
import os
import sys

from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--accent", help="e.g. italian, american, british")
    parser.add_argument("--gender", help="male or female")
    parser.add_argument("--search", help="free text, e.g. warm, friendly")
    parser.add_argument("--language", default="en")
    parser.add_argument("--limit", type=int, default=15)
    args = parser.parse_args()

    load_dotenv()
    client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
    voices = client.voices.get_shared(
        page_size=args.limit, accent=args.accent, gender=args.gender,
        search=args.search, language=args.language,
    ).voices
    for v in voices:
        print(f"{v.name}  ({v.gender}, {v.age}, {v.accent})")
        print(f"   voice_id={v.voice_id}")
        if v.description:
            print(f"   {v.description[:110]}")
        print(f"   listen: {v.preview_url}\n")
    if not voices:
        print("No voice found. Try fewer filters.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
