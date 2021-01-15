from itertools import chain, repeat, starmap

import cairo
import numpy as np
import shapely.geometry

import stylesheet

from pycairo_utils import draw_polyline, init_context
from geometry import default_shell, Ellipse, project
from labelling import insert_labels, Label


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

    def draw_bare(self, ctx, labels):
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
        ctx.set_source_rgb(*stylesheet.color(-1))
        draw_polyline(
            ctx,
            starmap(self.pf_sup, self.Σ.difference(self.Γ).exterior.coords),
        )
        ctx.close_path()
        ctx.fill()

        # Upper face of sub-system
        ctx.set_source_rgb(*stylesheet.color(3))
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

        ctx.set_source_rgb(*stylesheet.color(-2))
        draw_lateral(FG.coords)
        draw_lateral(BC.coords)
        ctx.fill()

        ctx.set_source_rgb(*stylesheet.color(-4))
        draw_lateral(CD.coords)
        draw_lateral(GH.coords)
        ctx.fill()

        # Lateral face of sub-system
        ctx.set_source_rgb(*stylesheet.color(1))
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
        ctx.set_line_width(stylesheet.line_width("thin"))
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
        ctx.set_line_width(stylesheet.line_width("normal"))
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
        ctx.set_line_width(stylesheet.line_width("thin"))
        ctx.set_source_rgb(*stylesheet.color(4))
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
        ctx.set_line_width(stylesheet.line_width("normal"))
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
        ctx.set_source_rgb(*stylesheet.color(0))
        draw_polyline(ctx, starmap(self.pf_sup, self.Γ.exterior.coords))
        draw_polyline(ctx, starmap(self.pf_inf, self.Γ_visible.coords))
        ctx.stroke()

        # Sub-system iso-[u, v] lines and fibers
        ctx.set_line_width(stylesheet.line_width("thin"))

        for iso in (iso_u, iso_v):
            ls = iso.intersection(self.Γ)
            draw_polyline(ctx, starmap(self.pf_sup, ls.coords))
            ctx.line_to(*self.pf_inf(*ls.coords[-1]))

        for u_, v_ in (self.Γ_visible.coords[0], self.Γ_visible.coords[-1]):
            ctx.move_to(*self.pf_inf(u_, v_))
            ctx.line_to(*self.pf_sup(u_, v_))
        ctx.stroke()

        u2d = ctx.user_to_device
        ctx.set_line_width(stylesheet.line_width("thin"))
        ctx.set_source_rgb(0.0, 0.0, 0.0)

        if labels is None:
            return

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


def main():
    basename = "fig20210105175723"
    shell = default_shell(plate=True, constant_thickness=False)
    border = Ellipse(7.0, 10.0)

    u = np.linspace(-15.0, 15.0, num=51)
    v = np.linspace(-20.0, 20.0, num=51)
    t = np.linspace(0.0, 2 * np.pi, num=51)
    u_cut, v_cut = 0.0, 0.0

    drawing = ShellWithSubSystem(
        shell,
        border,
        u,
        v,
        t,
        u_cut,
        v_cut,
    )

    with cairo.PDFSurface(basename + "-bare.pdf", 1, 1) as surface:
        ctx = init_context(surface)
        labels = []
        drawing.draw_bare(ctx, labels)

    insert_labels(basename, labels)
