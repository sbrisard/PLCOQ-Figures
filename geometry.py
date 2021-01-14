"""Helper function for the generation of 3D curves and surfaces"""
import numpy as np

COS_30_DEG = 0.5 * np.sqrt(3)
SIN_30_DEG = 0.5


def project(x, y, z):
    return COS_30_DEG * (y - x), z - SIN_30_DEG * (x + y)


def diff_u(f, h=1e-4):
    if hasattr(f, "__diff_u"):
        return f.__diff_u

    def f_u(u, v):
        x1, y1, z1 = f(u, v)
        x2, y2, z2 = f(u + h, v)
        return (x2 - x1) / h, (y2 - y1) / h, (z2 - z1) / h

    return f_u


def diff_v(f, h=1e-4):
    if hasattr(f, "__diff_v"):
        return f.__diff_v

    def f_v(u, v):
        x1, y1, z1 = f(u, v)
        x2, y2, z2 = f(u, v + h)
        return (x2 - x1) / h, (y2 - y1) / h, (z2 - z1) / h

    return f_v


def surface_normal(f, h=1e-4):
    f_u = diff_u(f, h)
    f_v = diff_v(f, h)

    def n(u, v):
        a_u = f_u(u, v)
        a_v = f_v(u, v)
        cross = np.cross(a_u, a_v)
        norm = np.linalg.norm(cross, axis=-1, keepdims=True)
        return cross / norm

    return n


def shift_surface(f, d, n=None):
    if n is None:
        n = surface_normal(f)
    return lambda u, v: f(u, v) + d(u, v) * n(u, v)


class Plane:
    def __call__(self, u, v):
        return u, v, 0.0

    def __diff_u(self, uv):
        return 1.0, 0.0, 0.0

    def __diff_v(self, uv):
        return 0.0, 1.0, 0.0


class HyperbolicParaboloid:
    def __init__(self, a, b):
        self.a = a
        self.b = b

    def __call__(self, u, v):
        return u, v, (u / self.a) ** 2 - (v / self.b) ** 2

    def __diff_u(self, u, v):
        return 1.0, 0.0, 2 * u / self.a

    def __diff_v(self, u, v):
        return 0.0, 1.0, 2 * v / self.b


class Ellipse:
    def __init__(self, a, b):
        self.a = a
        self.b = b

    def __call__(self, t):
        return self.a * np.cos(t), self.b * np.sin(t)


class Shell:
    def __init__(self, f_mid, n_mid, d_inf, d_sup):
        self.f_mid = f_mid
        self.n_mid = n_mid
        self.d_inf = d_inf
        self.d_sup = d_sup

        self.n_mid = surface_normal(f_mid)
        self.f_inf = shift_surface(f_mid, d_inf, n_mid)
        self.f_sup = shift_surface(f_mid, d_sup, n_mid)


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
