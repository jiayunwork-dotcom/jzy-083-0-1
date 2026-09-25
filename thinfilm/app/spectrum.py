"""波长扫描：在给定波段内逐点调用单点求解，返回光谱点列。

每个点都是同一套特征矩阵算出的真值，不做任何预设形状或插值拟合。
"""
from __future__ import annotations

from .solver import RTA, solve_point
from .validation import Stack


def scan(stack: Stack, wavelength_start: float, wavelength_end: float,
         points: int, angle_deg: float = 0.0,
         polarization: str = "unpolarized") -> list[dict]:
    """在 [wavelength_start, wavelength_end] 上均匀取 points 个波长逐点计算。"""
    if points == 1:
        wavelengths = [wavelength_start]
    else:
        step = (wavelength_end - wavelength_start) / (points - 1)
        wavelengths = [wavelength_start + i * step for i in range(points)]

    spectrum: list[dict] = []
    for wavelength in wavelengths:
        rta: RTA = solve_point(stack, wavelength, angle_deg, polarization)
        spectrum.append({"wavelength": wavelength, **rta.as_dict()})
    return spectrum
