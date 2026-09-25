"""光学导纳与 s/p 偏振处理。

采用自由空间归一化的光学导纳：
- s 偏振（TE）：eta = N * cos(theta)
- p 偏振（TM）：eta = N / cos(theta)

两种偏振的导纳表达式相互独立，绝不混用。折射角由 Snell 定律
在复数域给出（吸收介质中 cos(theta) 为复数）。
"""
from __future__ import annotations

import cmath

POLARIZATIONS = ("s", "p", "unpolarized")


def snell_cosines(indices: list[complex], sin_theta0: complex) -> list[complex]:
    """按 Snell 定律逐层求折射角余弦（复数）。

    indices[0] 为入射介质折射率，sin_theta0 为入射角正弦。
    返回与 indices 等长的 cos(theta_j) 列表；取实部非负的根，
    保证吸收介质中能流方向正确。
    """
    n0 = indices[0]
    cosines: list[complex] = []
    for n in indices:
        sin_t = n0 * sin_theta0 / n
        cos_t = cmath.sqrt(1.0 - sin_t * sin_t)
        if cos_t.real < 0.0:
            cos_t = -cos_t
        cosines.append(cos_t)
    return cosines


def admittance(n: complex, cos_theta: complex, polarization: str) -> complex:
    """当前偏振下的等效光学导纳。

    s 偏振与 p 偏振各有固定表达式，必须严格分开。
    """
    if polarization == "s":
        return n * cos_theta
    if polarization == "p":
        return n / cos_theta
    raise ValueError(f"未知偏振态: {polarization!r}（应为 's' 或 'p'）")
