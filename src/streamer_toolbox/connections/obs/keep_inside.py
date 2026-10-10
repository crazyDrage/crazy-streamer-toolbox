LEFT, RIGHT, TOP, BOTTOM = 1, 2, 4, 8  # OBS's alignment bits; neither of a pair = centre


def keep_inside(x: float, y: float, alignment: int, width: float, height: float, canvas_width: float,
                canvas_height: float) -> tuple[float, float]:
    """The position (x / y of the alignment point, like OBS keeps it) moved as little as needed so a box of
    width × height lies on the canvas; a box bigger than the canvas goes to its top / left edge. Rotation is
    not taken into account."""
    def offset(low: int, high: int, size: float) -> float:
        return 0.0 if alignment & low else size if alignment & high else size / 2

    dx, dy = offset(LEFT, RIGHT, width), offset(TOP, BOTTOM, height)
    left = min(max(x - dx, 0.0), max(canvas_width - width, 0.0))
    top = min(max(y - dy, 0.0), max(canvas_height - height, 0.0))
    return round(left + dx, 2), round(top + dy, 2)
