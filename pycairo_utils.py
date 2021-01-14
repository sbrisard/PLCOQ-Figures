"""
Helper functions for drawing with PyCairo.
"""
import cairo

MM = 72.0 / 25.4


def draw_line(ctx, x1, y1, x2, y2, stroke=True):
    ctx.move_to(x1, y1)
    ctx.line_to(x2, y2)
    if stroke:
        ctx.stroke()


def draw_polyline(ctx, xy, move_to_first=True, close_path=False):
    it = iter(xy)
    if move_to_first:
        ctx.move_to(*next(it))
    for x, y in it:
        ctx.line_to(x, y)


def init_context(surface, width, height):
    surface.set_size(width * MM, height * MM)
    ctx = cairo.Context(surface)

    ctx.scale(MM, MM)  # Default unit is mm
    ctx.translate(0.5 * width, 0.5 * height)  # Place origin at center
    ctx.scale(1.0, -1.0)  # y points upwards
    return ctx
