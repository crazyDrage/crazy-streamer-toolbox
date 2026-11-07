import re
from pathlib import Path

from streamer_toolbox.core.files.write_whole import write_whole

# the main listing, filled in for everyone (where it lives is still his to say: OPEN.md 109)
MAIN_LISTING = "https://raw.githubusercontent.com/crazyDrage/crazy-streamer-toolbox-plugins/main/plugins.toml"
FILE_NAME = "plugin_listings.txt"  # in the settings folder
COMMENT = "#"
OFFICIAL = f"{COMMENT} official"  # the note above the main listing
# a Google Drive file's share link (".../file/d/<id>/view?usp=...", ".../open?id=<id>"): its page, not the file
DRIVE_LINK = re.compile(r"https://drive\.google\.com/(?:file/d/([\w-]+)|(?:open|uc)\?(?:[^#]*&)?id=([\w-]+))")
DRIVE_RAW = "https://drive.google.com/uc?export=download&id={id}"


def raw_address(address: str) -> str:
    """The address the file itself comes from: a Google Drive share link becomes its download link (his
    listing on Drive, 2026-11-02); any other address stays as it is."""
    found = DRIVE_LINK.match(address.strip())
    return DRIVE_RAW.format(id=found.group(1) or found.group(2)) if found else address


class ListingAddresses:
    """The file that says where the plugin listings are (his answer of 2026-11-02): plain text, one web address
    or file path per line, `#` starts a note for people, empty lines are fine:

        # official
        https://raw.githubusercontent.com/.../plugins.toml
        # custom list
        C:/streams/my_plugins.toml

    Adding is one line at the end and removing takes out only that line, so his notes stay. Without the file
    the main listing counts (under "# official"); the file is written at the first change."""

    def __init__(self, path: Path) -> None:
        self._path = path

    @property
    def addresses(self) -> list[str]:
        return [line.strip() for line in self._lines() if line.strip() and not line.strip().startswith(COMMENT)]

    def add(self, address: str) -> None:
        address = raw_address(address.strip().strip('"'))
        if not address:
            raise ValueError("type a web address or the path of a file")
        if address.startswith(COMMENT):
            raise ValueError(f"an address can't start with {COMMENT} (that is a note)")
        if address not in self.addresses:
            self._write([*self._lines(), address])

    def remove(self, address: str) -> None:
        lines = self._lines()
        kept = [line for line in lines if line.strip() != address]
        if kept != lines:
            self._write(kept)

    def put_main_back(self) -> None:
        """Back under its "# official" note when that is still there, else at the top with it."""
        if MAIN_LISTING in self.addresses:
            return
        lines = self._lines()
        note = next((n for n, line in enumerate(lines) if line.strip() == OFFICIAL), None)
        if note is None:
            self._write([OFFICIAL, MAIN_LISTING, *lines])
        else:
            self._write([*lines[:note + 1], MAIN_LISTING, *lines[note + 1:]])

    def _lines(self) -> list[str]:
        if not self._path.is_file():
            return [OFFICIAL, MAIN_LISTING]
        return self._path.read_text(encoding="utf-8").splitlines()

    def _write(self, lines: list[str]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        write_whole(self._path, "\n".join(lines) + "\n")
