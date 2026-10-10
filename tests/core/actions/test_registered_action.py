import unittest

from streamer_toolbox.core.actions.registered_action import RegisteredAction


async def noop() -> None:
    return None


class TestRegisteredAction(unittest.TestCase):
    def test_title_is_humanised_name_without_category(self) -> None:
        action = RegisteredAction("obs.fit_raid_clip", noop, "")
        self.assertEqual((action.category, action.title), ("obs", "Fit raid clip"))

    def test_label_wins_over_name(self) -> None:
        self.assertEqual(RegisteredAction("hello.greet", noop, "", "Say hello").title, "Say hello")

    def test_name_without_dot_is_a_core_action(self) -> None:
        self.assertEqual(RegisteredAction("restart", noop, "").category, "toolbox")

    def test_filled_keeps_what_was_typed(self) -> None:
        def template(request):
            return {"data": f"{{{request}}}"}
        action = RegisteredAction("obs.request", noop, "", fills={"request": template})
        params = action.filled({}, "request", "A")
        self.assertEqual(params, {"request": "A", "data": "{A}"})
        params = action.filled(params, "request", "B")  # still the template of A: replaced
        self.assertEqual(params["data"], "{B}")
        params = action.filled(dict(params, data="typed"), "request", "C")
        self.assertEqual(params, {"request": "C", "data": "typed"})
        self.assertEqual(action.filled({"x": 1}, "x", 2), {"x": 2})  # a field without fills

    def test_shown_hides_the_fields_the_chosen_way_does_not_use(self) -> None:
        async def send(way: str = "mail", address: str = "", number: str = "", text: str = "") -> None:
            pass
        action = RegisteredAction("x.send", send, "", shown={"address": ("way", ("mail",)),
                                                              "number": ("way", ("phone", "fax"))})
        self.assertEqual(action.choosers(), {"way"})
        self.assertEqual([action.shows(f, {}) for f in ("way", "address", "number", "text")],
                         [True, True, False, True])  # an empty chooser counts as its default
        self.assertEqual([action.shows(f, {"way": "fax"}) for f in ("address", "number")], [False, True])
        self.assertEqual([action.shows(f, {"way": "${var.way}"}) for f in ("address", "number")],
                         [True, True])  # only known when the box runs: nothing is hidden


if __name__ == "__main__":
    unittest.main()
