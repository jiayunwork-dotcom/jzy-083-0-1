"""Flask HTTP 接口层。

只负责请求解析、调用 solver/spectrum、组织 JSON 响应；
所有矩阵运算都在下层模块完成。请求之间不共享任何中间量，
每次调用独立构造矩阵，可安全并发。

接口：
- GET  /health          存活探针
- GET  /api/demo        示范膜系及其在设计波长处的核算结果
- POST /api/rta         单点：膜系 + 波长 + 入射角 -> R/T/A
- POST /api/spectrum    扫描：膜系 + 波段 -> 反射率光谱点列
"""
from __future__ import annotations

from flask import Flask, jsonify, request

from . import demo, spectrum
from .solver import solve_point
from .validation import (
    ValidationError,
    parse_angle,
    parse_points,
    parse_polarization,
    parse_stack,
    parse_wavelength,
)


def create_app() -> Flask:
    app = Flask(__name__)

    @app.errorhandler(ValidationError)
    def handle_validation_error(err: ValidationError):
        body = {"error": {"type": "validation_error", "message": err.message}}
        if err.field is not None:
            body["error"]["field"] = err.field
        return jsonify(body), 400

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.get("/api/demo")
    def get_demo():
        """示范膜系：设计波长处镀膜与裸基底的反射率对照。"""
        coated = solve_point(demo.DEMO_STACK, demo.DESIGN_WAVELENGTH, 0.0)
        bare = solve_point(demo.BARE_STACK, demo.DESIGN_WAVELENGTH, 0.0)
        return jsonify({
            "description": "玻璃基底单层四分之一波长 MgF2 增透膜",
            "design_wavelength": demo.DESIGN_WAVELENGTH,
            "stack": demo.demo_payload(),
            "coated_R": coated.R,
            "bare_substrate_R": bare.R,
        })

    @app.post("/api/rta")
    def rta():
        """单点计算：膜系 + wavelength + angle_deg -> R/T/A。"""
        payload = request.get_json(silent=True)
        if payload is None:
            raise ValidationError("请求体必须是 JSON 对象")
        stack = parse_stack(payload)
        wavelength = parse_wavelength(payload.get("wavelength"))
        angle = parse_angle(payload.get("angle_deg", 0.0))
        polarization = parse_polarization(payload.get("polarization"))

        result = solve_point(stack, wavelength, angle, polarization)
        return jsonify({
            "wavelength": wavelength,
            "angle_deg": angle,
            "polarization": polarization,
            **result.as_dict(),
        })

    @app.post("/api/spectrum")
    def spectrum_scan():
        """光谱扫描：膜系 + 波段 -> 逐波长 R/T/A 点列。"""
        payload = request.get_json(silent=True)
        if payload is None:
            raise ValidationError("请求体必须是 JSON 对象")
        stack = parse_stack(payload)
        start = parse_wavelength(payload.get("wavelength_start"),
                                 "wavelength_start")
        end = parse_wavelength(payload.get("wavelength_end"), "wavelength_end")
        if end <= start:
            raise ValidationError(
                f"wavelength_end 必须大于 wavelength_start（{start}）",
                "wavelength_end",
            )
        points = parse_points(payload.get("points", 200))
        angle = parse_angle(payload.get("angle_deg", 0.0))
        polarization = parse_polarization(payload.get("polarization"))

        points_out = spectrum.scan(stack, start, end, points, angle, polarization)
        return jsonify({
            "wavelength_start": start,
            "wavelength_end": end,
            "angle_deg": angle,
            "polarization": polarization,
            "points": points_out,
        })

    return app
