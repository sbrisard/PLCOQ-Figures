import json


__styles = {}


def parse_palette(palette):
    values = [int(palette[i : i + 2], 16) / 255 for i in range(0, len(palette), 2)]
    return list(zip(values[0::3], values[1::3], values[2::3]))


def load(filename):
    with open(filename, "r") as f:
        global __styles
        __styles = json.load(f)

    #__styles["color"] = {k: parse_palette(v) for k, v in __styles["color"].items()}


def color(index):
    return __styles["color"]["category20c"][index]


def semantic_color(key, lightness="dark"):
    key2 = __styles["color"][key]
    r, g, b = __styles["color"][key2][lightness]
    return r / 255, g / 255, b / 255


def line_width(key):
    return __styles["line width"][key]


load("default_stylesheet.json")
