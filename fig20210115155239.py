from itertools import chain

import cairo
import numpy as np

import geometry
import stylesheet

from labelling import insert_labels, Label
from pycairo_utils import draw_frame_2d, draw_mark, draw_polyline, draw_arrow_head


def main():
    basename = "fig20210115155239"
    filename = stylesheet.full_path(basename + "-bare.pdf")

    shell = geometry.default_shell(plate=True, constant_thickness=False)

    u = 0.0
    v = np.linspace(-20.0, 20.0, num=51)

    with cairo.PDFSurface(filename, 1, 1) as surface:
        ctx = stylesheet.init_cairo_context(surface)

        project = lambda x, y, z: (y, z)

        points = chain(
            (project(*shell.f_inf(u, v_)) for v_ in v),
            (project(*shell.f_sup(u, v_)) for v_ in v[::-1]),
        )
        draw_polyline(ctx, points)
        ctx.close_path()
        path = ctx.copy_path()

        ctx.set_source_rgb(*stylesheet.color("system", "medium"))
        ctx.fill()

        draw_polyline(ctx, [(v[0], 0), (v[-1], 0)])

        ctx.set_source_rgb(*stylesheet.color("mid-surface"))
        ctx.set_line_width(stylesheet.line_width("thin"))
        ctx.stroke()

        ctx.append_path(path)
        ctx.set_source_rgb(0.0, 0.0, 0.0)
        ctx.set_line_width(stylesheet.line_width("thick"))
        ctx.stroke()

        labels = []

        dx, dy = 5.0, 5.0

        ctx.set_source_rgb(0.0, 0.0, 0.0)
        ctx.set_line_width(stylesheet.line_width("thin"))

        t = 0.75
        x1 = (1 - t) * v[0] + t * v[-1]
        _, _, y1 = shell.f_sup(u, x1)
        x2, y2 = x1 + dx, y1 + dy
        ctx.move_to(x1, y1)
        ctx.line_to(x2, y2)
        ctx.stroke()
        labels.append(
            Label(
                r"\(\partial\Omega^+\)",
                ctx.user_to_device(x2, y2),
                (0.0, 0.0),
                y_upwards=False,
            )
        )

        _, _, y1 = shell.f_inf(u, x1)
        x2, y2 = x1 + dx, y1 - dy
        ctx.move_to(x1, y1)
        ctx.line_to(x2, y2)
        ctx.stroke()
        labels.append(
            Label(
                r"\(\partial\Omega^-\)",
                ctx.user_to_device(x2, y2),
                (0.0, 1.0),
                y_upwards=False,
            )
        )

        t = 0.25
        x1 = (1 - t) * v[0] + t * v[-1]
        _, _, y1 = shell.f_inf(u, x1)
        y1 *= 0.5
        x2, y2 = x1 - dx, y1 - dy
        ctx.move_to(x1, y1)
        ctx.line_to(x2, y2)
        labels.append(
            Label(
                r"\(\Omega\)",
                ctx.user_to_device(x2, y2),
                (1.0, 1.0),
                y_upwards=False,
            )
        )

        t = 0.95
        x1 = (1 - t) * v[0] + t * v[-1]
        _, _, y1 = shell.f_mid(u, x1)
        x2, y2 = x1 + dx, y1 + dy
        ctx.move_to(x1, y1)
        ctx.line_to(x2, y2)
        labels.append(
            Label(
                r"\(\Sigma\)",
                ctx.user_to_device(x2, y2),
                (0.0, 0.0),
                y_upwards=False,
            )
        )

        ctx.stroke()

        ctx.save()
        ctx.translate(-35.0, 0.0)
        ctx.set_source_rgb(*stylesheet.color("unit-vector"))
        draw_frame_2d(ctx, labels)
        ctx.restore()

        for label in labels:
            if r"\vec e_y" in label.contents:
                label.contents = label.contents.replace(r"\vec e_y", r"\vec e_z")

        leg = 3.0
        shift = 7.5
        x = 0.5 * (v[0] + v[-1])
        y_mid = 0.0
        _, _, y_inf = shell.f_inf(u, x)
        _, _, y_sup = shell.f_sup(u, x)

        ctx.set_line_width(stylesheet.line_width("normal"))
        ctx.move_to(x, y_inf)
        ctx.line_to(x, y_sup)
        ctx.stroke()
        draw_mark(ctx, x, y_mid)

        ctx.set_line_width(stylesheet.line_width("thin"))
        ctx.move_to(x, y_mid)
        ctx.line_to(x + dx, y_mid - dy)
        ctx.stroke()
        labels.append(
            Label(
                r"\(\point{M}\)",
                ctx.user_to_device(x + dx, y_mid - dy),
                (0.0, 1.0),
                y_upwards=False,
            )
        )

        ctx.move_to(x, y_sup)
        ctx.line_to(x - shift, y_sup + shift)
        ctx.move_to(x, y_mid)
        ctx.line_to(x - shift, y_mid + shift)
        ctx.stroke()

        ctx.move_to(x - shift, y_mid + shift - leg)
        ctx.line_to(x - shift, y_sup + shift + leg)
        ctx.stroke()

        ctx.save()
        ctx.translate(x - shift, y_mid + shift)
        ctx.rotate(0.5 * np.pi)
        draw_arrow_head(ctx)
        ctx.restore()

        ctx.save()
        ctx.translate(x - shift, y_sup + shift)
        ctx.rotate(-0.5 * np.pi)
        draw_arrow_head(ctx)
        ctx.restore()

        labels.append(
            Label(
                r"\(Z^+(\point{M})\)",
                ctx.user_to_device(x - shift, y_sup + shift + leg),
                (0.5, 0.0),
                y_upwards=False,
            )
        )

        ctx.move_to(x, y_inf)
        ctx.line_to(x - shift, y_inf - shift)
        ctx.move_to(x, y_mid)
        ctx.line_to(x - shift, y_mid - shift)
        ctx.stroke()

        ctx.move_to(x - shift, y_mid - shift + leg)
        ctx.line_to(x - shift, y_inf - shift - leg)
        ctx.stroke()

        ctx.save()
        ctx.translate(x - shift, y_mid - shift)
        ctx.rotate(-0.5 * np.pi)
        draw_arrow_head(ctx)
        ctx.restore()

        ctx.save()
        ctx.translate(x - shift, y_inf - shift)
        ctx.rotate(0.5 * np.pi)
        draw_arrow_head(ctx)
        ctx.restore()

        labels.append(
            Label(
                r"\(Z^-(\point{M})\)",
                ctx.user_to_device(x - shift, y_inf - shift - leg),
                (0.5, 1.0),
                y_upwards=False,
            )
        )

    insert_labels(basename, labels)
