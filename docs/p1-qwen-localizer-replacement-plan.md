# P1 自动定位开发入口

2026-10-08：用户已授权在既定架构内持续开发、调试、模型运行与开发数据采集。
原“一次固定诊断后等待批准”的工作方式已被替代。冻结基线仍为 `64916b3`；
历史结果不重写。开发迭代与正式独立验收分开，几何/tool标准不降低。

## 当前实现

- Qwen3-VL-4B-Instruct：仅 full RGB 自动二维 BOX/POINT，不是 P3规划。
- 独立模型原生解析器 → source-bound typed grounding → 同一POINT/BOX/depth准入。
- 原 SAM2.1 tiny → 所有native masks → 冻结RGB-D几何；无人工定位/挑mask。
- 已有VisualTracker通过自动观测支持初始化，随后使用新帧RGB-D；不把旧mask续命。
- fresh sampler开发采集器不加载旧init状态；collector真值与sensor输入分开。

本地模型：`/home/junhongli/models/huggingface/Qwen3-VL-4B-Instruct-modelscope-302de2ef`。
独立环境：`.venv-p1-qwen3vl/bin/python`。
来源为Qwen官方ModelScope发布、revision `302de2efb1dd6de1ee943eb1277dc6875550563d`；
15files逐项SHA验证。HF commit等同性未知，不作虚假声明。配置及依赖/load receipts：
`runs/p1/qwen3vl-preparation-20261008/`。旧环境和SAM权重/门槛不变。

## 可运行命令

```sh
CUDA_VISIBLE_DEVICES=GPU_UUID .venv-p1-qwen3vl/bin/python -m embodied_runtime.experiments.p1_qwen_localizer_dev --model MODEL_PATH --recording RECORDED_FRAMES --output NEW_GROUNDING
CUDA_VISIBLE_DEVICES=GPU_UUID CUBLAS_WORKSPACE_CONFIG=:4096:8 .venv-p1-sam2/bin/python -m embodied_runtime.experiments.p1_localizer_surface_dev masks --input NEW_GROUNDING --output NEW_MASKS
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv-p1/bin/python -m embodied_runtime.experiments.p1_localizer_surface_dev geometry --input NEW_MASKS --output NEW_GEOMETRY
```

路径与GPU_UUID须用当前实际值。每次新目录；模型raw文本/tokens/完整性、typed拒绝、
frame绑定、全部native masks与逐候选几何保留。失败不是重试后覆盖。

## 开发到验收

先在已暴露帧上修工程接口、定位与支持质量，必要时明确记录新前端条件。
目标是得到真实自动定位/几何/连续追踪能力，不继续优化一个模型调用的表面成功。
随后冻结一个实际可用条件，在新的、经曝光/场景布局核查的RGB-D上配对评价。
现有init0–49与重渲染都不是新held-out；fresh sampler仅提供开发场景，不自动认证独立性。

正式评价分开BOX/POINT、SAM、geometry和最终candidate池；所有输入保留分母，
上游拒绝后下游NOT_EVALUATED。人工标注只作离线评价且保持真实来源，
保守区域外只能判不符合当前验收，不能直接认定别的物体。
空间通过后仍需10段真实时序验证、freshness/lineage和执行就绪检查，按P1 scope gate
决定P2a/B0非接触接近。没有reference则VERIFY UNKNOWN；不提前PUSH/Qwen规划/Laya联调。

初版详细草案（含尚未启用的30帧/124调用预算）保存在
`runs/p1/qwen3vl-development-direction-20261008/initial-plan-before-development-authorization.md`；
它不是正在执行的正式预注册。后续验收前再固定数据、预算、条件与停止规则。
