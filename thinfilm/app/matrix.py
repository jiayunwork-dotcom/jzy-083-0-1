"""复数特征矩阵的构造与连乘。

场的时间因子取 exp(-iωt)，折射率 N = n + ik（k>0 表示吸收），
此时每层均匀介质对应二阶特征矩阵：

    M_j = [[cos(delta_j),  -i sin(delta_j) / eta_j],
           [-i eta_j sin(delta_j),  cos(delta_j)]]

其中 delta_j 为相位厚度，eta_j 为该层在当前偏振下的等效光学导纳。
该矩阵把入射侧界面的切向场映到基底侧界面：[E0; H0] = M [Es; Hs]。
整层膜系的特征矩阵为各层矩阵按入射顺序连乘。矩阵元一律为复数，
折射率带虚部（吸收）时无需任何特判即可自然成立。
"""
from __future__ import annotations

import cmath
import math

# 2x2 复数矩阵，按 ((m11, m12), (m21, m22)) 存放
Matrix2x2 = tuple[tuple[complex, complex], tuple[complex, complex]]

IDENTITY: Matrix2x2 = ((1.0 + 0j, 0.0 + 0j), (0.0 + 0j, 1.0 + 0j))


def phase_thickness(n: complex, thickness: float, cos_theta: complex,
                    wavelength: float) -> complex:
    """相位厚度 delta = (2*pi/lambda) * N * d * cos(theta)。

    cos(theta) 因子绝不可省略：漏掉它斜入射下光谱峰位会整体漂移。
    """
    return 2.0 * math.pi * n * thickness * cos_theta / wavelength


def layer_matrix(delta: complex, eta: complex) -> Matrix2x2:
    """单层特征矩阵，由相位厚度和等效光学导纳唯一确定。"""
    cos_d = cmath.cos(delta)
    sin_d = cmath.sin(delta)
    return (
        (cos_d, -1j * sin_d / eta),
        (-1j * eta * sin_d, cos_d),
    )


def matmul(a: Matrix2x2, b: Matrix2x2) -> Matrix2x2:
    """2x2 复数矩阵乘法 a @ b。"""
    (a11, a12), (a21, a22) = a
    (b11, b12), (b21, b22) = b
    return (
        (a11 * b11 + a12 * b21, a11 * b12 + a12 * b22),
        (a21 * b11 + a22 * b21, a21 * b12 + a22 * b22),
    )


def stack_matrix(layers: list[Matrix2x2]) -> Matrix2x2:
    """按入射顺序连乘各层特征矩阵；无层时退化为单位矩阵。"""
    result = IDENTITY
    for m in layers:
        result = matmul(result, m)
    return result
