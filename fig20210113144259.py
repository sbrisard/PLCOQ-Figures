from itertools import chain

import cairo
import numpy as np
import shapely

from geometry import default_shell, project
from labelling import Label, insert_labels
from pycairo_utils import draw_arrow, draw_frame, draw_polyline, init_context


def main(params):
    basename = "fig20210113144259"
    shell = default_shell(plate=True, constant_thickness=False)

    u = np.linspace(-15.0, 15.0, num=51)
    v = np.linspace(-20.0, 20.0, num=51)

    u_cut = 0.0

    pf_sup = lambda u, v: project(*shell.f_sup(u, v))
    pf_inf = lambda u, v: project(*shell.f_inf(u, v))
    pf_mid = lambda u, v: project(*shell.f_mid(u, v))

    palette = params["color"]["category20c"]

    with cairo.PDFSurface(basename + "-bare.pdf", 1, 1) as surface:
        ctx = init_context(surface)
        ctx.set_line_width(params["line width"]["normal"])

        ctx.set_source_rgb(*palette[-1])
        ctx.move_to(*pf_sup(u[0], v[0]))
        for u_ in u[1:]:
            ctx.line_to(*pf_sup(u_, v[0]))
        for v_ in v:
            ctx.line_to(*pf_sup(u[-1], v_))
        for u_ in u[::-1]:
            ctx.line_to(*pf_sup(u_, v[-1]))
        for v_ in v[::-1]:
            ctx.line_to(*pf_sup(u[0], v_))
        ctx.close_path()
        upper_surface = ctx.copy_path()
        ctx.fill()

        ctx.set_source_rgb(*palette[-2])
        ctx.move_to(*pf_inf(u[-1], v[0]))
        for v_ in v[1:]:
            ctx.line_to(*pf_inf(u[-1], v_))
        for v_ in v[::-1]:
            ctx.line_to(*pf_sup(u[-1], v_))
        ctx.close_path()
        lateral_surface_100 = ctx.copy_path()
        ctx.fill()

        ctx.set_source_rgb(*palette[-4])
        ctx.move_to(*pf_inf(u[0], v[-1]))
        for u_ in u[1:]:
            ctx.line_to(*pf_inf(u_, v[-1]))
        for u_ in u[::-1]:
            ctx.line_to(*pf_sup(u_, v[-1]))
        ctx.close_path()
        lateral_surface_010 = ctx.copy_path()
        ctx.fill()

        ctx.set_source_rgb(0.0, 0.0, 0.0)
        ctx.append_path(upper_surface)
        ctx.append_path(lateral_surface_100)
        ctx.append_path(lateral_surface_010)
        ctx.stroke()

        ctx.set_source_rgb(*palette[4])
        ctx.move_to(*pf_mid(u[-1], v[0]))
        for v_ in v[1:]:
            ctx.line_to(*pf_mid(u[-1], v_))
        for u_ in u[::-1]:
            ctx.line_to(*pf_mid(u_, v[-1]))
        ctx.stroke()

        ctx.set_source_rgba(*palette[8], 0.5)
        FG = shapely.geometry.LineString(pf_sup(u_cut, v_) for v_ in v)

        x = 0.0
        y1, z1 = v[0] - 10.0, -10.0
        y2, z2 = v[-1] + 10.0, 10.0
        ls1 = shapely.geometry.LineString((project(x, y1, z1), project(x, y2, z1)))
        ls2 = shapely.geometry.LineString(pf_inf(u_, v[-1]) for u_ in u)
        A = ls1.intersection(ls2)
        B = shapely.geometry.Point(*project(x, y2, z1))
        C = shapely.geometry.Point(*project(x, y2, z2))
        D = shapely.geometry.Point(*project(x, y1, z2))
        H = shapely.geometry.Point(*pf_inf(u_cut, v[-1]))

        ls1 = shapely.geometry.LineString(pf_sup(u_, v[0]) for u_ in u[::-1])
        ls2 = shapely.geometry.LineString((project(x, y1, z1), project(x, y1, z2)))
        E = ls1.intersection(ls2)
        F = ls1.intersection(FG)

        rect = shapely.geometry.Polygon([E, (F.x, E.y), F, (E.x, F.y)])
        EF = rect.intersection(ls1)

        rect = shapely.geometry.Polygon([A, (H.x, A.y), H, (A.x, H.y)])
        HA = rect.intersection(
            shapely.geometry.LineString(pf_inf(u_, v[-1]) for u_ in u)
        )

        ctx.move_to(A.x, A.y)
        ctx.line_to(B.x, B.y)
        ctx.line_to(C.x, C.y)
        ctx.line_to(D.x, D.y)
        draw_polyline(ctx, chain(EF.coords, FG.coords, HA.coords), move_to_first=False)
        ctx.close_path()
        cutting_plane = ctx.copy_path()
        ctx.fill()

        ctx.set_line_width(params["line width"]["thin"])
        ctx.set_source_rgb(*palette[8])
        ctx.append_path(cutting_plane)
        ctx.stroke()

        ctx.set_source_rgb(0.0, 0.0, 0.0)
        ctx.set_line_width(params["line width"]["thin"])
        labels = []
        labels.append(
            Label(
                r"\(\Omega\)",
                ctx.user_to_device(*pf_sup(0.75 * u[-1], 0.75 * v[0])),
                (0.5, 0.5),
                y_upwards=False,
            )
        )

        dx, dy = 5.0, 5.0

        ls = shapely.geometry.LineString(pf_mid(u[-1], v_) for v_ in v)
        p1 = ls.interpolate(0.5, normalized=True)
        x2, y2 = p1.x - dx, p1.y - dy
        ctx.move_to(p1.x, p1.y)
        ctx.line_to(x2, y2)
        ctx.stroke()
        labels.append(
            Label(
                r"\(\Sigma\)", ctx.user_to_device(x2, y2), (1.0, 1.0), y_upwards=False
            )
        )

        ls = shapely.geometry.LineString(pf_inf(u[-1], v_) for v_ in v)
        p1 = ls.interpolate(0.75, normalized=True)
        x2, y2 = p1.x - dx, p1.y - dy
        ctx.move_to(p1.x, p1.y)
        ctx.line_to(x2, y2)
        ctx.stroke()
        labels.append(
            Label(
                r"\(\partial\Omega^-\)",
                ctx.user_to_device(x2, y2),
                (1.0, 1.0),
                y_upwards=False,
            )
        )

        u_ = u[-1]
        v_ = 0.75 * v[0]
        x1, y1 = pf_mid(u_, v_)
        x2, y2 = pf_inf(u_, v_)
        x1 = 0.5 * (x1 + x2)
        y1 = 0.5 * (y1 + y2)
        x2, y2 = x1 - dx, y1 - dy
        ctx.move_to(x1, y1)
        ctx.line_to(x2, y2)
        ctx.stroke()
        labels.append(
            Label(
                r"\(\Lambda\)",
                ctx.user_to_device(x2, y2),
                (1.0, 1.0),
                y_upwards=False,
            )
        )

        ls = shapely.geometry.LineString(pf_sup(u[0], v_) for v_ in v)
        p1 = ls.interpolate(0.25, normalized=True)
        x2, y2 = p1.x + dx, p1.y + dy
        ctx.move_to(p1.x, p1.y)
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
        ctx.set_source_rgb(*palette[4])
        ctx.save()
        ctx.translate(30., 17.)
        draw_frame(ctx, labels)
        ctx.restore()

    insert_labels(basename, labels)
