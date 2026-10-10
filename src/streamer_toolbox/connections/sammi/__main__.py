"""Write a SAMMI deck with one button per toolbox action, taken from a running toolbox's GET /actions.

python -m streamer_toolbox.sammi [--url http://127.0.0.1:8850] [--out build/sammi_toolbox_deck.json]

Only writes the file. Importing it (SAMMI: Paste Deck) is done by hand, by crazyDrage.
"""
import argparse
import json
from pathlib import Path

import httpx

from streamer_toolbox.connections.sammi.sammi_deck_builder import SammiDeckBuilder

REPO_ROOT = Path(__file__).resolve().parents[4]


def main() -> None:
    parser = argparse.ArgumentParser(prog="streamer_toolbox.connections.sammi")
    parser.add_argument("--url", default="http://127.0.0.1:8850", help="where the toolbox runs (and SAMMI calls)")
    parser.add_argument("--token", default=None, help="caller token, if this PC has no local caller")
    parser.add_argument("--deck-name", default="toolbox")
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "build" / "sammi_toolbox_deck.json")
    args = parser.parse_args()

    headers = {"Authorization": f"Bearer {args.token}"} if args.token else {}
    response = httpx.get(f"{args.url.rstrip('/')}/actions", headers=headers, timeout=10)
    response.raise_for_status()
    actions = response.json()
    deck = SammiDeckBuilder(args.url, args.deck_name).build(actions)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(deck, indent=1), encoding="utf-8")
    print(f"{len(actions)} buttons -> {args.out}")


if __name__ == "__main__":
    main()
