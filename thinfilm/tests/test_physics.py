"""物理正确性基准测试：特征矩阵法的核心不变量与经典极限。"""
import math

import pytest

from app.demo import BARE_STACK, DEMO_STACK, DESIGN_WAVELENGTH
from app.solver import solve_point
from app.spectrum import scan
from app.validation import Layer, Stack, ValidationError, parse_stack

# 一个无吸收的三层膜系，用于能量守恒检查
LOSSLESS_STACK = Stack(
    incident_index=1.0 + 0j,
    substrate_index=1.52 + 0j,
    layers=(
        Layer(index=1.38 + 0j, thickness=99.6),
        Layer(index=2.3 + 0j, thickness=120.0),
        Layer(index=1.45 + 0j, thickness=210.0),
    ),
)

# 带吸收（折射率含虚部）的膜系
ABSORBING_STACK = Stack(
    incident_index=1.0 + 0j,
    substrate_index=1.52 + 0j,
    layers=(
        Layer(index=2.0 + 0.4j, thickness=80.0),
        Layer(index=1.45 + 0j, thickness=150.0),
    ),
)


@pytest.mark.parametrize("wavelength", [400.0, 550.0, 700.0, 1064.0])
@pytest.mark.parametrize("angle", [0.0, 30.0, 60.0, 80.0])
@pytest.mark.parametrize("polarization", ["s", "p", "unpolarized"])
def test_lossless_energy_conservation(wavelength, angle, polarization):
    """无吸收时任意波长、角度、偏振下 R + T == 1。"""
    rta = solve_point(LOSSLESS_STACK, wavelength, angle, polarization)
    assert rta.R + rta.T == pytest.approx(1.0, abs=1e-9)
    assert rta.A == pytest.approx(0.0, abs=1e-9)


@pytest.mark.parametrize("wavelength", [450.0, 633.0, 900.0])
@pytest.mark.parametrize("polarization", ["s", "p"])
def test_absorbing_energy_budget(wavelength, polarization):
    """有吸收时 R + A + T == 1，且 A >= 0、R + T < 1。"""
    rta = solve_point(ABSORBING_STACK, wavelength, 25.0, polarization)
    assert rta.R + rta.A + rta.T == pytest.approx(1.0, abs=1e-9)
    assert rta.A >= 0.0
    assert rta.A > 1e-6  # 该膜系确实在吸收
    assert rta.R + rta.T < 1.0


def _fresnel_bare(n0, ns, angle_deg, polarization):
    """单界面菲涅耳反射率的独立解析计算（不经过特征矩阵）。"""
    theta0 = math.radians(angle_deg)
    sin_t = n0 * math.sin(theta0) / ns
    cos0, cos_t = math.cos(theta0), math.sqrt(1.0 - sin_t**2)
    if polarization == "s":
        r = (n0 * cos0 - ns * cos_t) / (n0 * cos0 + ns * cos_t)
    else:
        r = (ns * cos0 - n0 * cos_t) / (ns * cos0 + n0 * cos_t)
    return abs(r) ** 2


@pytest.mark.parametrize("angle", [0.0, 20.0, 45.0, 70.0])
@pytest.mark.parametrize("polarization", ["s", "p"])
def test_no_layers_reduces_to_single_interface_fresnel(angle, polarization):
    """无膜层时退化为入射介质与基底之间的单界面菲涅耳反射。"""
    rta = solve_point(BARE_STACK, 550.0, angle, polarization)
    expected = _fresnel_bare(1.0, 1.52, angle, polarization)
    assert rta.R == pytest.approx(expected, abs=1e-12)


def test_quarter_wave_ar_beats_bare_substrate():
    """四分之一波长增透膜在设计波长处反射率明显低于裸基底。"""
    coated = solve_point(DEMO_STACK, DESIGN_WAVELENGTH, 0.0)
    bare = solve_point(BARE_STACK, DESIGN_WAVELENGTH, 0.0)
    assert coated.R < 0.4 * bare.R  # 约 1.3% vs 约 4.3%
    assert coated.R < 0.02


def test_half_wave_layer_loses_ar_effect():
    """厚度改为半波（光学厚度 lambda/2）后，设计波长处增透消失。"""
    half_wave = Stack(
        incident_index=DEMO_STACK.incident_index,
        substrate_index=DEMO_STACK.substrate_index,
        layers=(Layer(DEMO_STACK.layers[0].index,
                      2.0 * DEMO_STACK.layers[0].thickness),),
    )
    coated = solve_point(half_wave, DESIGN_WAVELENGTH, 0.0)
    bare = solve_point(BARE_STACK, DESIGN_WAVELENGTH, 0.0)
    assert coated.R == pytest.approx(bare.R, abs=1e-9)


def test_reflectance_rises_toward_grazing_incidence():
    """只把入射角往掠射方向加大，反射率升高（菲涅耳 s 偏振单调）。"""
    angles = [0.0, 30.0, 50.0, 70.0, 85.0]
    rs = [solve_point(BARE_STACK, 633.0, a, "s").R for a in angles]
    for low, high in zip(rs, rs[1:]):
        assert high > low
    # 非偏振光在接近掠射时同样远高于正入射
    r0 = solve_point(BARE_STACK, 633.0, 0.0, "unpolarized").R
    r85 = solve_point(BARE_STACK, 633.0, 85.0, "unpolarized").R
    assert r85 > 5.0 * r0


def test_phase_thickness_includes_cosine_factor():
    """相位厚度含 cos(theta) 因子：斜入射下光谱极小值蓝移。

    若漏掉 cos 因子，峰位不随角度移动，本测试即失败。
    """
    def min_wavelength(angle):
        points = scan(DEMO_STACK, 400.0, 700.0, 601, angle, "s")
        return min(points, key=lambda p: p["R"])["wavelength"]

    wl_normal = min_wavelength(0.0)
    wl_oblique = min_wavelength(50.0)
    assert wl_normal == pytest.approx(DESIGN_WAVELENGTH, abs=2.0)
    # 斜入射时极小值明显移向短波（50 度约移 60 nm 以上）
    assert wl_oblique < wl_normal - 50.0


def test_invalid_inputs_rejected_before_computation():
    """非法膜系与参数在计算前就被拒绝。"""
    base = {"incident_index": 1.0, "substrate_index": 1.52, "layers": []}
    bad_payloads = [
        {**base, "layers": [{"index": 1.38, "thickness": -10.0}]},   # 负层厚
        {**base, "incident_index": -1.0},                            # 折射率实部非正
        {**base, "incident_index": 0.0},
        {**base, "substrate_index": {"n": -1.5, "k": 0.0}},
        {**base, "layers": [{"index": [1.38, -0.1], "thickness": 10}]},  # k<0
    ]
    for payload in bad_payloads:
        with pytest.raises(ValidationError):
            parse_stack(payload)
