import asyncio
import unittest

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.actions.unknown_action_error import UnknownActionError


class TestActionRegistry(unittest.TestCase):
    def test_runs_handler_with_params(self) -> None:
        registry = ActionRegistry()

        async def greet(name: str = "chat") -> str:
            return f"hello {name}"

        registry.add("greet", greet, "say hello")
        self.assertEqual(asyncio.run(registry.run("greet", name="Kit")), "hello Kit")
        self.assertEqual([(a.name, a.description) for a in registry.all()], [("greet", "say hello")])

    def test_unknown_action_raises(self) -> None:
        with self.assertRaises(UnknownActionError):
            asyncio.run(ActionRegistry().run("nope"))

    def test_duplicate_name_is_rejected(self) -> None:
        registry = ActionRegistry()

        async def noop() -> None:
            return None

        registry.add("x", noop)
        with self.assertRaises(ValueError):
            registry.add("x", noop)

    def test_remove_frees_the_name_and_keeps_options(self) -> None:
        registry = ActionRegistry()

        async def noop() -> None:
            return None

        async def scenes() -> list[str]:
            return ["Scene"]

        registry.add("x", noop, options={"scene": scenes}, capture="y")
        self.assertEqual(registry.get("x").capture, "y")
        self.assertEqual(asyncio.run(registry.get("x").options["scene"]()), ["Scene"])
        registry.remove("x")
        registry.remove("never there")
        registry.add("x", noop)
        self.assertEqual(registry.get("x").options, {})

    def test_a_parked_action_is_in_no_list_but_still_runs(self) -> None:
        registry = ActionRegistry()

        async def pin() -> str:
            return "pinned"

        registry.add("pin", pin)
        registry.add("only.in.flows", pin, flow_only=True)
        registry.add("other", pin)
        registry.park(["pin", "only.in.flows", "not registered"])
        self.assertEqual([a.name for a in registry.all(include_flow_only=True)], ["other"])
        self.assertEqual(asyncio.run(registry.run("pin")), "pinned")
        self.assertEqual(registry.get("pin").name, "pin")
        self.assertIn("pin", registry)
        registry.park([])
        self.assertEqual([a.name for a in registry.all()], ["other", "pin"])


if __name__ == "__main__":
    unittest.main()
