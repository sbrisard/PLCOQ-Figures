"""
Helper functions for drawing with PyCairo.
"""
import numpy as np
import itertools

def draw_polyline(ctx, xy, move_to_first=True):
    it = iter(xy)
    if move_to_first:
        ctx.move_to(*next(it))
    for x, y in it:
        ctx.line_to(x, y)
