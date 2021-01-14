import json

from itertools import chain, repeat, starmap

import PyPDF2
import cairo
import shapely.geometry

import numpy as np

import labelling

from pycairo_utils import draw_line, draw_polyline, init_context
from geometry import *
from labelling import Label, insert_labels

MM = 72.0 / 25.4


def parse_palette(palette):
    values = [int(palette[i : i + 2], 16) / 255 for i in range(0, len(palette), 2)]
    return list(zip(values[0::3], values[1::3], values[2::3]))


class ShellWithSubSystem:
    def __init__(self, shell, border, u, v, t, u_cut, v_cut):
        """Shell is cut along two lines: ``u = u_cut`` and ``v = v_cut``.

        It is assumed that the visible sector is ``u ≥ u_cut`` and ``v ≥ v_cut``.

        """
        self.shell = shell
        self.border = border
        self.u = np.asarray(u)
        self.v = np.asarray(v)
        self.t = np.asarray(t)
        self.u_cut = u_cut
        self.v_cut = v_cut

        self.Γ = shapely.geometry.Polygon(self.border(t_) for t_ in t)

        self.u_min, self.u_max = np.min(self.u), np.max(self.u)
        self.v_min, self.v_max = np.min(self.v), np.max(self.v)
        u_le = u <= u_cut
        u_ge = u >= u_cut
        v_le = v <= v_cut
        v_ge = v >= v_cut
        self.Σ = shapely.geometry.Polygon(
            chain(
                zip(repeat(u_cut), v[v_ge]),
                zip(u[u_le][::-1], repeat(self.v_max)),
                zip(repeat(self.u_min), v[::-1]),
                zip(u, repeat(self.v_min)),
                zip(repeat(self.u_max), v[v_le]),
                zip(u[u_ge][::-1], repeat(v_cut)),
            )
        )

        self.Γ_visible = self.Γ.exterior.difference(self.Σ)

    def pf_sup(self, u, v):
        return project(*self.shell.f_sup(u, v))

    def pf_inf(self, u, v):
        return project(*self.shell.f_inf(u, v))

    def pf_mid(self, u, v):
        return project(*self.shell.f_mid(u, v))

    def draw_bare(self, ctx, labels, params):
        palette = params["color"]["category20c"]

        iso_u = shapely.geometry.LineString(zip(repeat(self.u_cut), self.v))
        iso_v = shapely.geometry.LineString(zip(self.u, repeat(self.v_cut)))

        i = self.v >= self.v_cut
        AC = shapely.geometry.LineString(zip(repeat(self.u_cut), self.v[i]))

        i = self.u <= self.u_cut
        CD = shapely.geometry.LineString(zip(self.u[i][::-1], repeat(self.v_max)))

        i = self.v <= self.v_cut
        FG = shapely.geometry.LineString(zip(repeat(self.u_max), self.v[i]))

        i = self.u >= self.u_cut
        GA = shapely.geometry.LineString(zip(self.u[i][::-1], repeat(self.v_cut)))

        GH = GA.difference(self.Γ)
        BC = AC.difference(self.Γ)

        # Upper face of outer system
        ctx.set_source_rgb(*palette[-1])
        draw_polyline(
            ctx,
            starmap(self.pf_sup, self.Σ.difference(self.Γ).exterior.coords),
        )
        ctx.close_path()
        ctx.fill()

        # Upper face of sub-system
        ctx.set_source_rgb(*palette[3])
        draw_polyline(ctx, starmap(self.pf_sup, self.Γ.exterior.coords))
        ctx.close_path()
        ctx.fill()

        # Lateral face of outer system
        def draw_lateral(uv):
            points = chain(starmap(self.pf_inf, uv), starmap(self.pf_sup, uv[::-1]))
            ctx.move_to(*next(points))
            for x, y in points:
                ctx.line_to(x, y)
            ctx.close_path()

        ctx.set_source_rgb(*palette[-2])
        draw_lateral(FG.coords)
        draw_lateral(BC.coords)
        ctx.fill()

        ctx.set_source_rgb(*palette[-4])
        draw_lateral(CD.coords)
        draw_lateral(GH.coords)
        ctx.fill()

        # Lateral face of sub-system
        ctx.set_source_rgb(*palette[1])
        points = chain(
            starmap(self.pf_inf, self.Γ_visible.coords),
            starmap(self.pf_sup, self.Γ_visible.coords[::-1]),
        )
        ctx.move_to(*next(points))
        for x, y in points:
            ctx.line_to(x, y)
        ctx.close_path()
        ctx.fill()

        # Iso-lines, outer system
        ctx.set_line_width(params["line width"]["thin"])
        ctx.set_source_rgb(0.0, 0.0, 0.0)

        for iso, index, bound in [(iso_u, 1, self.v_cut), (iso_v, 0, self.u_cut)]:
            mls = iso.difference(self.Γ)
            for ls in mls:
                if ls.coords[0][index] <= bound:
                    points = starmap(self.pf_sup, ls.coords)
                    ctx.move_to(*next(points))
                    for x, y in points:
                        ctx.line_to(x, y)
        ctx.stroke()

        # Upper and lower faces of outer system
        ctx.set_line_width(params["line width"]["normal"])
        points = starmap(self.pf_sup, self.Σ.exterior.difference(self.Γ).coords)
        ctx.move_to(*next(points))
        for x, y in points:
            ctx.line_to(x, y)
        points = chain(starmap(self.pf_inf, FG.coords), starmap(self.pf_inf, GH.coords))
        ctx.move_to(*next(points))
        for x, y in points:
            ctx.line_to(x, y)
        points = chain(starmap(self.pf_inf, BC.coords), starmap(self.pf_inf, CD.coords))
        ctx.move_to(*next(points))
        for x, y in points:
            ctx.line_to(x, y)
        ctx.stroke()

        # Mid surface
        ctx.set_line_width(params["line width"]["thin"])
        ctx.set_source_rgb(*palette[4])
        points = starmap(
            self.pf_mid,
            chain(FG.coords, GH.coords, self.Γ.exterior.difference(self.Σ).coords),
        )
        ctx.move_to(*next(points))
        for x, y in points:
            ctx.line_to(x, y)
        points = starmap(self.pf_mid, chain(BC.coords, CD.coords))
        ctx.move_to(*next(points))
        for x, y in points:
            ctx.line_to(x, y)
        ctx.stroke()

        # Fibers of outer system
        ctx.set_line_width(params["line width"]["normal"])
        ctx.set_source_rgb(0.0, 0.0, 0.0)
        for u_, v_ in [
            (self.u_max, self.v_min),
            (self.u_max, self.v_cut),
            (self.u_cut, self.v_max),
            (self.u_min, self.v_max),
        ]:
            ctx.move_to(*self.pf_inf(u_, v_))
            ctx.line_to(*self.pf_sup(u_, v_))
        ctx.stroke()

        # Sub-system
        ctx.set_source_rgb(*palette[0])
        draw_polyline(ctx, starmap(self.pf_sup, self.Γ.exterior.coords))
        draw_polyline(ctx, starmap(self.pf_inf, self.Γ_visible.coords))
        ctx.stroke()

        # Sub-system iso-[u, v] lines and fibers
        ctx.set_line_width(params["line width"]["thin"])

        for iso in (iso_u, iso_v):
            ls = iso.intersection(self.Γ)
            draw_polyline(ctx, starmap(self.pf_sup, ls.coords))
            ctx.line_to(*self.pf_inf(*ls.coords[-1]))

        for u_, v_ in (self.Γ_visible.coords[0], self.Γ_visible.coords[-1]):
            ctx.move_to(*self.pf_inf(u_, v_))
            ctx.line_to(*self.pf_sup(u_, v_))
        ctx.stroke()

        u2d = ctx.user_to_device
        ctx.set_line_width(params["line width"]["thin"])
        ctx.set_source_rgb(0.0, 0.0, 0.0)

        dx, dy = 5.0, 5.0

        x1, y1 = self.pf_sup(self.u_min + dx, self.v_min + dy)
        x2, y2 = x1 - dx, y1 + dy
        ctx.move_to(x1, y1)
        ctx.line_to(x2, y2)
        labels.append(Label(r"\(\Omega\)", u2d(x2, y2), (1.0, 0.0), False))

        x1, y1 = self.pf_mid(self.u_max, 0.5 * self.v_min)
        x2, y2 = x1 - dx, y1 - dx
        ctx.move_to(x1, y1)
        ctx.line_to(x2, y2)
        labels.append(Label(r"\(\Sigma\)", u2d(x2, y2), (1.0, 1.0), False))

        uv = self.Γ_visible.interpolate(0.5, normalized=True)
        x1, y1 = self.pf_mid(uv.x, uv.y)
        x2, y2 = x1 + dx, y1 - dy
        ctx.move_to(x1, y1)
        ctx.line_to(x2, y2)
        labels.append(Label(r"\(\Gamma\)", u2d(x2, y2), (0.0, 1.0), False))

        uv = self.Γ_visible.interpolate(0.25, normalized=True)
        x1a, y1a = self.pf_mid(uv.x, uv.y)
        x1b, y1b = self.pf_inf(uv.x, uv.y)
        x1, y1 = 0.5 * (x1a + x1b), 0.5 * (y1a + y1b)
        x2, y2 = x1 - dx, y1 - dy
        ctx.move_to(x1, y1)
        ctx.line_to(x2, y2)
        labels.append(Label(r"\(\Lambda(\Gamma)\)", u2d(x2, y2), (1.0, 1.0), False))

        uv = self.Γ.exterior.interpolate(0.33, normalized=True)
        x1, y1 = self.pf_sup(uv.x, uv.y)
        x1, y1 = 0.75 * x1, 0.75 * y1
        x2, y2 = x1 + dx, y1
        ctx.move_to(x1, y1)
        ctx.line_to(x2, y2)
        labels.append(Label(r"\(\Omega(\Gamma)\)", u2d(x2, y2), (0.0, 0.5), False))

        ctx.stroke()
        return labels

    def draw(self, width, height, basename, params):
        with cairo.PDFSurface(basename + "-bare.pdf", 1, 1) as surface:
            ctx = init_context(surface, width, height)
            labels = []
            self.draw_bare(ctx, labels, params)

        insert_labels(basename, labels)


