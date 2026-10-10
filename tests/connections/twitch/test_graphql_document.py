import unittest

from streamer_toolbox.connections.twitch.graphql_document import find_document, to_query, variables_of
from tests.fakes.player_code import QUESTION, player_code


class TestGraphqlDocument(unittest.TestCase):
    def test_the_question_is_read_out_of_the_packed_code_and_written_as_text(self) -> None:
        document = find_document(player_code(), "VideoAccessToken_Clip")
        self.assertEqual(to_query(document), QUESTION)
        self.assertEqual(variables_of(document, "VideoAccessToken_Clip"), ["slug", "platform", "codecs"])

    def test_code_without_the_question_gives_nothing(self) -> None:
        self.assertIsNone(find_document(player_code("Something_Else"), "VideoAccessToken_Clip"))
        self.assertIsNone(find_document("var a=1;", "VideoAccessToken_Clip"))
        cut = player_code()[:-200]  # the object never closes
        self.assertIsNone(find_document(cut, "VideoAccessToken_Clip"))

    def test_a_brace_inside_a_text_does_not_end_the_object(self) -> None:
        document = find_document(player_code(player_type='a}"{b'.replace('"', '\\"')), "VideoAccessToken_Clip")
        self.assertIn('playerType: "a}\\"{b"', to_query(document))

    def test_the_other_parts_a_question_can_have(self) -> None:
        document = {"kind": "Document", "definitions": [{
            "kind": "OperationDefinition", "operation": "query", "name": {"kind": "Name", "value": "Q"},
            "selectionSet": {"kind": "SelectionSet", "selections": [
                {"kind": "Field", "alias": {"kind": "Name", "value": "mine"}, "name": {"kind": "Name", "value": "user"},
                 "arguments": [{"kind": "Argument", "name": {"kind": "Name", "value": "first"},
                                "value": {"kind": "IntValue", "value": "5"}},
                               {"kind": "Argument", "name": {"kind": "Name", "value": "live"},
                                "value": {"kind": "BooleanValue", "value": True}},
                               {"kind": "Argument", "name": {"kind": "Name", "value": "after"},
                                "value": {"kind": "NullValue"}}],
                 "directives": [{"kind": "Directive", "name": {"kind": "Name", "value": "skip"}, "arguments": [
                     {"kind": "Argument", "name": {"kind": "Name", "value": "if"},
                      "value": {"kind": "BooleanValue", "value": False}}]}],
                 "selectionSet": {"kind": "SelectionSet", "selections": [
                     {"kind": "InlineFragment", "typeCondition": {"kind": "NamedType",
                                                                  "name": {"kind": "Name", "value": "User"}},
                      "selectionSet": {"kind": "SelectionSet", "selections": [
                          {"kind": "Field", "name": {"kind": "Name", "value": "id"}}]}}]}}]}}]}
        self.assertEqual(to_query(document),
                         "query Q { mine: user(first: 5, live: true, after: null) @skip(if: false) "
                         "{ ... on User { id } } }")
        with self.assertRaisesRegex(ValueError, "doesn't know: 'SchemaDefinition'"):
            to_query({"kind": "Document", "definitions": [{"kind": "SchemaDefinition"}]})


if __name__ == "__main__":
    unittest.main()
