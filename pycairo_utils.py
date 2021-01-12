"""
Helper functions for drawing with PyCairo.
"""
import numpy as np
import itertools

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
