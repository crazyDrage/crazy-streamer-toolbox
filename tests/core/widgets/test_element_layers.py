import unittest

from streamer_toolbox.core.widgets.element_design import ElementDesign


class ElementLayersTest(unittest.TestCase):
    """His layers (2026-11-06): add, rename, change, copy, move and delete them."""

    def setUp(self) -> None:
        self.design = ElementDesign.new()

    def names(self) -> list[str]:
        return [self.design.layer_name(number) for number, _ in self.design.layers()]

    def test_layers_of_his_own(self) -> None:
        back = self.design.add_layer("", "Frame")
        self.assertEqual(["Always there", "Frame"], self.names())
        self.assertEqual("", self.design.event_of(back))
        self.assertEqual("Layer", self.design.layer_name(self.design.add_layer()))
        self.assertEqual("Layer 2", self.design.layer_name(self.design.add_layer()))

    def test_rename_a_layer(self) -> None:
        alert = self.design.add_layer("follower")
        self.assertEqual("Hello follow", self.design.rename_layer(alert, "  Hello   follow "))
        self.assertEqual([(0, "Always there"), (1, "Hello follow")], self.design.layers())
        self.design.rename_layer(alert, "Big hello")
        self.assertEqual("Big hello (Follow alert)", self.design.layers()[1][1])
        with self.assertRaises(ValueError):
            self.design.rename_layer(alert, "Always there")
        self.assertEqual("Big hello", self.design.rename_layer(alert, "   "))

    def test_streamelements_default_reads_as_its_event(self) -> None:
        alert = self.design.add_layer("cheer")
        self.design.config["configStates"][alert]["displayName"] = "Default"
        self.assertEqual("Cheer alert", self.design.layer_name(alert))

    def test_a_second_alert_for_an_event_is_a_variation(self) -> None:
        plain = self.design.add_layer("cheer")
        big = self.design.add_layer("cheer")
        self.assertEqual("Cheer alert 2", self.design.layer_name(big))
        self.assertEqual({"at_least": None, "at_most": None, "chance": None, "other": False},
                         self.design.condition(plain))
        self.assertEqual(100, self.design.condition(big)["at_least"])
        self.assertEqual(50, self.design.condition(self.design.add_layer("follower")
                                                   and self.design.add_layer("follower"))["chance"])

    def test_a_condition_of_his(self) -> None:
        alert = self.design.add_layer("raid")
        self.design.set_condition(alert, at_least=10, at_most=50.5)
        rule = self.design.config["configStates"][alert]["triggers"][0]["userCondition"]
        self.assertEqual({"and": [{">=": [{"var": "event.data.amount"}, 10]},
                                  {"<=": [{"var": "event.data.amount"}, 50.5]}]}, rule)
        self.design.set_condition(alert, at_most=None, chance=25)
        self.assertEqual({"at_least": 10, "at_most": None, "chance": 25, "other": False},
                         self.design.condition(alert))
        self.design.set_condition(alert, at_least=None, chance=None)
        self.assertEqual({}, self.design.config["configStates"][alert]["triggers"][0]["userCondition"])
        with self.assertRaises(ValueError):
            self.design.set_condition(0, at_least=3)

    def test_a_condition_from_streamelements_stays(self) -> None:
        alert = self.design.add_layer("tip")
        own = {"==": [{"var": "event.data.tier"}, "2000"]}
        self.design.config["configStates"][alert]["triggers"][0]["userCondition"] = own
        self.assertTrue(self.design.condition(alert)["other"])
        self.design.set_condition(alert, at_least=5)
        self.assertEqual({"and": [own, {">=": [{"var": "event.data.amount"}, 5]}]},
                         self.design.config["configStates"][alert]["triggers"][0]["userCondition"])

    def test_copy_move_and_delete_layers(self) -> None:
        alert = self.design.add_layer("follower")
        self.design.add(alert, "text")
        twin = self.design.duplicate_layer(alert)
        self.assertEqual(["Always there", "Follow alert", "Follow alert 2"], self.names())
        self.assertEqual(["Text"], list(self.design.pieces(twin)))
        states = self.design.config["configStates"]
        self.assertNotEqual(states[alert]["referenceId"], states[twin]["referenceId"])
        self.assertEqual(0, self.design.move_layer(twin, -5))
        self.assertEqual(["Follow alert 2", "Always there", "Follow alert"], self.names())
        self.assertEqual(2, self.design.move_layer(0, 9))
        self.design.remove_layer(0)
        self.design.remove_layer(0)
        self.assertEqual(["Follow alert 2"], self.names())
        with self.assertRaises(ValueError):
            self.design.remove_layer(0)

    def test_change_what_a_layer_is(self) -> None:
        alert = self.design.add_layer("follower")
        self.design.set_condition(alert, chance=30)
        self.design.set_layer_event(alert, "subscriber")
        self.assertEqual("Subscriber alert", self.design.layer_name(alert))
        rule = self.design.config["configStates"][alert]["triggers"][0]
        self.assertIn({"!=": [{"var": "event.data.gifted"}, True]}, rule["systemCondition"]["and"])
        self.assertEqual(30, self.design.condition(alert)["chance"])
        self.design.rename_layer(alert, "Mine")
        self.design.set_layer_event(alert, "")
        self.assertEqual("Mine", self.design.layer_name(alert))
        self.assertEqual("", self.design.event_of(alert))
        self.assertEqual([{"systemCondition": {}, "userCondition": {}}],
                         self.design.config["configStates"][alert]["triggers"])

    def test_off_and_in_front(self) -> None:
        alert = self.design.add_layer("raid")
        self.assertTrue(self.design.is_on(alert))
        self.assertEqual({"raid"}, self.design.events())
        self.design.set_on(alert, False)
        self.assertFalse(self.design.is_on(alert))
        self.assertEqual(set(), self.design.events())
        self.design.set_on(alert, True)
        self.assertNotIn("toolbox", self.design.config["configStates"][alert])
        self.assertFalse(self.design.in_front(0))
        self.design.set_in_front(0, True)
        self.assertTrue(self.design.in_front(0))
        self.design.config["configStates"][alert]["referenceId"] = "foreground"
        self.assertTrue(self.design.in_front(alert))

    def test_canvas_size(self) -> None:
        self.design.set_canvas(800, 10)
        self.assertEqual((800, 50), self.design.canvas())


if __name__ == "__main__":
    unittest.main()
