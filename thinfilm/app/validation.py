"""输入合法性校验与膜系解析。

所有非法输入（层厚为负、折射率实部非正、波长非正、入射角不小于
九十度等）在进入任何矩阵计算之前就在这里被拒绝，并以结构化错误
返回给接口层。
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field


class ValidationError(ValueError):
    """输入非法；message 面向调用方，field 指出出错字段。"""

    def __init__(self, message: str, field: str | None = None):
        super().__init__(message)
        self.message = message
        self.field = field


@dataclass(frozen=True)
class Layer:
    """单层膜：复折射率 n = n_real + i*k（k>0 表示吸收），物理厚度 nm。"""

    index: complex
    thickness: float


@dataclass(frozen=True)
class Stack:
    """完整膜系：入射介质 / 若干膜层 / 基底。"""

    incident_index: complex
    substrate_index: complex
    layers: tuple[Layer, ...] = field(default_factory=tuple)


def _parse_index(value: object, field_name: str) -> complex:
    """折射率接受三种写法：实数、"n+ik" 形式的 [n, k]、{"n":..,"k":..}。"""
    if isinstance(value, bool):
        raise ValidationError(f"{field_name} 必须是数值或对象", field_name)
    if isinstance(value, (int, float)):
        n_complex = complex(float(value), 0.0)
    elif isinstance(value, (list, tuple)) and len(value) == 2:
        n_complex = complex(float(value[0]), float(value[1]))
    elif isinstance(value, dict):
        n_complex = complex(float(value.get("n", 0.0)), float(value.get("k", 0.0)))
    else:
        raise ValidationError(
            f"{field_name} 无法解析为折射率（支持数值、[n,k] 或 {{n,k}}）",
            field_name,
        )
    if not (math.isfinite(n_complex.real) and math.isfinite(n_complex.imag)):
        raise ValidationError(f"{field_name} 必须是有限数值", field_name)
    if n_complex.real <= 0.0:
        raise ValidationError(
            f"{field_name} 的实部必须为正数，得到 {n_complex.real}", field_name
        )
    if n_complex.imag < 0.0:
        raise ValidationError(
            f"{field_name} 的虚部（消光系数 k）不能为负，得到 {n_complex.imag}",
            field_name,
        )
    return n_complex


def _parse_layer(raw: object, position: int) -> Layer:
    field_name = f"layers[{position}]"
    if not isinstance(raw, dict):
        raise ValidationError(f"{field_name} 必须是对象", field_name)
    if "index" not in raw:
        raise ValidationError(f"{field_name} 缺少 index（折射率）", field_name)
    if "thickness" not in raw:
        raise ValidationError(f"{field_name} 缺少 thickness（物理厚度, nm）", field_name)
    index = _parse_index(raw["index"], f"{field_name}.index")
    try:
        thickness = float(raw["thickness"])
    except (TypeError, ValueError):
        raise ValidationError(
            f"{field_name}.thickness 必须是数值", f"{field_name}.thickness"
        ) from None
    if not math.isfinite(thickness):
        raise ValidationError(
            f"{field_name}.thickness 必须是有限数值", f"{field_name}.thickness"
        )
    if thickness < 0.0:
        raise ValidationError(
            f"{field_name}.thickness 不能为负，得到 {thickness}",
            f"{field_name}.thickness",
        )
    return Layer(index=index, thickness=thickness)


def parse_stack(payload: dict) -> Stack:
    """从请求 JSON 解析并校验膜系；非法时抛 ValidationError。"""
    if not isinstance(payload, dict):
        raise ValidationError("请求体必须是 JSON 对象")
    for key in ("incident_index", "substrate_index"):
        if key not in payload:
            raise ValidationError(f"缺少必填字段 {key}", key)
    incident = _parse_index(payload["incident_index"], "incident_index")
    substrate = _parse_index(payload["substrate_index"], "substrate_index")
    raw_layers = payload.get("layers", [])
    if not isinstance(raw_layers, list):
        raise ValidationError("layers 必须是数组", "layers")
    layers = tuple(_parse_layer(raw, i) for i, raw in enumerate(raw_layers))
    return Stack(incident_index=incident, substrate_index=substrate, layers=layers)


def parse_wavelength(value: object, field_name: str = "wavelength") -> float:
    """波长（nm），必须为正。"""
    try:
        wavelength = float(value)
    except (TypeError, ValueError):
        raise ValidationError(f"{field_name} 必须是数值", field_name) from None
    if not math.isfinite(wavelength) or wavelength <= 0.0:
        raise ValidationError(
            f"{field_name} 必须为正数，得到 {value}", field_name
        )
    return wavelength


def parse_angle(value: object, field_name: str = "angle_deg") -> float:
    """入射角（度），必须在 [0, 90) 内。"""
    try:
        angle = float(value)
    except (TypeError, ValueError):
        raise ValidationError(f"{field_name} 必须是数值", field_name) from None
    if not math.isfinite(angle) or not (0.0 <= angle < 90.0):
        raise ValidationError(
            f"{field_name} 必须在 [0, 90) 度内，得到 {value}", field_name
        )
    return angle


def parse_polarization(value: object) -> str:
    """偏振态：s / p / unpolarized，缺省 unpolarized。"""
    if value is None:
        return "unpolarized"
    if value not in ("s", "p", "unpolarized"):
        raise ValidationError(
            f"polarization 必须是 's'、'p' 或 'unpolarized'，得到 {value!r}",
            "polarization",
        )
    return value


def parse_points(value: object, field_name: str = "points") -> int:
    """光谱扫描采样点数，至少为 2。"""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(f"{field_name} 必须是整数", field_name)
    if value < 2:
        raise ValidationError(f"{field_name} 至少为 2，得到 {value}", field_name)
    return value
