"""Run the scenarios: a simulated guest calls, the waiter agent answers.

Writes one transcript per scenario to scenes/<id>.json, with every tool call
the waiter made. Uses the Claude API (a few cents per scenario), so it only
runs with --confirm.

    python scripts/simulate.py                         # dry run: what would run
    python scripts/simulate.py --confirm               # all scenarios
    python scripts/simulate.py --confirm --only dessert
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import anthropic  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

from agent.guest import HANG_UP, Guest  # noqa: E402
from agent.waiter import Waiter  # noqa: E402

MAX_TURNS = 6  # guest turns; keeps each call under a minute of audio


def run(client, scenario: dict) -> dict:
    waiter = Waiter(client)
    guest = Guest(client, scenario["persona"], scenario["goal"], max_turns=MAX_TURNS - 1)
    turns = [{"speaker": "sound", "text": "phone ringing"}]

    waiter_line, trace = waiter.reply("(The phone rings. You pick up.)")
    turns.append({"speaker": "waiter", "text": waiter_line, "tools": trace})
    for _ in range(MAX_TURNS):
        guest_line = guest.reply(waiter_line)
        done = HANG_UP in guest_line
        guest_line = guest_line.replace(HANG_UP, "").strip()
        if guest_line:
            turns.append({"speaker": "guest", "text": guest_line})
        if done:
            break
        waiter_line, trace = waiter.reply(guest_line)
        turns.append({"speaker": "waiter", "text": waiter_line, "tools": trace})
    return {**scenario, "turns": turns, "order": waiter.menu.get_order()}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm", action="store_true", help="call the Claude API")
    parser.add_argument("--only", help="run a single scenario id")
    args = parser.parse_args()

    scenarios = json.loads((ROOT / "data" / "scenarios.json").read_text())
    if args.only:
        scenarios = [s for s in scenarios if s["id"] == args.only]
    print("Scenarios:", ", ".join(s["id"] for s in scenarios))
    if not args.confirm:
        print("Dry run: nothing sent. Add --confirm to run them (a few cents each).")
        return 0

    load_dotenv(ROOT / ".env")
    client = anthropic.Anthropic()
    out = ROOT / "scenes"
    out.mkdir(exist_ok=True)
    for scenario in scenarios:
        scene = run(client, scenario)
        path = out / f"{scenario['id']}.json"
        path.write_text(json.dumps(scene, indent=2, ensure_ascii=False) + "\n")
        print(f"\n== {scenario['title']} -> {path.relative_to(ROOT)}")
        for t in scene["turns"]:
            print(f"  {t['speaker']:>6}: {t['text']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
