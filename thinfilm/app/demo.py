"""内置示范膜系：玻璃基底上的单层四分之一波长增透膜。

- 入射介质：空气 n = 1.0
- 膜层：MgF2，n = 1.38，光学厚度 lambda0/4（lambda0 = 550 nm）
- 基底：玻璃 n = 1.52

加载后应复现：550 nm 处镀膜反射率（约 1.3%）明显低于
裸玻璃单界面反射率（约 4.3%）。
"""
from __future__ import annotations

from .validation import Layer, Stack

DESIGN_WAVELENGTH = 550.0  # nm
LAYER_INDEX = 1.38         # MgF2
SUBSTRATE_INDEX = 1.52     # 玻璃
INCIDENT_INDEX = 1.0       # 空气

# 四分之一波长光学厚度对应的物理厚度 d = lambda0 / (4 n)
QUARTER_WAVE_THICKNESS = DESIGN_WAVELENGTH / (4.0 * LAYER_INDEX)

DEMO_STACK = Stack(
    incident_index=complex(INCIDENT_INDEX),
    substrate_index=complex(SUBSTRATE_INDEX),
    layers=(Layer(index=complex(LAYER_INDEX), thickness=QUARTER_WAVE_THICKNESS),),
)

# 同参数、去掉膜层的裸基底，用于对照
BARE_STACK = Stack(
    incident_index=complex(INCIDENT_INDEX),
    substrate_index=complex(SUBSTRATE_INDEX),
    layers=(),
)


def demo_payload() -> dict:
    """示范膜系的 JSON 表示，可直接作为 /api/rta、/api/spectrum 的入参。"""
    return {
        "incident_index": INCIDENT_INDEX,
        "substrate_index": SUBSTRATE_INDEX,
        "layers": [{"index": LAYER_INDEX, "thickness": QUARTER_WAVE_THICKNESS}],
    }
