import unittest

from streamer_toolbox.core.security.login_throttle import LoginThrottle


class TestLoginThrottle(unittest.TestCase):
    def test_too_many_wrong_tries_wait_then_may_try_again(self) -> None:
        now = [0.0]
        throttle = LoginThrottle(limit=3, window=60, clock=lambda: now[0])
        for _ in range(3):
            self.assertEqual(throttle.wait_seconds("phone"), 0)
            throttle.failed("phone")
            now[0] += 1
        self.assertAlmostEqual(throttle.wait_seconds("phone"), 57)
        self.assertEqual(throttle.wait_seconds("laptop"), 0)  # per address
        now[0] = 61
        self.assertEqual(throttle.wait_seconds("phone"), 0)
        throttle.failed("phone")
        throttle.succeeded("phone")
        self.assertEqual(throttle.wait_seconds("phone"), 0)
