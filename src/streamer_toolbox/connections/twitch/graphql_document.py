"""A GraphQL question as it sits in a web page's code (a parsed "Document" written as a JavaScript object,
the way build tools pack it) → the question as text again. Only reads text: nothing of the page's code is run.

find_document() cuts the object out of the code, to_query() writes it as a question. Used by
TwitchClipQuestion to learn how Twitch's own player asks for a clip."""
import json
import re
from typing import Any

STRING = re.compile(r'("(?:[^"\\]|\\.)*")')
KEY = re.compile(r"([{,]\s*)([A-Za-z_$][\w$]*)\s*:")
WORDS = ((re.compile(r"!0\b"), "true"), (re.compile(r"!1\b"), "false"), (re.compile(r"\bvoid 0\b"), "null"))
START = '{kind:"Document"'
MAX_LENGTH = 200_000  # a question is a few thousand characters; more than this is not one


def find_document(code: str, operation: str) -> dict[str, Any] | None:
    """The Document that holds the operation of that name, read from the code; None if it isn't in there."""
    named = code.find(f'name:{{kind:"Name",value:"{operation}"}}')
    start = code.rfind(START, 0, named) if named >= 0 else -1
    if start < 0:
        return None
    end = _closing(code, start)
    if end < 0:
        return None
    parts = STRING.split(code[start:end + 1])
    for index in range(0, len(parts), 2):  # the parts between the texts in quotes
        parts[index] = KEY.sub(r'\1"\2":', parts[index])
        for word, meaning in WORDS:
            parts[index] = word.sub(meaning, parts[index])
    try:
        document = json.loads("".join(parts))
    except ValueError:
        return None
    return document if isinstance(document, dict) and document.get("kind") == "Document" else None


def to_query(document: dict[str, Any]) -> str:
    """The Document as a question Twitch's GQL reads. ValueError for a part this doesn't know."""
    return _write(document)


def variables_of(document: dict[str, Any], operation: str) -> list[str]:
    """The names of the variables that operation asks for."""
    for definition in document.get("definitions") or []:
        if definition.get("kind") == "OperationDefinition" and _name(definition) == operation:
            return [_name(variable["variable"]) for variable in definition.get("variableDefinitions") or []]
    return []


def _closing(code: str, start: int) -> int:
    """Where the object that opens at `start` closes; -1 if it doesn't within MAX_LENGTH."""
    depth, in_text, position = 0, False, start
    limit = min(len(code), start + MAX_LENGTH)
    while position < limit:
        sign = code[position]
        if in_text:
            if sign == "\\":
                position += 1
            elif sign == '"':
                in_text = False
        elif sign == '"':
            in_text = True
        elif sign == "{":
            depth += 1
        elif sign == "}":
            depth -= 1
            if depth == 0:
                return position
        position += 1
    return -1


def _name(node: dict[str, Any]) -> str:
    return str((node.get("name") or {}).get("value", ""))


def _list(nodes: Any, before: str = "(", after: str = ")", between: str = ", ") -> str:
    return before + between.join(_write(node) for node in nodes) + after if nodes else ""


def _directives(node: dict[str, Any]) -> str:
    return "".join(" " + _write(directive) for directive in node.get("directives") or [])


def _write(node: dict[str, Any]) -> str:
    kind = node.get("kind")
    if kind == "Document":
        return "\n".join(_write(definition) for definition in node.get("definitions") or [])
    if kind == "OperationDefinition":
        head = f"{node.get('operation', 'query')} {_name(node)}{_list(node.get('variableDefinitions'))}"
        return f"{head}{_directives(node)} {_write(node['selectionSet'])}"
    if kind == "FragmentDefinition":
        return (f"fragment {_name(node)} on {_name(node['typeCondition'])}{_directives(node)} "
                f"{_write(node['selectionSet'])}")
    if kind == "VariableDefinition":
        default = f" = {_write(node['defaultValue'])}" if node.get("defaultValue") else ""
        return f"{_write(node['variable'])}: {_write(node['type'])}{default}"
    if kind == "SelectionSet":
        return _list(node.get("selections"), "{ ", " }", " ") or "{ }"
    if kind == "Field":
        alias = f"{node['alias']['value']}: " if node.get("alias") else ""
        inside = f" {_write(node['selectionSet'])}" if node.get("selectionSet") else ""
        return f"{alias}{_name(node)}{_list(node.get('arguments'))}{_directives(node)}{inside}"
    if kind == "InlineFragment":
        on = f"on {_name(node['typeCondition'])} " if node.get("typeCondition") else ""
        directives = f"{_directives(node).strip()} " if node.get("directives") else ""
        return f"... {on}{directives}{_write(node['selectionSet'])}"
    if kind == "FragmentSpread":
        return f"...{_name(node)}{_directives(node)}"
    if kind == "Directive":
        return f"@{_name(node)}{_list(node.get('arguments'))}"
    if kind in ("Argument", "ObjectField"):
        return f"{_name(node)}: {_write(node['value'])}"
    if kind == "Variable":
        return f"${_name(node)}"
    if kind == "NamedType":
        return _name(node)
    if kind == "NonNullType":
        return f"{_write(node['type'])}!"
    if kind == "ListType":
        return f"[{_write(node['type'])}]"
    if kind == "StringValue":
        return json.dumps(str(node.get("value", "")))
    if kind in ("IntValue", "FloatValue", "EnumValue"):
        return str(node.get("value", ""))
    if kind == "BooleanValue":
        return "true" if node.get("value") else "false"
    if kind == "NullValue":
        return "null"
    if kind == "ListValue":
        return _list(node.get("values"), "[", "]") or "[]"
    if kind == "ObjectValue":
        return _list(node.get("fields"), "{", "}") or "{}"
    raise ValueError(f"a part of the question this doesn't know: {kind!r}")
