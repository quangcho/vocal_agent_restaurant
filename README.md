# Vocal agent restaurant

A Python agent that answers the customers of a pizzeria from its real menu, and a
pipeline that turns a simulated conversation into expressive audio with ElevenLabs
Eleven v4. Work in progress.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then put your ElevenLabs and Anthropic keys in .env
```

## Step 1: check Eleven v4 with Text to Dialogue

```bash
python scripts/probe_dialogue.py            # free: lists models and voices
python scripts/probe_dialogue.py --confirm  # one ~100-character request (< $0.01)
```

The audio lands in `out/` (ignored by git).

## Step 2: simulate the calls (text only)

```bash
pytest -q                               # offline tests, free
python scripts/simulate.py              # dry run
python scripts/simulate.py --confirm    # 3 calls with Claude, a few cents each
```

Each call lands in `scenes/<id>.json`: the transcript plus every tool the waiter used.
Read it before any audio is generated.

## How it works

- `agent/menu.py`: the menu and the waiter's tools. Plain Python: prices, ingredients
  and totals always come from here, never from the model.
- `agent/waiter.py`: Claude answering the phone, calling the tools in a short loop.
- `agent/guest.py`: Claude playing a caller who only hears what the waiter says.
- `data/scenarios.json`: the three callers and what they want.

## Data

`data/menu.json` is a faithful transcription of `data/menu.pdf`.
