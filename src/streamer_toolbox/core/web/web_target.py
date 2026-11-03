import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote

METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE")
PLACE = re.compile(r"\{(\w+)\}")
SECRET = re.compile(r"\{secret\.(\w+)\}")
EITHER = re.compile(r"\{(secret\.)?(\w+)\}")  # filled in one go: a value never becomes a place itself


@dataclass(frozen=True)
class WebTarget:
    """Where a web box sends its request and what it takes from the answer (see WebBoxes for the file).

    `url` and the `headers`' values may hold {field}: that field's value goes there (in the address made safe
    for it), and {secret.name}: the plugin's key of that name, typed on its card under Plugins. The other
    fields go into the address after the ? for GET and DELETE, else into a JSON body. `output` names each data
    dot and where its value is in the answer: "punchline", "items.0.name" (a dot between the steps, a number
    for a list's place); "" is the whole answer."""

    url: str
    method: str = "GET"
    headers: dict[str, str] = field(default_factory=dict)
    output: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, target: dict[str, Any], output: dict[str, str]) -> "WebTarget":
        unknown = set(target) - {"url", "method", "headers"}
        if unknown or not target.get("url"):
            raise ValueError(f"a target needs \"url\" and may have method, headers (got {', '.join(sorted(target))})")
        url = str(target["url"])
        if not url.startswith(("http://", "https://")):
            raise ValueError(f"the url must start with http:// or https:// (got {url!r})")
        method = str(target.get("method", "GET")).upper()
        if method not in METHODS:
            raise ValueError(f"method must be one of {', '.join(METHODS)} (got {method!r})")
        if not isinstance(output, dict) or not all(isinstance(path, str) for path in output.values()):
            raise ValueError("output must be an object: {\"dot's name\": \"where in the answer\"}")
        return cls(url, method, {str(k): str(v) for k, v in dict(target.get("headers", {})).items()},
                   dict(output) or {"answer": ""})

    def places(self) -> set[str]:
        """The fields named as {field} in the address or a header."""
        return self._found(PLACE)

    def secrets(self) -> set[str]:
        """The keys named as {secret.name} in the address or a header."""
        return self._found(SECRET)

    def address(self, data: dict[str, Any], keys: dict[str, str]) -> str:
        return _fill(self.url, data, keys, lambda text: quote(text, safe=""))

    def sent_headers(self, data: dict[str, Any], keys: dict[str, str]) -> dict[str, str]:
        return {k: _fill(v, data, keys, str) for k, v in self.headers.items()}

    def outputs_from(self, answer: Any) -> dict[str, Any]:
        """The data dots' values; a step that isn't in the answer gives None."""
        return {name: _step(answer, path) for name, path in self.output.items()}

    def _found(self, pattern: re.Pattern[str]) -> set[str]:
        return set(pattern.findall(self.url)) | {n for value in self.headers.values() for n in pattern.findall(value)}


def _fill(text: str, data: dict[str, Any], keys: dict[str, str], safe: Any) -> str:
    def value(m: re.Match[str]) -> str:
        return safe(keys.get(m.group(2), "") if m.group(1) else str(data.get(m.group(2), "")))
    return EITHER.sub(value, text)


def _step(value: Any, path: str) -> Any:
    for step in path.split(".") if path else ():
        if isinstance(value, dict):
            value = value.get(step)
        elif isinstance(value, list) and step.lstrip("-").isdigit() and -len(value) <= int(step) < len(value):
            value = value[int(step)]
        else:
            return None
    return value
