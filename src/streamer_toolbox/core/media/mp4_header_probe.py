import struct
from pathlib import Path
from typing import BinaryIO, Iterator, Optional

from streamer_toolbox.core.interfaces.video_probe import VideoProbe
from streamer_toolbox.core.media.video_size import VideoSize


class Mp4HeaderProbe(VideoProbe):
    """Reads the video size (moov/trak/tkhd) and length (moov/mvhd) from an MP4/MOV header. Pure Python, no ffmpeg.

    Only box headers are read and large boxes such as mdat are skipped with a seek, so this is
    fast even for big files and works whether moov sits before or after mdat.
    Phone videos are often stored landscape with a 90/270 degree rotation matrix; the returned
    size is the display size, with width and height swapped for those.
    """

    _CONTAINERS = {b"moov", b"trak"}

    def probe(self, path: Path) -> Optional[VideoSize]:
        try:
            with path.open("rb") as file:
                end = file.seek(0, 2)
                return self._find_video_size(file, 0, end)
        except (OSError, struct.error):
            return None

    def length(self, path: Path) -> Optional[float]:
        try:
            with path.open("rb") as file:
                end = file.seek(0, 2)
                for box_type, payload_start, box_end in self._iter_boxes(file, 0, end):
                    if box_type != b"moov":
                        continue
                    for inner, inner_start, inner_end in self._iter_boxes(file, payload_start, box_end):
                        if inner == b"mvhd":
                            file.seek(inner_start)
                            return self._parse_mvhd(file.read(min(inner_end - inner_start, 32)))
        except (OSError, struct.error):
            return None
        return None

    @staticmethod
    def _parse_mvhd(payload: bytes) -> Optional[float]:
        # version/flags, creation + modification time (4 or 8 bytes each), timescale, duration (4 or 8)
        if payload[0] == 1:
            timescale, duration = struct.unpack_from(">IQ", payload, 20)
            unknown = 0xFFFFFFFFFFFFFFFF
        else:
            timescale, duration = struct.unpack_from(">II", payload, 12)
            unknown = 0xFFFFFFFF
        if not timescale or duration in (0, unknown):  # a fragmented or streamed file: the length isn't here
            return None
        return duration / timescale

    def _find_video_size(self, file: BinaryIO, start: int, end: int) -> Optional[VideoSize]:
        for box_type, payload_start, box_end in self._iter_boxes(file, start, end):
            if box_type in self._CONTAINERS:
                size = self._find_video_size(file, payload_start, box_end)
                if size is not None:
                    return size
            elif box_type == b"tkhd":
                file.seek(payload_start)
                size = self._parse_tkhd(file.read(box_end - payload_start))
                if size is not None:
                    return size
        return None

    @staticmethod
    def _iter_boxes(file: BinaryIO, start: int, end: int) -> Iterator[tuple[bytes, int, int]]:
        position = start
        while position + 8 <= end:
            file.seek(position)
            box_size, box_type = struct.unpack(">I4s", file.read(8))
            header_size = 8
            if box_size == 1:
                box_size = struct.unpack(">Q", file.read(8))[0]
                header_size = 16
            elif box_size == 0:
                box_size = end - position
            if box_size < header_size or position + box_size > end:
                return
            yield box_type, position + header_size, position + box_size
            position += box_size

    @staticmethod
    def _parse_tkhd(payload: bytes) -> Optional[VideoSize]:
        version = payload[0]
        # version/flags, then creation/modification time, track id, reserved, duration
        offset = 36 if version == 1 else 24
        # reserved(8) layer(2) alternate_group(2) volume(2) reserved(2)
        offset += 16
        matrix = struct.unpack_from(">9i", payload, offset)
        width_fixed, height_fixed = struct.unpack_from(">II", payload, offset + 36)
        width = round(width_fixed / 65536)
        height = round(height_fixed / 65536)
        if width == 0 or height == 0:
            return None  # audio or other non-visual track
        a, b = matrix[0], matrix[1]
        if a == 0 and b != 0:  # rotated by 90 or 270 degrees
            width, height = height, width
        return VideoSize(width, height)
