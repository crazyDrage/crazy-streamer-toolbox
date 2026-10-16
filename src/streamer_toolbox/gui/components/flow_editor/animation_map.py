from streamer_toolbox.connections.vtube_studio.vts_animation import VtsAnimation
from streamer_toolbox.connections.vtube_studio.vts_position import VtsPosition

WIDTH, HEIGHT = 320, 180  # the picture, 16:9 like the stream
MARGIN = 0.15  # room around the outermost point, in VTS units


class AnimationMap:
    """A small picture with the animation's path: the stream screen as a rectangle, numbered dots (bigger = model
    bigger), the start as a ring. It zooms out when spots lie off screen (a model's middle is often below it).
    Relative steps are drawn from the spot they were measured from (or the middle)."""

    @staticmethod
    def svg(animation: VtsAnimation, model: VtsPosition | None = None) -> str:
        start = (animation.base or VtsPosition(0, 0, 0, 0)) if animation.relative else None
        spots = [animation.target(step, start) if start else step.position for step in animation.steps]
        extra = [p for p in (start, model) if p]
        xs = [-1.0, 1.0, *(p.x for p in spots + extra)]
        ys = [-1.0, 1.0, *(p.y for p in spots + extra)]
        left, right = min(xs) - MARGIN, max(xs) + MARGIN
        bottom, top = min(ys) - MARGIN, max(ys) + MARGIN
        # one VTS unit is WIDTH/2 px across and HEIGHT/2 px up on screen: keep that shape, shrink to fit
        scale = min(2 / (right - left), 2 / (top - bottom))
        mid_x, mid_y = (left + right) / 2, (bottom + top) / 2

        def at(x: float, y: float) -> tuple[float, float]:
            return WIDTH / 2 + (x - mid_x) * scale * WIDTH / 2, HEIGHT / 2 - (y - mid_y) * scale * HEIGHT / 2

        (sx1, sy1), (sx2, sy2) = at(-1, 1), at(1, -1)
        parts = [f'<svg viewBox="0 0 {WIDTH} {HEIGHT}" width="100%" xmlns="http://www.w3.org/2000/svg" '
                 f'style="display:block">',
                 f'<rect x="0" y="0" width="{WIDTH}" height="{HEIGHT}" rx="6" fill="rgba(127,127,127,0.06)"/>',
                 f'<rect x="{sx1:.1f}" y="{sy1:.1f}" width="{sx2 - sx1:.1f}" height="{sy2 - sy1:.1f}" '
                 f'fill="rgba(127,127,127,0.12)" stroke="rgba(127,127,127,0.55)"><title>the screen</title></rect>']
        if model:
            x, y = at(model.x, model.y)
            parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="none" stroke="#21ba45" stroke-width="2" '
                         f'stroke-dasharray="2 2"><title>model now</title></circle>')
        points = [at(p.x, p.y) for p in spots]
        line = list(points)
        if start:
            x, y = at(start.x, start.y)
            parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="8" fill="none" stroke="#3fbfae" '
                         f'stroke-width="2"><title>start</title></circle>')
            line.insert(0, (x, y))
        if len(line) > 1:
            path = " ".join(f"{x:.1f},{y:.1f}" for x, y in line)
            parts.append(f'<polyline points="{path}" fill="none" stroke="#3fbfae" stroke-width="2" '
                         f'stroke-linejoin="round" opacity="0.7"/>')
        for number, ((x, y), spot) in enumerate(zip(points, spots), 1):
            radius = 6 + (max(-100.0, min(100.0, spot.size)) + 100) / 200 * 6
            parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" fill="#3fbfae"/>'
                         f'<text x="{x:.1f}" y="{y + 3.5:.1f}" text-anchor="middle" font-size="10" '
                         f'font-weight="700" fill="#fff">{number}</text>')
        parts.append("</svg>")
        return "".join(parts)
