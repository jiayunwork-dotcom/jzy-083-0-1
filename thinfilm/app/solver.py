"""单波长、单入射角下反射率 / 透射率 / 吸收率的求解。

由整层膜系特征矩阵 M 与入射侧、基底侧导纳 eta0、etas：

    B = M11 + M12 * etas
    C = M21 + M22 * etas
    r = (eta0 * B - C) / (eta0 * B + C)
    t = 2 * eta0 / (eta0 * B + C)

    R = |r|^2
    T = Re(etas) / Re(eta0) * |t|^2
    A = 1 - R - T

无膜层时 M 为单位矩阵，自动退化为单界面菲涅耳公式。
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .admittance import admittance, snell_cosines
from .matrix import layer_matrix, phase_thickness, stack_matrix
from .validation import Stack


@dataclass(frozen=True)
class RTA:
    """单一波长、角度、偏振下的结果。"""

    R: float
    T: float
    A: float

    def as_dict(self) -> dict:
        return {"R": self.R, "T": self.T, "A": self.A}


def _rta_one_polarization(stack: Stack, wavelength: float, angle_deg: float,
                          polarization: str) -> RTA:
    # 折射率序列：入射介质、各膜层、基底
    indices = [stack.incident_index]
    indices.extend(layer.index for layer in stack.layers)
    indices.append(stack.substrate_index)

    sin_theta0 = math.sin(math.radians(angle_deg))
    cosines = snell_cosines(indices, sin_theta0)

    # 各膜层特征矩阵连乘（无层时为单位矩阵）
    layer_matrices = []
    for layer, cos_t in zip(stack.layers, cosines[1:-1]):
        eta = admittance(layer.index, cos_t, polarization)
        delta = phase_thickness(layer.index, layer.thickness, cos_t, wavelength)
        layer_matrices.append(layer_matrix(delta, eta))
    m = stack_matrix(layer_matrices)
    (m11, m12), (m21, m22) = m

    eta0 = admittance(stack.incident_index, cosines[0], polarization)
    eta_s = admittance(stack.substrate_index, cosines[-1], polarization)

    b = m11 + m12 * eta_s
    c = m21 + m22 * eta_s
    denom = eta0 * b + c
    r = (eta0 * b - c) / denom
    t = (2.0 * eta0) / denom

    reflectance = abs(r) ** 2
    transmittance = (eta_s.real / eta0.real) * abs(t) ** 2
    # 数值噪声可能给出 ~-1e-17 的"吸收"，钳到 0
    absorptance = max(0.0, 1.0 - reflectance - transmittance)
    return RTA(R=reflectance, T=transmittance, A=absorptance)


def solve_point(stack: Stack, wavelength: float, angle_deg: float,
                polarization: str = "unpolarized") -> RTA:
    """单点计算；unpolarized 取 s、p 两偏振的算术平均。"""
    if polarization in ("s", "p"):
        return _rta_one_polarization(stack, wavelength, angle_deg, polarization)
    rta_s = _rta_one_polarization(stack, wavelength, angle_deg, "s")
    rta_p = _rta_one_polarization(stack, wavelength, angle_deg, "p")
    return RTA(
        R=0.5 * (rta_s.R + rta_p.R),
        T=0.5 * (rta_s.T + rta_p.T),
        A=0.5 * (rta_s.A + rta_p.A),
    )
