# 薄膜光学核算服务（thinfilm）

基于分层均匀介质**特征矩阵法**的薄膜光学核算服务，纯 HTTP/JSON 对外，
无网页界面。单点给出反射率 / 透射率 / 吸收率，波段扫描给出反射率光谱
点列。复数特征矩阵连乘实现，折射率带虚部（吸收）自然支持；s/p 偏振
的等效光学导纳各自独立处理。

## 模块划分

| 文件 | 职责 |
|---|---|
| `app/matrix.py` | 复数特征矩阵的构造与连乘（相位厚度含 cos θ 因子） |
| `app/admittance.py` | 光学导纳与 s/p 偏振（Snell 定律复数折射角） |
| `app/solver.py` | 单波长单角度 R/T/A 求解 |
| `app/spectrum.py` | 波长扫描，逐点真值 |
| `app/validation.py` | 输入合法性校验（计算前拒绝非法输入） |
| `app/demo.py` | 内置示范膜系（玻璃基底 MgF2 四分之一波长增透膜） |
| `app/server.py` | Flask HTTP 接口层 |

物理约定：时间因子 exp(-iωt)，折射率 N = n + ik（k>0 为吸收）；
s 偏振导纳 η = N cosθ，p 偏振导纳 η = N / cosθ；
相位厚度 δ = (2π/λ) N d cosθ。

## 构建与启动（单条命令）

```bash
docker build -t thinfilm . && docker run --rm -p 8080:8080 thinfilm
```

基础镜像为 `python:3.12-slim`，服务监听 `0.0.0.0:8080`，多线程并发，
请求间无共享状态。

本地开发（Python 3.12）：

```bash
pip install -r requirements-dev.txt
python run.py        # 启动服务
pytest tests/ -q     # 运行测试
```

## 接口

### `POST /api/rta` — 单点计算

```json
{
  "incident_index": 1.0,
  "substrate_index": 1.52,
  "layers": [{"index": 1.38, "thickness": 99.64}],
  "wavelength": 550.0,
  "angle_deg": 0.0,
  "polarization": "s"
}
```

- 折射率三种写法：`1.38`、`[1.38, 0.0]`、`{"n": 1.38, "k": 0.0}`（k>0 为吸收）
- `thickness` 物理厚度（nm）；`wavelength` 波长（nm）；`angle_deg` 入射角（度，[0, 90)）
- `polarization`：`s` / `p` / `unpolarized`（缺省，取两者平均）

响应：`{"R": ..., "T": ..., "A": ..., "wavelength": ..., ...}`

### `POST /api/spectrum` — 光谱扫描

在单点参数基础上，以波段替代单波长：

```json
{
  "incident_index": 1.0,
  "substrate_index": 1.52,
  "layers": [{"index": 1.38, "thickness": 99.64}],
  "wavelength_start": 400.0,
  "wavelength_end": 700.0,
  "points": 301,
  "angle_deg": 0.0
}
```

响应 `points` 为逐波长点列 `[{"wavelength":..., "R":..., "T":..., "A":...}, ...]`，
每点都是同一套特征矩阵算出的真值。

### `GET /api/demo` — 示范膜系核对

玻璃（n=1.52）基底上单层 MgF2（n=1.38）四分之一波长增透膜，
返回设计波长 550 nm 处镀膜反射率（≈1.26%）与裸基底反射率（≈4.26%）对照。

### `GET /health` — 存活探针

## 错误处理

非法输入在计算前被拒绝，返回 400 与结构化错误：

```json
{"error": {"type": "validation_error", "field": "layers[0].thickness",
           "message": "layers[0].thickness 不能为负，得到 -5.0"}}
```

覆盖：层厚为负、折射率实部非正、消光系数为负、波长非正、
入射角不在 [0, 90)、非法偏振态、波段起点不小于终点等。

## 测试锁住的正确性基准（`tests/`）

- 无吸收膜系任意波长/角度/偏振下 R + T = 1
- 有吸收时 R + A + T = 1 且 A ≥ 0
- 无膜层退化为单界面菲涅耳反射（与独立解析式比对）
- 四分之一波长增透膜设计波长处反射率明显低于裸基底
- 半波厚度时设计波长处增透消失、回升至裸基底
- 入射角趋向掠射时反射率升高
- 相位厚度含 cos θ 因子：斜入射下光谱极小值蓝移
- 非法膜系与参数在计算前被拒绝（400）
- 并发请求结果一致、互不串扰
