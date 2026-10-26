import unittest

from streamer_toolbox.core.data.boxes.get_from_list import GetFromList
from streamer_toolbox.core.data.boxes.get_from_object import GetFromObject
from streamer_toolbox.core.flows.boxes.calculate import Calculate
from streamer_toolbox.core.flows.boxes.clamp import Clamp
from streamer_toolbox.core.flows.boxes.random_number import RandomNumber
from streamer_toolbox.core.flows.boxes.round_number import RoundNumber
from streamer_toolbox.core.points.boxes.get_points import GetPoints
from streamer_toolbox.core.variables.boxes.get_variable import GetVariable
from streamer_toolbox.core.variables.boxes.get_viewer_value import GetViewerValue


class TestDataOnlyBoxes(unittest.TestCase):
    def test_boxes_that_work_out_a_value_or_read_the_toolboxs_own_need_no_run_wire(self) -> None:  # OPEN 92
        for box in (Calculate, Clamp, RoundNumber, RandomNumber, GetFromList, GetFromObject, GetVariable,
                    GetViewerValue):
            with self.subTest(box=box.__name__):
                self.assertTrue(box.data_only)

    def test_what_may_ask_another_program_keeps_its_run_wire(self) -> None:  # his round 62 A
        self.assertFalse(GetPoints.data_only)  # the points can be Mix It Up's


if __name__ == "__main__":
    unittest.main()
