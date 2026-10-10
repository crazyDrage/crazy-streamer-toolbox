import types
import typing
from typing import Any

# what a value of the key's kind may go into without surprises (anything goes into "any" and "text")
FITS = {"number": {"number", "yes/no"}, "yes/no": {"yes/no"}, "text": {"text"},
        "list": {"list"}, "object": {"object"}}


class KindCheck:
    """Kinds for wires: a field's kind from its parameter type (float → number), and whether an output's kind
    fits into it. Like LOGO!'s "analog can't go into digital", but only a warning: text holding a number still
    works when the box runs."""

    @staticmethod
    def plain(annotation: Any) -> Any:
        """float | None → float: an optional field has the kind of its type."""
        if isinstance(annotation, str):  # postponed annotations: "float | None"
            others = [a.strip() for a in annotation.split("|") if a.strip() != "None"]
            return others[0] if len(others) == 1 else annotation
        if typing.get_origin(annotation) not in (typing.Union, types.UnionType):
            return annotation
        others = [a for a in typing.get_args(annotation) if a is not type(None)]
        return others[0] if len(others) == 1 else annotation

    @staticmethod
    def of_annotation(annotation: Any) -> str:
        annotation = KindCheck.plain(annotation)
        name = annotation if isinstance(annotation, str) else getattr(annotation, "__name__", "")
        return {"int": "number", "float": "number", "bool": "yes/no", "str": "text", "list": "list",
                "dict": "object"}.get(name.split("[", 1)[0], "any")

    @staticmethod
    def problem(source: str, target: str) -> str:
        """Empty if a `source` value fits a `target` field, else a short warning."""
        if not source or source == "any" or target in ("any", "text"):
            return ""
        return "" if target in FITS.get(source, {target}) else f"{source} into a {target} field"
