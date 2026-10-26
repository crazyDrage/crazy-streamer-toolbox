import unittest

from streamer_toolbox.connections.obs.obs_request_error import ObsRequestError


class TestObsRequestError(unittest.TestCase):
    def test_not_running_names_the_output(self) -> None:
        cases = {"CreateRecordChapter": "OBS isn't recording right now", "SplitRecordFile": "OBS isn't recording",
                 "SendStreamCaption": "OBS isn't streaming right now", "SaveReplayBuffer": "the replay buffer",
                 "StopVirtualCam": "the virtual camera"}
        for request, words in cases.items():
            self.assertIn(words, str(ObsRequestError(request, 501, None)), request)
        self.assertEqual(str(ObsRequestError("CreateRecordChapter", 501, None)),
                         "OBS isn't recording right now (CreateRecordChapter, OBS code 501)")

    def test_obs_comment_stays_after_the_words(self) -> None:
        error = ObsRequestError("GetSourceFilter", 600, "No source was found by the name of `cam`.")
        self.assertEqual(str(error), "OBS has nothing with that name: No source was found by the name of `cam`. "
                                     "(GetSourceFilter, OBS code 600)")
        self.assertEqual((error.request_type, error.code), ("GetSourceFilter", 600))

    def test_an_existing_name_still_says_exist(self) -> None:  # overlay_source's hint looks for it
        self.assertIn("exist", str(ObsRequestError("CreateInput", 601, None)))

    def test_an_unknown_code_still_shows_it(self) -> None:
        self.assertEqual(str(ObsRequestError("Whatever", 999, None)), "OBS said no (Whatever, OBS code 999)")


if __name__ == "__main__":
    unittest.main()
