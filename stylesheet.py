import json
import os.path

import cairo

__styles = {}


def load(filename):
    with open(filename, "r") as f:
        # TODO: This is pretty bad
        global __styles
        __styles = json.load(f)


def color(key, lightness="dark"):
    value = __styles["color"][key]
    if isinstance(value, str):
        # Use recursive call in case of double aliases
        return color(value, lightness)
    else:
        r, g, b = value[lightness]
        return r / 255, g / 255, b / 255


def line_width(key):
    return __styles["line width"][key]


def init_cairo_context(surface):
    unit = __styles["unit"]
    width, height = __styles["figure size"]
    surface.set_size(width * unit, height * unit)
    ctx = cairo.Context(surface)

    ctx.scale(unit, unit)
    ctx.translate(0.5 * width, 0.5 * height)  # Place origin at center
    ctx.scale(1.0, -1.0)  # y points upwards
    ctx.set_line_cap(cairo.LineCap.ROUND)
    ctx.set_line_join(cairo.LineJoin.ROUND)
    return ctx


def full_path(basename):
    return os.path.join(__styles["output directory"], basename)


# This is executed when the module is imported
load("default_stylesheet.json")
