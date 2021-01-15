import json


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


load("default_stylesheet.json")
