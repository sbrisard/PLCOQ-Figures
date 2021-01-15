import json

import fig20210105175723, fig20210113144259

MM = 72.0 / 25.4


def parse_palette(palette):
    values = [int(palette[i : i + 2], 16) / 255 for i in range(0, len(palette), 2)]
    return list(zip(values[0::3], values[1::3], values[2::3]))


if __name__ == "__main__":
    with open("cairo_params.json", "r") as f:
        params = json.load(f)

    params["color"] = {k: parse_palette(v) for k, v in params["color"].items()}

    fig20210105175723.main(params)
    fig20210113144259.main(params)
