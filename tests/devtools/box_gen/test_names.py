import unittest

from streamer_toolbox.devtools.box_gen.names import block, camel, literal, snake, unique, wrapped


class TestNames(unittest.TestCase):
    def test_snake_and_camel(self) -> None:
        self.assertEqual(snake("userName"), "user_name")
        self.assertEqual(snake("UserID"), "user_id")
        self.assertEqual(snake("HTTPStatus"), "http_status")
        self.assertEqual(snake("user-name 2"), "user_name_2")
        self.assertEqual(snake("class"), "class_")
        self.assertEqual(snake("1st"), "_1st")
        self.assertEqual(camel("get_counter"), "GetCounter")
        self.assertEqual(unique(["a", "b", "a"]), ["a", "b", "a_2"])

    def test_literal_double_quotes_and_escapes(self) -> None:
        self.assertEqual(literal({"a": [1, True, None], "b": 'say "hi"\n'}),
                         '{"a": [1, True, None], "b": "say \\"hi\\"\\n"}')
        self.assertEqual(literal(("GET", "x", {})), '("GET", "x", {})')

    def test_block_wraps_only_when_needed(self) -> None:
        self.assertEqual(block({"a": 1}, 4, 10), '{"a": 1}')
        wide = {f"key_{n}": "value " * 3 for n in range(6)}
        text = block(wide, 4, 20)
        self.assertTrue(text.startswith("{\n        \"key_0\": "))
        self.assertTrue(text.endswith("\n    }"))
        self.assertEqual(eval(text), wide)  # still the same value

    def test_wrapped_string_parts(self) -> None:
        text = wrapped("word " * 40, 20)
        self.assertGreater(text.count("\n"), 0)
        self.assertTrue(all(len(line) <= 118 for line in text.split("\n")))
        self.assertEqual(eval(text.replace("\n", " ")), "word " * 40)


if __name__ == "__main__":
    unittest.main()