def default_shell(plate=True, constant_thickness=True):
    f_mid = Plane() if plate else HyperbolicParaboloid(11.0, 8.0)
    n_mid = surface_normal(f_mid)

    if constant_thickness:
        d_inf = lambda u, v: -3.0
        d_sup = lambda u, v: 3.0
    else:
        d_inf = lambda u, v: -3.0 + np.sin(0.3 * (u + v))
        d_sup = lambda u, v: 3.0 + np.cos(0.3 * (u - v))

    return Shell(f_mid, n_mid, d_inf, d_sup)


def fig20210113144259(params):
    basename = "fig20210113144259"
    width, height = 80.0, 60.0
    shell = default_shell(plate=True, constant_thickness=False)

    u = np.linspace(-15.0, 15.0, num=51)
    v = np.linspace(-20.0, 20.0, num=51)

    u_cut = 0.0

    pf_sup = lambda u, v: project(*shell.f_sup(u, v))
    pf_inf = lambda u, v: project(*shell.f_inf(u, v))
    pf_mid = lambda u, v: project(*shell.f_mid(u, v))

    palette = params["color"]["category20c"]

    with cairo.PDFSurface(basename + "-bare.pdf", 1, 1) as surface:
        ctx = init_context(surface, width, height)
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

    insert_labels(basename, labels)


def fig20210105175723(params, basename):
    width, height = 80.0, 60.0
    shell = default_shell(plate=True, constant_thickness=False)

    border = Ellipse(7.0, 10.0)

    u_min, u_max, u_cut = -15.0, 15.0, 0.0
    v_min, v_max, v_cut = -20.0, 20.0, 0.0

    drawing = ShellWithSubSystem(
        shell,
        border,
        np.linspace(u_min, u_max, num=51),
        np.linspace(v_min, v_max, num=51),
        np.linspace(0.0, 2 * np.pi, num=51),
        u_cut,
        v_cut,
    )
    drawing.draw(width, height, basename, params)


def main():
    with open("cairo_params.json", "r") as f:
        params = json.load(f)

    params["color"] = {k: parse_palette(v) for k, v in params["color"].items()}
    fig20210105175723(params, "fig20210105175723")

    fig20210113144259(params)


if __name__ == "__main__":
    main()
