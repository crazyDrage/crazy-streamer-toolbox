from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FontFace:
    """One face of a font file (a .ttc holds several): its family, weight (400 normal, 700 bold) and italic,
    and what the file says about itself: copyright, license text and address, and whether embedding is
    forbidden (OpenType fsType "restricted license"). A variable font has all weights from `weight` to
    `weight_most` (0: just the one)."""

    family: str
    path: Path
    weight: int = 400
    weight_most: int = 0
    italic: bool = False
    copyright: str = ""
    license: str = ""
    license_url: str = ""
    no_embedding: bool = False
