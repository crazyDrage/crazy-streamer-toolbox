import unittest
from unittest.mock import Mock

from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.flows.flow_library import FlowLibrary
from streamer_toolbox.gui.pages.flows_page import FlowsPage


class TestFlowsPageSideItems(unittest.TestCase):
    """The Flows tab's side list: a row per folder with its flows under it, "No folder" last."""

    def test_folders_with_their_flows_below_them(self) -> None:
        library = Mock(spec=FlowLibrary)
        library.all.return_value = [Flow("b", "Bonk", folder="Fun"), Flow("a", "Alert"),
                                    Flow("c", "Clap", folder="Fun"), Flow("d", "Mine sweep", folder="My games")]
        library.folders.return_value = ["Fun", "My games"]
        page = FlowsPage(library, Mock(), Mock())
        self.assertEqual(page.side_items(), [
            ("Fun", "/flows?show=Fun", "folder"),
            ("Bonk", "/flows/edit?flow=b", "account_tree", True),
            ("Clap", "/flows/edit?flow=c", "account_tree", True),
            ("My games", "/flows?show=My%20games", "folder"),
            ("Mine sweep", "/flows/edit?flow=d", "account_tree", True),
            ("No folder", "/flows?show=~", "folder_off"),
            ("Alert", "/flows/edit?flow=a", "account_tree", True)])

    def test_no_flows_no_side_list(self) -> None:
        library = Mock(spec=FlowLibrary)
        library.all.return_value = []
        library.folders.return_value = []
        self.assertEqual(FlowsPage(library, Mock(), Mock()).side_items(), [])


if __name__ == "__main__":
    unittest.main()
