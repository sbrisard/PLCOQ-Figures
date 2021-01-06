import datetime
import inspect
import json
import subprocess

import PyPDF2
import cairo
import jinja2
import shapely.geometry

import numpy as np

import label

COS_30_DEG = 0.5 * np.sqrt(3)
SIN_30_DEG = 0.5

MM = 72.0 / 25.4


def parse_palette(palette):
    values = [int(palette[i : i + 2], 16) / 255 for i in range(0, len(palette), 2)]
    return list(zip(values[0::3], values[1::3], values[2::3]))


def run_jinja(basename, values):
    env = jinja2.Environment(
        variable_start_string="@",
        variable_end_string="@",
        comment_start_string="/*",
        comment_end_string="*/",
        loader=jinja2.FileSystemLoader("."),
    )

    template = env.get_template(basename + ".in")
    with open(basename, "w", encoding="utf8") as f:
        f.write(template.render(values))


def project(xyz):
    xyz = np.asarray(xyz)
    xy = np.empty(xyz.shape[:-1] + (2,), dtype=np.float64)
    xy[..., 0] = COS_30_DEG * (xyz[..., 1] - xyz[..., 0])
    xy[..., 1] = xyz[..., 2] - SIN_30_DEG * (xyz[..., 0] + xyz[..., 1])
    return xy


def draw_polyline(ctx, xy, move_to_first=True):
    xy = np.asarray(xy)
    first = 1 if move_to_first else 0
    if move_to_first:
        ctx.move_to(*xy[0])
    for x_i, y_i in xy[first:]:
        ctx.line_to(x_i, y_i)


def diff_u(f, h=1e-4):
    if hasattr(f, "__diff_u"):
        return f.__diff_u

    def f_u(uv):
        uv1 = np.copy(uv)
        uv1[..., 0] -= 0.5 * h
        uv2 = np.copy(uv)
        uv2[..., 0] += 0.5 * h
        return (f(uv2) - f(uv1)) / h

    return f_u


def diff_v(f, h=1e-4):
    if hasattr(f, "__diff_v"):
        return f.__diff_v

    def f_v(uv):
        uv1 = np.copy(uv)
        uv1[..., 1] -= 0.5 * h
        uv2 = np.copy(uv)
        uv2[..., 1] += 0.5 * h
        return (f(uv2) - f(uv1)) / h

    return f_v


def surface_normal(f, h=1e-4):
    f_u = diff_u(f, h)
    f_v = diff_v(f, h)

    def n(uv):
        a_u = f_u(uv)
        a_v = f_v(uv)
        cross = np.cross(a_u, a_v)
        norm = np.linalg.norm(cross, axis=-1, keepdims=True)
        return cross / norm

    return n


def shift_surface(f, d, n=None):
    if n is None:
        n = surface_normal(f)

    def shifted(uv):
        uv = np.asarray(uv)
        f_uv = f(uv)
        d_uv = d(uv)
        n_uv = n(uv)
        return f(uv) + d(uv)[..., None] * n(uv)

    return shifted


class Plane:
    def __call__(self, uv):
        uv = np.asarray(uv)
        xyz = np.empty(uv.shape[:-1] + (3,), dtype=np.float64)
        xyz[..., 0:-1] = uv[..., 0:2]
        xyz[..., -1] = 0.0
        return xyz

    def __diff_u(self, uv):
        uv = np.asarray(uv)
        out = np.empty(uv.shape[:-1] + (3,), dtype=np.float64)
        out[..., 0] = 1.0
        out[..., 1] = 0.0
        out[..., 2] = 0.0
        return out

    def __diff_v(self, uv):
        uv = np.asarray(uv)
        out = np.empty(uv.shape[:-1] + (3,), dtype=np.float64)
        out[..., 0] = 0.0
        out[..., 1] = 1.0
        out[..., 2] = 0.0
        return out


