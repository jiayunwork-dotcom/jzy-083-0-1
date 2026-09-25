"""HTTP 接口层测试：两个计算口子、示范膜系、错误处理与并发隔离。"""
import concurrent.futures

import pytest

from app.demo import DESIGN_WAVELENGTH, demo_payload
from app.server import create_app


@pytest.fixture()
def client():
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def test_rta_endpoint_single_point(client):
    payload = {**demo_payload(), "wavelength": DESIGN_WAVELENGTH,
               "angle_deg": 0.0, "polarization": "s"}
    resp = client.post("/api/rta", json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    assert set(("R", "T", "A")) <= set(data)
    assert data["R"] + data["T"] == pytest.approx(1.0, abs=1e-9)
    assert data["R"] < 0.02  # 设计波长处增透生效


def test_spectrum_endpoint_returns_real_scan(client):
    payload = {**demo_payload(), "wavelength_start": 400.0,
               "wavelength_end": 700.0, "points": 301, "angle_deg": 0.0}
    resp = client.post("/api/spectrum", json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    points = data["points"]
    assert len(points) == 301
    # 每点都满足能量守恒（真值，不是预设形状）
    for p in points:
        assert p["R"] + p["T"] == pytest.approx(1.0, abs=1e-9)
    # 极小值落在设计波长附近
    best = min(points, key=lambda p: p["R"])
    assert abs(best["wavelength"] - DESIGN_WAVELENGTH) < 2.0
    # 曲线两端反射率高于极小值（确为随波长变化的光谱）
    assert points[0]["R"] > best["R"]
    assert points[-1]["R"] > best["R"]


def test_demo_endpoint_reproduces_ar_relation(client):
    resp = client.get("/api/demo")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["coated_R"] < data["bare_substrate_R"]
    assert data["bare_substrate_R"] == pytest.approx(0.0426, abs=1e-3)


def test_invalid_inputs_return_structured_400(client):
    base = demo_payload()
    bad_requests = [
        {**base, "wavelength": -550.0},                       # 波长非正
        {**base, "wavelength": 550.0, "angle_deg": 90.0},     # 入射角 >= 90
        {**base, "wavelength": 550.0, "angle_deg": 120.0},
        {**base, "wavelength": 550.0,
         "layers": [{"index": 1.38, "thickness": -5.0}]},     # 负层厚
        {**base, "wavelength": 550.0, "incident_index": 0.0},  # 折射率实部非正
        {**base, "wavelength": 550.0, "polarization": "x"},    # 非法偏振
    ]
    for payload in bad_requests:
        resp = client.post("/api/rta", json=payload)
        assert resp.status_code == 400, payload
        err = resp.get_json()["error"]
        assert err["type"] == "validation_error"
        assert err["message"]


def test_spectrum_rejects_bad_range(client):
    payload = {**demo_payload(), "wavelength_start": 700.0,
               "wavelength_end": 400.0, "points": 100}
    resp = client.post("/api/spectrum", json=payload)
    assert resp.status_code == 400
    assert resp.get_json()["error"]["field"] == "wavelength_end"


def test_concurrent_requests_are_isolated(client):
    """多路请求并发：不同膜系/角度的结果互不串扰。"""
    def query(angle):
        payload = {**demo_payload(), "wavelength": DESIGN_WAVELENGTH,
                   "angle_deg": angle, "polarization": "s"}
        resp = client.post("/api/rta", json=payload)
        assert resp.status_code == 200
        return resp.get_json()

    angles = [0.0, 15.0, 30.0, 45.0, 60.0, 75.0] * 3
    with concurrent.futures.ThreadPoolExecutor(max_workers=9) as pool:
        results = list(pool.map(query, angles))

    for angle, data in zip(angles, results):
        assert data["angle_deg"] == pytest.approx(angle)
        assert data["R"] + data["T"] == pytest.approx(1.0, abs=1e-9)
    # 同角度多次并发结果完全一致（无共享状态污染）
    by_angle = {}
    for angle, data in zip(angles, results):
        by_angle.setdefault(angle, set()).add(data["R"])
    assert all(len(v) == 1 for v in by_angle.values())
