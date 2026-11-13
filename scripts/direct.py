"""Direction pass: Claude picks one Eleven v4 audio tag per line.

The words are never touched: Claude only returns a tag per line, and the code
puts it in front of the original text. The result is saved in each scene as
"performance". Read it before generating audio.

    python scripts/direct.py              # dry run
    python scripts/direct.py --confirm    # a fraction of a cent per scene
"""

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import anthropic  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

from agent.llm import create, text_of  # noqa: E402

ACCENT = json.loads((ROOT / "data" / "voices.json").read_text())["waiter"]["tag"]

PROMPT = """You are directing voice actors for a short phone call at a pizzeria.
For each numbered line, choose ONE audio tag for Eleven v4 that fits the emotion.

Rules:
- A tag is short, in square brackets, describing delivery: e.g. [cheerful], [curious],
  [warmly], [relieved], [excited], [playfully], [hesitant], [laughs softly], [sighs].
- Every WAITER tag must also contain "light Italian accent", e.g. [cheerful, light Italian accent].
- No sound effects, no music. Vary the tags; follow the arc of the call.
- Return only a JSON array of strings, one tag per line, in order. Nothing else.

{lines}"""


def direct(client, scene: dict) -> list[str]:
    spoken = [t for t in scene["turns"] if t["speaker"] in ("waiter", "guest")]
    lines = "\n".join(f"{i}. {t['speaker'].upper()}: {t['text']}" for i, t in enumerate(spoken))
    response = create(client, effort="low",
                      messages=[{"role": "user", "content": PROMPT.format(lines=lines)}])
    raw = text_of(response)
    tags = json.loads(raw[raw.find("["): raw.rfind("]") + 1])
    if len(tags) != len(spoken):
        raise ValueError(f"{scene['id']}: got {len(tags)} tags for {len(spoken)} lines")
    clean = []
    for turn, tag in zip(spoken, tags):
        tag = "[" + re.sub(r"[\[\]]", "", str(tag)).strip() + "]"
        if turn["speaker"] == "waiter" and "italian" not in tag.lower():
            tag = ACCENT
        clean.append(tag)
    return clean


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm", action="store_true", help="call the Claude API")
    parser.add_argument("--only", help="a single scene id")
    args = parser.parse_args()

    paths = sorted((ROOT / "scenes").glob("*.json"))
    if args.only:
        paths = [p for p in paths if p.stem == args.only]
    print("Scenes:", ", ".join(p.stem for p in paths))
    if not args.confirm:
        print("Dry run: nothing sent. Add --confirm.")
        return 0

    load_dotenv(ROOT / ".env")
    client = anthropic.Anthropic()
    for path in paths:
        scene = json.loads(path.read_text())
        tags = iter(direct(client, scene))
        print(f"\n== {scene['id']}")
        for turn in scene["turns"]:
            if turn["speaker"] in ("waiter", "guest"):
                turn["performance"] = f"{next(tags)} {turn['text']}"
                print(f"  {turn['speaker']:>6}: {turn['performance']}")
        path.write_text(json.dumps(scene, indent=2, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