class HyperbolicParaboloid:
    def __init__(self, a, b):
        self.a = a
        self.b = b

    def __call__(self, uv):
        uv = np.asarray(uv)
        xyz = np.empty(uv.shape[:-1] + (3,), dtype=np.float64)
        xyz[..., 0:-1] = uv[..., 0:2]
        xyz[..., -1] = (uv[..., 0] / self.a) ** 2 - (uv[..., 1] / self.b) ** 2
        return xyz

    def __diff_u(self, uv):
        uv = np.asarray(uv)
        out = np.empty(uv.shape[:-1] + (3,), dtype=np.float64)
        out[..., 0] = 1.0
        out[..., 1] = 0.0
        out[..., 2] = 2 * (uv[..., 0] / self.a)
        return out

    def __diff_v(self, uv):
        uv = np.asarray(uv)
        out = np.empty(uv.shape[:-1] + (3,), dtype=np.float64)
        out[..., 0] = 0.0
        out[..., 1] = 1.0
        out[..., 2] = 2 * (uv[..., 1] / self.b)
        return out


class Ellipse:
    def __init__(self, a, b):
        self.a = a
        self.b = b

    def __call__(self, t):
        t = np.asarray(t)
        uv = np.empty(t.shape + (2,), dtype=np.float64)
        uv[..., 0] = self.a * np.cos(t)
        uv[..., 1] = self.b * np.sin(t)
        return uv


