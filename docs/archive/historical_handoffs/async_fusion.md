> Historical record; its plans and checkout paths are not current instructions.
> Current authority: [current_state.md](../../current_state.md).

# 异步观测融合设计

## 结论

自动驾驶可以借鉴三类机制：严格区分采集时间和到达时间、用有限容量队列处理背压、在固定时间窗内处理晚到观测。不能直接照搬车辆的地图定位和雷达运动模型；LIBERO 这里的参考时钟是仿真时间，机器人相机位姿来自同一帧的标定/proprioception，任务几何必须由 RGB-D 估计。

## 时间合同

每个观测必须携带：

- `episode_id`
- `source`
- `source_seq`
- `capture_sim_time`
- `received_wall_time`
- camera calibration version
- frame/camera id
- quality and TTL

控制决策在 `reference_time` 形成。视觉结果可以晚到，但只有在固定 `lag_s` 窗口内才允许插入；更早的结果记录为 `dropped_too_late`。同一 source/sequence 的重复结果记录为 out-of-order。

## 几何融合

`ConstantVelocityFusion3D` 是第一版固定滞后滤波器：

1. 以捕获时间排序 RGB-D 3D 位置；
2. 用常速度状态 `[x,y,z,vx,vy,vz]` 做预测；
3. 用测量协方差和质量调整观测噪声；
4. 用 Mahalanobis 门限拒绝明显错误观测；
5. 晚到观测插回 lag window 后重放；
6. 在当前 reference time 外推，输出位置、速度、协方差和 age。

这是工程上比“最新结果覆盖旧结果”可靠的最小实现。它仍然不是完整 SLAM 或物体姿态估计：相机标定错误、错误关联和系统性深度偏差不会被 Kalman 自动修复。

## 语义融合

`SemanticEvidenceFusion` 与几何滤波分开。标签概率按 source sequence 去重，并随 capture age 衰减；语义不被硬塞进高斯状态。目标部件的离散判断要通过质量和 TTL 影响动作门控。

## 关联

`QueryTrackManager` 只在同一个 query 内关联，使用 2D IoU 和 3D 距离门控。它不使用 simulator object id 或真实关节值。多目标场景需要继续加入匈牙利匹配、遮挡状态和 track covariance。

## 当前频率策略

第一版建议：

- MuJoCo/proprio：每个控制 step；
- RGB-D capture：每个控制 step 或 10--20 Hz；
- LocateAnything：单 worker、容量 1、只处理最新帧；
- geometry fusion：每个控制 step 查询一次；
- Laya：只有在新语义结果、目标状态变化或 TTL 到期时触发；否则短暂保持上一动作，但不能越过动作最大保持步数。

模型推理慢于仿真时，旧帧不能阻塞控制循环。队列替换、模型延迟、观测年龄、晚到和门控拒绝都必须进入 JSONL。

## 仍需验证

- 多步、多 seed 的 vision_rule / vision_laya；
- drawer front/handle/运动轴的 RGB-D 几何估计；
- 深度方差和物体尺寸估计；
- 多目标遮挡与 track switch；
- Laya 候选数量、温度和动作保持策略；
- 真实任务成功率与 Wilson 置信区间。
