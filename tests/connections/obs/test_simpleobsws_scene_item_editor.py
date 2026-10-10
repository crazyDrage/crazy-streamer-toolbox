import unittest

import simpleobsws

from streamer_toolbox.core.layout.box import Box
from streamer_toolbox.connections.obs.obs_request_error import ObsRequestError
from streamer_toolbox.connections.obs.simpleobsws_scene_item_editor import SimpleobswsSceneItemEditor
from tests.fakes.fake_obs_client import FakeObsClient


def _response(request_type: str, ok: bool = True, data: dict | None = None) -> simpleobsws.RequestResponse:
    status = simpleobsws.RequestStatus(result=ok, code=100 if ok else 600, comment=None if ok else "No source")
    return simpleobsws.RequestResponse(requestType=request_type, requestStatus=status, responseData=data)


class TestSimpleobswsSceneItemEditor(unittest.IsolatedAsyncioTestCase):
    async def test_set_bounds_sends_bounds_transform_for_the_item(self) -> None:
        client = FakeObsClient({
            "GetSceneItemId": _response("GetSceneItemId", data={"sceneItemId": 7}),
            "SetSceneItemTransform": _response("SetSceneItemTransform"),
        })
        editor = SimpleobswsSceneItemEditor(client)

        await editor.set_bounds("toolbox_test", "sound_alert", Box(100, 50, 400, 900))

        get_id, set_transform = client.requests
        self.assertEqual(get_id.requestData, {"sceneName": "toolbox_test", "sourceName": "sound_alert"})
        self.assertEqual(set_transform.requestData["sceneItemId"], 7)
        transform = set_transform.requestData["sceneItemTransform"]
        self.assertEqual(transform["boundsType"], "OBS_BOUNDS_SCALE_INNER")
        self.assertEqual((transform["positionX"], transform["positionY"]), (100, 50))
        self.assertEqual((transform["boundsWidth"], transform["boundsHeight"]), (400, 900))

    async def test_failed_request_raises(self) -> None:
        client = FakeObsClient({"GetSceneItemId": _response("GetSceneItemId", ok=False)})
        editor = SimpleobswsSceneItemEditor(client)

        with self.assertRaises(ObsRequestError):
            await editor.set_bounds("toolbox_test", "missing", Box(0, 0, 1, 1))


if __name__ == "__main__":
    unittest.main()
