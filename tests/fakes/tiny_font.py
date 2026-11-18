from pathlib import Path

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen


class TinyFont:
    """A real, tiny TrueType font file for tests (fontTools' FontBuilder): a family name, weight, italic, its
    license text and embedding flags (fsType) as a test needs them."""

    @staticmethod
    def make(path: Path, family: str, weight: int = 400, italic: bool = False, license: str = "",
             copyright: str = "", fs_type: int = 0) -> Path:
        builder = FontBuilder(1000, isTTF=True)
        builder.setupGlyphOrder([".notdef", "A"])
        builder.setupCharacterMap({ord("A"): "A"})
        pen = TTGlyphPen(None)
        pen.moveTo((100, 0))
        pen.lineTo((500, 700))
        pen.lineTo((900, 0))
        pen.closePath()
        glyph = pen.glyph()
        builder.setupGlyf({".notdef": TTGlyphPen(None).glyph(), "A": glyph})
        builder.setupHorizontalMetrics({".notdef": (500, 0), "A": (1000, 100)})
        builder.setupHorizontalHeader(ascent=800, descent=-200)
        style = ("Bold " if weight >= 700 else "") + ("Italic" if italic else "") or "Regular"
        builder.setupNameTable({"familyName": family, "styleName": style.strip(), "copyright": copyright,
                                "licenseDescription": license})
        builder.setupOS2(usWeightClass=weight, fsType=fs_type, fsSelection=0x0001 if italic else 0x0040)
        builder.setupPost()
        builder.font["head"].macStyle = (0x0001 if weight >= 700 else 0) | (0x0002 if italic else 0)
        path.parent.mkdir(parents=True, exist_ok=True)
        builder.save(str(path))
        return path
