import unittest

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.actions.numbered_fields import numbered_fields


class TestNumberedFields(unittest.TestCase):
    def test_count_comes_from_the_count_field_or_the_highest_number_at_least_one(self) -> None:
        self.assertEqual(numbered_fields("case", {}), ["case_1"])
        self.assertEqual(numbered_fields("case", {"cases": 3}), ["case_1", "case_2", "case_3"])
        self.assertEqual(numbered_fields("case", {"case_1": "a", "case_4": "d"}),  # an old 4-case Switch
                         ["case_1", "case_2", "case_3", "case_4"])
        self.assertEqual(numbered_fields("case", {"cases": "x", "case_10x": 1, "value": 2}), ["case_1"])

    def test_a_box_with_port_fields_has_one_output_per_field_before_its_ports(self) -> None:
        actions = ActionRegistry()

        async def switch(value, **cases):
            return "else"

        actions.add("logic.switch", switch, ports=("else",), port_fields="case")
        action = actions.get("logic.switch")
        self.assertEqual(action.ports_for({"cases": 3}), ("case_1", "case_2", "case_3", "else"))
        actions.add("logic.if", switch, ports=("then", "else"))
        self.assertEqual(actions.get("logic.if").ports_for({"cases": 3}), ("then", "else"))


if __name__ == "__main__":
    unittest.main()
