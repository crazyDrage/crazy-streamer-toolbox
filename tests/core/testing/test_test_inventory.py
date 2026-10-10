import unittest

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.testing.test_inventory import TestInventory, slug


class TestTestInventory(unittest.TestCase):
    def test_lists_everything_in_the_menus_order_with_its_file(self) -> None:
        actions = ActionRegistry()

        async def noop() -> None:
            return None

        actions.add("obs.set_scene", noop, label="Set scene", group="Scenes")
        actions.add("obs.get_scene", noop, label="Get scene", group="Scenes")
        actions.add("vts.tint", noop)
        actions.add("logic.wait", noop, flow_only=True)
        actions.add("flow.my_own_flow", noop)
        actions.add("vts.pin_item", noop)
        actions.park(["vts.pin_item"])
        menu = [("Live", "/", []), ("Flows", "/flows", [("Edit flow", "/flows/edit")]),
                ("Overlay", "/overlays", [("Alerts", "/overlays?show=alerts")]), ("Tools", "/tools", []),
                ("Connections", "/connections", [])]
        items = TestInventory(actions, [("obs", "OBS"), ("vtube_studio", "VTube Studio")], ["SAMMI decks"],
                              {"twitch.chat": ("Twitch chat message", "Twitch"), "timer": ("Timer", "Toolbox"),
                               "chat": ("Chat message", "Any platform"),
                               "vts.model_loaded": ("Model loaded", "VTube Studio")},
                              {"vtube_studio": "vts"}, menu).items()
        self.assertEqual([(i.key, i.title, i.area, i.group, i.file, i.heading) for i in items], [
            ("page:/", "Live", "Live", "", "live/page", "Live"),
            ("page:/flows", "Flows", "Flows", "", "flows/page", "Flows"),
            ("page:/flows/edit", "Edit flow", "Flows", "", "flows/page", "Flows"),
            ("trigger:chat", "Chat message", "Any platform", "", "flows/triggers/any_platform",
             "Flows > Triggers > Any platform"),
            ("trigger:timer", "Timer", "Toolbox", "", "flows/triggers/toolbox", "Flows > Triggers > Toolbox"),
            ("trigger:twitch.chat", "Twitch chat message", "Twitch", "", "flows/triggers/twitch",
             "Flows > Triggers > Twitch"),
            ("trigger:vts.model_loaded", "Model loaded", "VTube Studio", "", "flows/triggers/vtube_studio",
             "Flows > Triggers > VTube Studio"),
            ("box:logic.wait", "Wait", "Logic", "", "flows/boxes/logic/general", "Flows > Boxes > Logic"),
            ("box:obs.get_scene", "Get scene", "OBS", "Scenes", "flows/boxes/obs/scenes",
             "Flows > Boxes > OBS > Scenes"),
            ("box:obs.set_scene", "Set scene", "OBS", "Scenes", "flows/boxes/obs/scenes",
             "Flows > Boxes > OBS > Scenes"),
            ("box:vts.tint", "Tint", "VTube Studio", "", "flows/boxes/vtube_studio/general",
             "Flows > Boxes > VTube Studio"),
            ("page:/overlays", "Overlay", "Overlay", "", "overlay/page", "Overlay"),
            ("page:/overlays?show=alerts", "Alerts", "Overlay", "", "overlay/page", "Overlay"),
            ("page:/tools", "Tools", "Tools", "", "tools/page", "Tools"),
            ("tool:sammi_decks", "SAMMI decks", "", "", "tools/sammi_decks", "Tools > SAMMI decks"),
            ("page:/connections", "Connections", "Connections", "", "connections/page", "Connections"),
            ("connection:obs", "OBS", "", "", "connections/obs", "Connections > OBS"),
            ("connection:vtube_studio", "VTube Studio", "", "", "connections/vtube_studio",
             "Connections > VTube Studio"),
        ])

    def test_a_slug_is_a_title_as_in_an_address(self) -> None:
        self.assertEqual(slug("SAMMI decks"), "sammi_decks")
        self.assertEqual(slug(" Points! "), "points")


if __name__ == "__main__":
    unittest.main()
