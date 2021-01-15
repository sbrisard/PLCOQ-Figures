import json


__styles = {}


def load(filename):
    with open(filename, "r") as f:
        # TODO: This is pretty bad
        global __styles
        __styles = json.load(f)


def semantic_color(key, lightness="dark"):
    key2 = __styles["color"][key]
    r, g, b = __styles["color"][key2][lightness]
    return r / 255, g / 255, b / 255


def line_width(key):
    return __styles["line width"][key]


load("default_stylesheet.json")
