import logging
from pathlib import Path

from fontTools.ttLib import TTCollection, TTFont

from streamer_toolbox.core.fonts.font_face import FontFace

log = logging.getLogger(__name__)
RESTRICTED = 0x0002  # OpenType OS/2 fsType: "restricted license embedding", the font may not be embedded
ITALIC = 0x0001  # OS/2 fsSelection


class FontReader:
    """Reads what a font file says about itself (fontTools, only the name and OS/2 tables). A file it can't
    read gives no faces."""

    def read(self, path: Path) -> list[FontFace]:
        try:  # the file opened here, so it is closed also when fontTools gives up (a bad upload can be deleted)
            with path.open("rb") as file:
                if path.suffix.casefold() == ".ttc":
                    return [self._face(font, path) for font in TTCollection(file, lazy=True).fonts]
                return [self._face(TTFont(file, lazy=True), path)]
        except Exception as e:  # not a font, broken, or a kind fontTools needs more for (woff2 without brotli)
            log.debug("font %s not read: %s", path, e)
            return []

    @staticmethod
    def _face(font: TTFont, path: Path) -> FontFace:
        names = font["name"]

        def name(*ids: int) -> str:
            for id_ in ids:
                found = names.getDebugName(id_)
                if found:
                    return found.strip()
            return ""

        os2 = font["OS/2"] if "OS/2" in font else None
        weight, most = int(getattr(os2, "usWeightClass", 400) or 400), 0
        if "fvar" in font:  # a variable font: every weight of its wght axis
            axis = next((a for a in font["fvar"].axes if a.axisTag == "wght"), None)
            if axis is not None:
                weight, most = int(axis.minValue), int(axis.maxValue)
        return FontFace(family=name(16, 1) or path.stem, path=path, weight=weight, weight_most=most,
                        italic=bool(getattr(os2, "fsSelection", 0) & ITALIC),
                        copyright=name(0), license=name(13), license_url=name(14),
                        no_embedding=bool(getattr(os2, "fsType", 0) & RESTRICTED))
