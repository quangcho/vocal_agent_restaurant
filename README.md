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

## Data

`data/menu.json` is a faithful transcription of `data/menu.pdf`.
