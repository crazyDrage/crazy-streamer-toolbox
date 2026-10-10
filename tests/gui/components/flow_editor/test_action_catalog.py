import unittest

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.actions.box_filter import BoxFilter
from streamer_toolbox.gui.components.flow_editor.action_catalog import ActionCatalog


async def noop() -> None:
    return None


class TestActionCatalog(unittest.TestCase):
    def setUp(self) -> None:
        actions = ActionRegistry()
        for name, description, group in (
                ("obs.switch_scene", "Switches OBS to a scene", "Scenes"),
                ("obs.set_volume", "Sets an audio source's volume", "Audio"),
                ("obs.get_volume", "An audio source's volume", "Audio"),
                ("logic.if", "Goes one way or the other", ""),
                ("flow.lizard_timer", "Runs the flow lizard_timer", ""),
                ("flow.testing", "Runs the flow testing", ""),
                ("mixitup.add_currency", "Gives a viewer some currency (rats)", "Currency")):
            actions.add(name, noop, description, group=group)
        self.actions = actions
        self.catalog = ActionCatalog(actions, exclude="flow.testing")

    def test_categories_basics_first_flows_last_with_counts(self) -> None:
        self.assertEqual(self.catalog.categories(), [("logic", "Logic", 1), ("mixitup", "Mix It Up", 1),
                                                     ("obs", "OBS", 3), ("flow", "Flows", 1)])

    def test_groups(self) -> None:
        groups = self.catalog.groups("obs")
        self.assertEqual([(g, [a.name for a in items]) for g, items in groups], [
            ("Audio", ["obs.get_volume", "obs.set_volume"]), ("Scenes", ["obs.switch_scene"])])
        self.assertEqual([g for g, _ in self.catalog.groups("logic")], [""])  # one group: no heading

    def test_search_every_word_anywhere_names_starting_with_it_first(self) -> None:
        found = self.catalog.search("Volume")
        self.assertEqual([(t, [a.name for a in items]) for t, items in found],
                         [("OBS", ["obs.get_volume", "obs.set_volume"])])
        self.assertEqual([a.name for _, items in self.catalog.search("rats viewer") for a in items],
                         ["mixitup.add_currency"])
        self.assertEqual([a.name for _, items in self.catalog.search("audio set") for a in items],
                         ["obs.set_volume"])
        self.assertEqual(self.catalog.search("testing"), [])  # the flow being edited isn't offered
        self.assertEqual(self.catalog.search("  "), [])

    def test_a_filter_keeps_whole_categories_and_single_groups(self) -> None:
        catalog = ActionCatalog(self.actions, box_filter=BoxFilter("Sound job", ("logic", "obs/Audio")))
        self.assertEqual(catalog.categories(), [("logic", "Logic", 1), ("obs", "OBS", 2)])
        self.assertEqual(catalog.search("scene"), [])
        self.assertEqual([a.name for _, items in catalog.search("volume") for a in items],
                         ["obs.get_volume", "obs.set_volume"])

    def test_single_boxes_can_be_left_out(self) -> None:
        catalog = ActionCatalog(self.actions, shows=lambda a: a.name != "obs.set_volume")
        self.assertEqual((catalog.count(), ActionCatalog(self.actions).count()), (6, 7))
        self.assertEqual([a.name for _, items in catalog.search("volume") for a in items], ["obs.get_volume"])

    def test_hidden_categories_are_left_out(self) -> None:
        catalog = ActionCatalog(self.actions, hide={"obs", "mixitup"})
        self.assertEqual([c for c, _, _ in catalog.categories()], ["logic", "flow"])
        self.assertEqual(catalog.search("volume"), [])


if __name__ == "__main__":
    unittest.main()
