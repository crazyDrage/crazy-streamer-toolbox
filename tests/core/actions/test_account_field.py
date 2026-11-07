import inspect
import unittest

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.connections.current_account import ACCOUNT


class TestAccountField(unittest.IsolatedAsyncioTestCase):
    """His plan of 2026-11-05, step 3: every box of a connection with several accounts gets an Account field."""

    def setUp(self) -> None:
        self.actions = ActionRegistry()
        self.on = False
        self.seen: list[str] = []

        async def say(message: str) -> str:
            self.seen.append(ACCOUNT.get())
            return message.upper()

        async def own(account: str = "x") -> str:  # a box with an account field of its own
            return account

        self.actions.add("twitch.say", say)
        self.actions.add("twitch.own", own)
        self.actions.add("obs.say", say)
        self.actions.accounts_for("twitch", lambda: self.on, lambda: ["crazydrage", "crazydrage_bot"])

    async def test_the_box_runs_as_the_account_its_field_names(self) -> None:
        self.assertEqual(await self.actions.run("twitch.say", message="hi", account="Crazydrage_Bot"), "HI")
        self.assertEqual(await self.actions.run("twitch.say", message="hi"), "HI")
        self.assertEqual(self.seen, ["crazydrage_bot", ""])  # empty: the main account (his answer 122)
        self.assertEqual(ACCOUNT.get(), "")  # only for that one run

    def test_the_field_is_there_for_the_connections_boxes_only(self) -> None:
        params = inspect.signature(self.actions.get("twitch.say").handler).parameters
        self.assertEqual(list(params), ["message", "account"])
        self.assertNotIn("account", inspect.signature(self.actions.get("obs.say").handler).parameters)
        self.assertEqual(inspect.signature(self.actions.get("twitch.own").handler).parameters["account"].default,
                         "x")  # its own field stays as it is

    def test_a_box_added_later_gets_it_too(self) -> None:
        async def later(text: str) -> None:
            return None

        self.actions.add("twitch.later", later)
        self.assertIn("account", inspect.signature(self.actions.get("twitch.later").handler).parameters)

    def test_shown_with_the_switch_on_or_when_a_box_names_one(self) -> None:
        action = self.actions.get("twitch.say")
        self.assertFalse(action.shows("account", {}))
        self.assertTrue(action.shows("account", {"account": "crazydrage_bot"}))  # rule 29: never hidden
        self.on = True
        self.assertTrue(action.shows("account", {}))
        self.assertTrue(action.shows("message", {}))

    async def test_its_choices_are_the_accounts(self) -> None:
        choices = await self.actions.get("twitch.say").options["account"]()
        self.assertEqual(choices, {"": "main account", "crazydrage": "crazydrage",
                                   "crazydrage_bot": "crazydrage_bot"})


if __name__ == "__main__":
    unittest.main()