class Shell:
    def __init__(self, f_mid, n_mid, d_inf, d_sup):
        self.f_mid = f_mid
        self.n_mid = n_mid
        self.d_inf = d_inf
        self.d_sup = d_sup

        self.n_mid = surface_normal(f_mid)
        self.f_inf = shift_surface(f_mid, d_inf, n_mid)
        self.f_sup = shift_surface(f_mid, d_sup, n_mid)

    def __call__(self, uv, z):
        return self.f_mid(uv) + z * self.n_mid(uv)


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

        self.uv_Γ = self.border(t)

        u_min, u_max = np.min(self.u), np.max(self.u)
        v_min, v_max = np.min(self.v), np.max(self.v)
        self.uv_Σ = (
            [(u_cut, v_i) for v_i in v if v_i >= v_cut]
            + [(u_i, v_max) for u_i in u[::-1] if u_i <= u_cut]
            + [(u_min, v_i) for v_i in v[::-1]]
            + [(u_i, v_min) for u_i in u]
            + [(u_max, v_i) for v_i in v if v_i <= v_cut]
            + [(u_i, v_cut) for u_i in u[::-1] if u_i >= u_cut]
        )

    def draw(self, ctx, params):
        palette = params["color"]["category20c"]

        def pf_sup(uv):
            return project(self.shell.f_sup(uv))

        def pf_inf(uv):
            return project(self.shell.f_inf(uv))

        def pf_mid(uv):
            return project(self.shell.f_mid(uv))

        u_min, u_max, u_cut = np.min(self.u), np.max(self.u), self.u_cut
        v_min, v_max, v_cut = np.min(self.v), np.max(self.v), self.v_cut

        Γ = shapely.geometry.Polygon(self.uv_Γ)
        Σ = shapely.geometry.Polygon(self.uv_Σ)

        iso_u = np.empty((self.v.shape[0], 2), dtype=np.float64)
        iso_u[:, 0] = self.u_cut
        iso_u[:, 1] = self.v
        iso_u = shapely.geometry.LineString(iso_u)

        iso_v = np.empty((self.u.shape[0], 2), dtype=np.float64)
        iso_v[:, 0] = self.u
        iso_v[:, 1] = self.v_cut
        iso_v = shapely.geometry.LineString(iso_v)

        Γ_visible = Γ.exterior.difference(Σ)

        i = self.v >= v_cut
        AC = np.empty((np.sum(i), 2), dtype=np.float64)
        AC[:, 0] = u_cut
        AC[:, 1] = self.v[i]
        AC = shapely.geometry.LineString(AC)

        i = self.u <= u_cut
        CD = np.empty((np.sum(i), 2), dtype=np.float64)
        CD[:, 0] = self.u[i][::-1]
        CD[:, 1] = v_max
        CD = shapely.geometry.LineString(CD)

        i = self.v <= v_cut
        FG = np.empty((np.sum(i), 2), dtype=np.float64)
        FG[:, 0] = u_max
        FG[:, 1] = self.v[i]
        FG = shapely.geometry.LineString(FG)

        i = self.u >= u_cut
        GA = np.empty((np.sum(i), 2), dtype=np.float64)
        GA[:, 0] = self.u[i][::-1]
        GA[:, 1] = v_cut
        GA = shapely.geometry.LineString(GA)

        GH = GA.difference(Γ)
        BC = AC.difference(Γ)

        # Filled areas

        ## Upper face of outer system
        ctx.set_source_rgb(*palette[-1])
        draw_polyline(ctx, pf_sup(Σ.difference(Γ).exterior))
        ctx.close_path()
        ctx.fill()

        ## Upper face of sub-system
        ctx.set_source_rgb(*palette[3])
        draw_polyline(ctx, pf_sup(Γ.exterior))
        ctx.close_path()
        ctx.fill()

        ## Lateral face of outer system
        def draw_lateral(uv):
            draw_polyline(ctx, pf_inf(uv))
            draw_polyline(ctx, pf_sup(uv[::-1]), move_to_first=False)
            ctx.close_path()

        ctx.set_source_rgb(*palette[-2])
        draw_lateral(FG.coords)
        draw_lateral(BC.coords)
        ctx.fill()
        ctx.set_source_rgb(*palette[-4])
        draw_lateral(CD.coords)
        draw_lateral(GH.coords)
        ctx.fill()

        ## Lateral face of sub-system
        ctx.set_source_rgb(*palette[1])
        draw_polyline(ctx, pf_inf(Γ_visible))
        draw_polyline(ctx, pf_sup(Γ_visible)[::-1], move_to_first=False)
        ctx.close_path()
        ctx.fill()

        # Borders

        ## Iso-lines, outer system
        ctx.set_line_width(params["line width"]["thin"])
        ctx.set_source_rgb(0.0, 0.0, 0.0)

        for iso, index, bound in [(iso_u, 1, v_cut), (iso_v, 0, u_cut)]:
            mls = iso.difference(Γ)
            for ls in mls:
                if ls.coords[0][index] <= bound:
                    draw_polyline(ctx, pf_sup(ls))
        ctx.stroke()

        ## Upper and lower faces of outer system
        ctx.set_line_width(params["line width"]["normal"])
        draw_polyline(ctx, pf_sup(Σ.exterior.difference(Γ)))
        draw_polyline(ctx, pf_inf(FG))
        draw_polyline(ctx, pf_inf(GH), move_to_first=False)
        draw_polyline(ctx, pf_inf(BC))
        draw_polyline(ctx, pf_inf(CD), move_to_first=False)
        ctx.stroke()

        ## Mid surface
        ctx.set_line_width(params["line width"]["thin"])
        ctx.set_source_rgb(*palette[4])
        draw_polyline(ctx, pf_mid(FG))
        draw_polyline(ctx, pf_mid(GH), move_to_first=False)
        draw_polyline(ctx, pf_mid(Γ.exterior.difference(Σ)), move_to_first=False)
        draw_polyline(ctx, pf_mid(BC))
        draw_polyline(ctx, pf_mid(CD), move_to_first=False)
        ctx.stroke()

        ## Fibers of outer system
        ctx.set_line_width(params["line width"]["normal"])
        ctx.set_source_rgb(0.0, 0.0, 0.0)
        for uv_i in [(u_max, v_min), (u_max, v_cut), (u_cut, v_max), (u_min, v_max)]:
            ctx.move_to(*project(self.shell.f_inf(uv_i)))
            ctx.line_to(*project(self.shell.f_sup(uv_i)))
        ctx.stroke()

        ## Sub-system
        ctx.set_source_rgb(*palette[0])
        draw_polyline(ctx, pf_sup(Γ.exterior))
        draw_polyline(ctx, pf_inf(Γ_visible))
        ctx.stroke()

        ## Sub-system iso-[u, v] lines and fibers
        ctx.set_line_width(params["line width"]["thin"])

        for iso in (iso_u, iso_v):
            ls = iso.intersection(Γ)
            draw_polyline(ctx, pf_sup(ls))
            ctx.line_to(*pf_inf(ls.coords[-1]))

        for uv in (Γ_visible.coords[0], Γ_visible.coords[-1]):
            ctx.move_to(*pf_inf(uv))
            ctx.line_to(*pf_sup(uv))
        ctx.stroke()

        # Labels
        ctx.set_line_width(params["line width"]["thin"])
        ctx.set_source_rgb(0.0, 0.0, 0.0)

        labels = []
        dx, dy = 5.0, 5.0

        x1, y1 = pf_sup((u_min + dx, v_min + dy))
        x2, y2 = x1 - dx, y1 + dy
        ctx.move_to(x1, y1)
        ctx.line_to(x2, y2)

        # TODO: dirty trick -y to account for different orientations of y axis.
        labels.append((r"\(\Omega\)", ctx.user_to_device(x2, -y2), (1.0, 0.0)))

        # x1, y1 = pf_mid((u_max, 0.5 * v_min))
        # x2, y2 = x1 - dx, y1 - dx
        # values["xSigma"], values["ySigma"] = x2, y2
        # ctx.move_to(x1, y1)
        # ctx.line_to(x2, y2)
        #
        # x1, y1 = pf_mid(Γ_visible.interpolate(0.5, normalized=True))
        # x2, y2 = x1 + dx, y1 - dy
        # values["xGamma"], values["yGamma"] = x2, y2
        # ctx.move_to(x1, y1)
        # ctx.line_to(x2, y2)
        #
        # uv = Γ_visible.interpolate(0.25, normalized=True)
        # x1, y1 = 0.5 * (pf_mid(uv) + pf_inf(uv))
        # x2, y2 = x1 - dx, y1 - dy
        # values["xLambdaGamma"], values["yLambdaGamma"] = x2, y2
        # ctx.move_to(x1, y1)
        # ctx.line_to(x2, y2)
        #
        # uv = Γ.exterior.interpolate(0.33, normalized=True)
        # x1, y1 = 0.75 * pf_sup(uv)
        # x2, y2 = x1 + dx, y1
        # values["xOmegaGamma"], values["yOmegaGamma"] = x2, y2
        # ctx.move_to(x1, y1)
        # ctx.line_to(x2, y2)
        #
        ctx.stroke()
        return labels


