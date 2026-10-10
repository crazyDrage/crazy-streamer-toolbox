import unittest

from streamer_toolbox.core.actions.box_filter import BoxFilter
from streamer_toolbox.core.actions.box_filter_draft import BoxFilterDraft
from streamer_toolbox.core.actions.registered_action import RegisteredAction


async def noop() -> None:
    return None


def box(name: str, group: str = "") -> RegisteredAction:
    return RegisteredAction(name, noop, "", group=group)


PLAY, STATUS = box("obs.play_video_once", "Media"), box("obs.get_media_status", "Media")
VOLUME, SCENE = box("obs.set_volume", "Audio"), box("obs.switch_scene", "Scenes")
OBS = [PLAY, STATUS, VOLUME, SCENE]
MEDIA = [PLAY, STATUS]


class TestBoxFilterDraft(unittest.TestCase):
    def test_single_boxes_go_in_and_out(self) -> None:
        draft = BoxFilterDraft()
        draft.add(PLAY)
        draft.add(PLAY)
        draft.add(VOLUME)
        draft.remove(VOLUME)
        self.assertEqual(draft.to_filter("Alerts"), BoxFilter("Alerts", ("obs.play_video_once",)))
        self.assertTrue(draft.has(PLAY))
        self.assertFalse(draft.has(STATUS))

    def test_a_whole_group_takes_its_single_boxes_in_and_remembers_one_left_out(self) -> None:
        draft = BoxFilterDraft(BoxFilter("x", ("obs.play_video_once",)))
        draft.add_all("obs/Media", MEDIA)
        self.assertEqual(draft.to_filter().parts, ("obs/Media",))
        self.assertTrue(draft.whole("obs/Media"))
        draft.remove(STATUS)
        self.assertEqual(draft.to_filter(), BoxFilter("", ("obs/Media",), ("obs.get_media_status",)))
        self.assertFalse(draft.has(STATUS))
        draft.add(STATUS)  # back in: nothing left out, and not twice
        self.assertEqual(draft.to_filter(), BoxFilter("", ("obs/Media",)))

    def test_a_whole_category_swallows_its_groups(self) -> None:
        draft = BoxFilterDraft(BoxFilter("x", ("obs/Media", "obs.set_volume"), ("obs.get_media_status",)))
        draft.add_all("obs", OBS)
        self.assertEqual(draft.to_filter(), BoxFilter("", ("obs",)))
        self.assertTrue(draft.whole("obs/Scenes"))

    def test_a_group_out_of_a_whole_category_is_left_out_box_by_box(self) -> None:
        draft = BoxFilterDraft(BoxFilter("x", ("obs",)))
        draft.remove_all("obs/Media", MEDIA)
        self.assertEqual(draft.to_filter(), BoxFilter("", ("obs",), ("obs.play_video_once", "obs.get_media_status")))
        self.assertEqual([draft.has(a) for a in OBS], [False, False, True, True])

    def test_a_category_taken_out_leaves_nothing_behind(self) -> None:
        draft = BoxFilterDraft(BoxFilter("x", ("obs/Media", "obs.set_volume", "sound"), ("obs.get_media_status",)))
        draft.remove_all("obs", OBS)
        self.assertEqual(draft.to_filter(), BoxFilter("", ("sound",)))


if __name__ == "__main__":
    unittest.main()
