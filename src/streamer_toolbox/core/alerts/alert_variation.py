from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AlertVariation:
    """A bigger alert from an amount on (1000 bits, a raid of 50): its own text, picture and sound. What is
    left empty stays what the alert has anyway; the look, seconds and volume are the alert's."""

    minimum: int = 0
    text: str = ""
    image: str = ""
    sound: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AlertVariation":
        return cls(int(data.get("minimum", 0)), str(data.get("text", "")), str(data.get("image", "")),
                   str(data.get("sound", "")))

    def to_dict(self) -> dict[str, Any]:
        return {"minimum": self.minimum, "text": self.text, "image": self.image, "sound": self.sound}