def fig20210105175723(params, basename):
    width, height = 80.0, 60.0

    f_mid = Plane()
    # f_mid = HyperbolicParaboloid(11.0, 8.0)
    n_mid = surface_normal(f_mid)

    def d_inf(uv):
        uv = np.asarray(uv)
        return -3.0 + np.sin(0.3 * (uv[..., 0] + uv[..., 1]))

    def d_sup(uv):
        uv = np.asarray(uv)
        return 3.0 + np.cos(0.3 * (uv[..., 0] - uv[..., 1]))

    shell = Shell(f_mid, n_mid, d_inf, d_sup)

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

    with cairo.PDFSurface(basename + "-bare.pdf", width * MM, height * MM) as surface:
        ctx = cairo.Context(surface)

        ctx.scale(MM, MM)  # Default unit is mm
        ctx.translate(0.5 * width, 0.5 * height)  # Place origin at center
        ctx.scale(1.0, -1.0)  # y points upwards

        labels = drawing.draw(ctx, params)

    page = PyPDF2.PdfFileReader(basename + "-bare.pdf").getPage(0)

    print(labels)
    for latex, position, anchor in labels:
        label.insert(latex, page, position, anchor)
    writer = PyPDF2.PdfFileWriter()
    writer.addPage(page)
    with open(basename + ".pdf", "wb") as f:
        writer.write(f)

    # run_jinja(basename + ".tex", values)


if __name__ == "__main__":
    with open("cairo_params.json", "r") as f:
        params = json.load(f)

    params["color"] = {k: parse_palette(v) for k, v in params["color"].items()}
    fig20210105175723(params, "fig20210105175723")
