import unittest

from streamer_toolbox.core.data.json_actions import JsonActions


class TestJsonActions(unittest.IsolatedAsyncioTestCase):
    async def test_read_and_write(self) -> None:
        self.assertEqual(await JsonActions.read('{"modelName": "Dragon", "items": ["hat"]}'),
                         {"modelName": "Dragon", "items": ["hat"]})
        self.assertEqual(await JsonActions.write(["hat", "fän"]), '["hat", "fän"]')
        self.assertEqual(await JsonActions.write({"a": 1}, pretty="true"), '{\n  "a": 1\n}')
        with self.assertRaisesRegex(ValueError, "not JSON text"):
            await JsonActions.read("hat")


if __name__ == "__main__":
    unittest.main()
