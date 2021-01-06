"""Helper function for the generation of 3D curves and surfaces"""
import numpy as np

COS_30_DEG = 0.5 * np.sqrt(3)
SIN_30_DEG = 0.5


def project(xyz):
    xyz = np.asarray(xyz)
    xy = np.empty(xyz.shape[:-1] + (2,), dtype=np.float64)
    xy[..., 0] = COS_30_DEG * (xyz[..., 1] - xyz[..., 0])
    xy[..., 1] = xyz[..., 2] - SIN_30_DEG * (xyz[..., 0] + xyz[..., 1])
    return xy


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

    return lambda uv: f(uv) + d(uv)[..., None] * n(uv)


class Plane:
    def __call__(self, uv):
        uv = np.asarray(uv)
        xyz = np.zeros(uv.shape[:-1] + (3,), dtype=np.float64)
        xyz[..., 0:2] = uv
        return xyz

    def __diff_u(self, uv):
        uv = np.asarray(uv)
        out = np.zeros(uv.shape[:-1] + (3,), dtype=np.float64)
        out[..., 0] = 1.0
        return out

    def __diff_v(self, uv):
        uv = np.asarray(uv)
        out = np.zeros(uv.shape[:-1] + (3,), dtype=np.float64)
        out[..., 1] = 1.0
        return out


class HyperbolicParaboloid:
    def __init__(self, a, b):
        self.a = a
        self.b = b

    def __call__(self, uv):
        uv = np.asarray(uv)
        xyz = np.empty(uv.shape[:-1] + (3,), dtype=np.float64)
        xyz[..., 0:2] = uv
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
