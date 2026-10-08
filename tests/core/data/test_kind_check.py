import unittest
from typing import Any

from streamer_toolbox.core.data.kind_check import KindCheck


class TestKindCheck(unittest.TestCase):
    def test_kinds_from_parameter_types(self) -> None:
        self.assertEqual([KindCheck.of_annotation(a) for a in (float, "int", bool, str, "dict[str, Any]", Any,
                                                                 list, "list[str]")],
                         ["number", "number", "yes/no", "text", "object", "any", "list", "list"])

    def test_optional_fields_have_the_kind_of_their_type(self) -> None:
        self.assertEqual([KindCheck.of_annotation(a) for a in (float | None, "float | None", dict[str, Any] | None,
                                                                 str | int)],
                         ["number", "number", "object", "any"])
        self.assertIs(KindCheck.plain(float | None), float)

    def test_what_fits_where(self) -> None:
        self.assertEqual(KindCheck.problem("text", "number"), "text into a number field")
        self.assertEqual(KindCheck.problem("object", "number"), "object into a number field")
        for source, target in (("number", "text"), ("number", "number"), ("number", "yes/no"), ("", "number"),
                               ("any", "number"), ("text", "any"), ("object", "text")):
            self.assertEqual(KindCheck.problem(source, target), "", (source, target))
