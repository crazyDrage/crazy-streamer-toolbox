import unittest

from streamer_toolbox.core.data.boxes.json_text_to_value import JsonTextToValue
from streamer_toolbox.core.data.boxes.value_to_json_text import ValueToJsonText


class TestJsonActions(unittest.IsolatedAsyncioTestCase):
    async def test_read_and_write(self) -> None:
        self.assertEqual(await JsonTextToValue().run('{"modelName": "Dragon", "items": ["hat"]}'),
                         {"modelName": "Dragon", "items": ["hat"]})
        self.assertEqual(await ValueToJsonText().run(["hat", "fän"]), '["hat", "fän"]')
        self.assertEqual(await ValueToJsonText().run({"a": 1}, pretty="true"), '{\n  "a": 1\n}')
        with self.assertRaisesRegex(ValueError, "not JSON text"):
            await JsonTextToValue().run("hat")


if __name__ == "__main__":
    unittest.main()
