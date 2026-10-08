import unittest

from streamer_toolbox.connections.twitch.twitch_reward import TwitchReward

API = {"id": "r7", "title": "Lizard", "cost": 300, "prompt": "type a name", "background_color": "#00C7AC",
       "is_enabled": True, "is_paused": True, "is_user_input_required": True,
       "should_redemptions_skip_request_queue": False,
       "global_cooldown_setting": {"is_enabled": True, "global_cooldown_seconds": 60},
       "max_per_stream_setting": {"is_enabled": False, "max_per_stream": 0},
       "max_per_user_per_stream_setting": {"is_enabled": True, "max_per_user_per_stream": 2},
       "image": None, "default_image": {"url_1x": "a.png", "url_2x": "b.png"}}


class TestTwitchReward(unittest.TestCase):
    def test_reads_what_twitch_sends(self) -> None:
        reward = TwitchReward.from_api(API, by_toolbox=True)
        self.assertEqual((reward.title, reward.cost, reward.prompt, reward.color), ("Lizard", 300, "type a name",
                                                                                  "#00C7AC"))
        self.assertEqual((reward.paused, reward.needs_text, reward.skip_queue), (True, True, False))
        self.assertEqual((reward.cooldown, reward.max_per_stream, reward.max_per_user), (60, 0, 2))
        self.assertEqual((reward.id, reward.by_toolbox, reward.image), ("r7", True, "b.png"))

    def test_writes_what_twitch_takes_0_means_no_limit(self) -> None:
        body = TwitchReward("Hydrate", cost=0, cooldown=30).to_api()
        self.assertEqual(body["cost"], 1)  # Twitch needs at least 1
        self.assertEqual((body["is_global_cooldown_enabled"], body["global_cooldown_seconds"]), (True, 30))
        self.assertEqual((body["is_max_per_stream_enabled"], body["is_max_per_user_per_stream_enabled"]),
                         (False, False))
        self.assertNotIn("id", body)
