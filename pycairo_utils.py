"""
Helper functions for drawing with PyCairo.
"""
import math
import cairo

from geometry import project
from labelling import Label


def draw_line(ctx, x1, y1, x2, y2, stroke=True):
    ctx.move_to(x1, y1)
    ctx.line_to(x2, y2)
    if stroke:
        ctx.stroke()


def draw_polyline(ctx, xy, move_to_first=True):
    it = iter(xy)
    if move_to_first:
        ctx.move_to(*next(it))
    for x, y in it:
        ctx.line_to(x, y)


def draw_arrow_head(ctx):
    lw = ctx.get_line_width()
    w = 5 * lw
    h = 5 * lw
    ctx.move_to(0.0, 0.0)
    ctx.line_to(-w, 0.5 * h)
    ctx.line_to(-0.75 * w, 0.0)
    ctx.line_to(-w, -0.5 * h)
    ctx.close_path()
    ctx.fill()


def draw_arrow(ctx, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    angle = math.atan2(dy, dx)
    dr = 1.5 * ctx.get_line_width()
    ctx.move_to(x1, y1)
    ctx.line_to(x2 - dr * math.cos(angle), y2 - dr * math.sin(angle))
    ctx.stroke()
    ctx.save()
    ctx.translate(x2, y2)
    ctx.rotate(angle)
    draw_arrow_head(ctx)

    ctx.restore()


def draw_frame(ctx, labels=None):
    r = 10.0
    draw_arrow(ctx, 0.0, 0.0, *project(r, 0.0, 0.0))
    draw_arrow(ctx, 0.0, 0.0, *project(0.0, r, 0.0))
    draw_arrow(ctx, 0.0, 0.0, *project(0.0, 0.0, r))
    if labels is not None:
        color = "\\color[rgb]{{{:0.3f}, {:0.3f}, {:0.3f}}}".format(
            *ctx.get_source().get_rgba()
        )

        x, y = project(0.5 * r, 0.0, 0.0)
        labels.append(
            Label(
                color + r"\(\vec e_x\)",
                ctx.user_to_device(x, y + 3.0),
                (1.0, 1.0),
                y_upwards=False,
            )
        )
        x, y = project(0.0, 0.5 * r, 0.0)
        labels.append(
            Label(
                color + r"\(\vec e_y\)",
                ctx.user_to_device(x, y + 3.0),
                (0.0, 1.0),
                y_upwards=False,
            )
        )
        x, y = project(0.0, 0.0, r)
        labels.append(
            Label(
                color + r"\(\vec e_z\)",
                ctx.user_to_device(x + 1.0, y),
                (0.0, 0.75),
                y_upwards=False,
            )
        )


def draw_frame_2d(ctx, labels=None):
    r = 10.0
    lw = ctx.get_line_width()
    draw_arrow(ctx, 0.0, 0.0, r, 0.0)
    draw_arrow(ctx, 0.0, 0.0, 0.0, r)
    if labels is not None:
        color = "\\color[rgb]{{{:0.3f}, {:0.3f}, {:0.3f}}}".format(
            *ctx.get_source().get_rgba()
        )

        x, y = r, 0.0
        labels.append(
            Label(
                color + r"\(\vec e_x\)",
                ctx.user_to_device(x, y - 3 * lw),
                (0.5, 1.0),
                y_upwards=False,
            )
        )
        x, y = 0.0, r
        labels.append(
            Label(
                color + r"\(\vec e_y\)",
                ctx.user_to_device(x - 2 * lw, y),
                (1.0, 0.5),
                y_upwards=False,
            )
        )

