import struct

_IDENTITY = (0x10000, 0, 0, 0, 0x10000, 0, 0, 0, 0x40000000)
_ROTATE_90 = (0, 0x10000, 0, -0x10000, 0, 0, 0, 0, 0x40000000)


class Mp4Builder:
    """Builds minimal MP4 byte strings with just enough structure for header probing."""

    IDENTITY = _IDENTITY
    ROTATE_90 = _ROTATE_90

    @staticmethod
    def box(box_type: bytes, payload: bytes) -> bytes:
        return struct.pack(">I4s", 8 + len(payload), box_type) + payload

    @classmethod
    def tkhd(cls, width: int, height: int, matrix: tuple = _IDENTITY, version: int = 0) -> bytes:
        if version == 1:
            times = struct.pack(">QQIIQ", 0, 0, 1, 0, 0)
        else:
            times = struct.pack(">IIIII", 0, 0, 1, 0, 0)
        payload = (
            bytes([version, 0, 0, 3])
            + times
            + bytes(16)
            + struct.pack(">9i", *matrix)
            + struct.pack(">II", width << 16, height << 16)
        )
        return cls.box(b"tkhd", payload)

    @classmethod
    def mvhd(cls, timescale: int, duration: int, version: int = 0) -> bytes:
        """The movie header: how long it plays is duration / timescale seconds."""
        if version == 1:
            times = struct.pack(">QQIQ", 0, 0, timescale, duration)
        else:
            times = struct.pack(">IIII", 0, 0, timescale, duration)
        return cls.box(b"mvhd", bytes([version, 0, 0, 0]) + times + bytes(80))

    @classmethod
    def movie(cls, *tracks: bytes, mdat_first: bool = False, mvhd: bytes = b"") -> bytes:
        ftyp = cls.box(b"ftyp", b"isom" + bytes(4))
        moov = cls.box(b"moov", mvhd + b"".join(cls.box(b"trak", track) for track in tracks))
        mdat = cls.box(b"mdat", bytes(64))
        return ftyp + (mdat + moov if mdat_first else moov + mdat)
