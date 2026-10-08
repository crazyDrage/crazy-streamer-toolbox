import unittest

from streamer_toolbox.connections.sammi.sammi_deck_list import SammiDeckList

DECKS = [  # the shape SAMMI's getDeckList answers with (cut down)
    {"deckId": "2025", "deckName": "stream", "status": 1.0, "crc": 1.0,
     "buttons": [{"id": "ID24", "text": "twitch_marker"}, {"id": "hammer_bonk", "text": "hammer\n bonk"},
                 {"id": "ID25", "text": ""}]},
    {"deckId": "2026", "deckName": "sounds", "status": 0.0, "crc": 2.0, "buttons": [{"id": "ID38", "text": "<-"}]},
]


class TestSammiDeckList(unittest.IsolatedAsyncioTestCase):
    async def test_choices_and_summary_from_one_read_then_fresh_after_a_while(self) -> None:
        now, reads = [0.0], []

        async def fetch():
            reads.append(now[0])
            return DECKS

        decks = SammiDeckList(fetch, keep_seconds=5, clock=lambda: now[0])
        self.assertEqual(await decks.button_groups(), {
            "stream": {"ID24": "twitch_marker  [ID24]", "hammer_bonk": "hammer bonk  [hammer_bonk]",
                       "ID25": "(no text)  [ID25]"},
            "sounds": {"ID38": "<-  [ID38]"}})
        self.assertEqual(await decks.deck_choices(), {"2025": "stream", "2026": "sounds"})
        self.assertEqual((await decks.summary())[1], {"name": "sounds", "id": "2026", "enabled": False,
                                                       "buttons": [{"id": "ID38", "text": "<-"}]})
        self.assertEqual(len(reads), 1)
        now[0] = 6
        await decks.button_groups()
        self.assertEqual(len(reads), 2)  # a button made in SAMMI meanwhile shows up
