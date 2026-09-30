# 目标点估计合同

版本：2026-09-29。这个文件定义“目标点”如何从观测得到；它不是把VLM的框中心直接当作接触点。

点、状态、意图和执行器之间的传输字段及异步规则见 [模块协议与推理例子](protocols-and-inference-example.md)。

## 结论

首版不需要激光雷达。LIBERO已有`agentview`和`robot0_eye_in_hand`相机，打开`camera_depths`后可用同一时刻的RGB、metric depth、内参K和相机到机器人基座的T生成彩色点云。真实机器人迁移时再按工作距离选择深度相机；D405的官方理想工作距离约7–50cm，7cm处“<1mm”是最小可检测物体指标，不是整个手眼系统的目标点精度。

## 模型职责

1. Qwen3-VL-4B-Instruct：输入任务和RGB，输出短 referring query、目标类别/部件类别、阶段和是否弃权。它可以做2D定位消融，但不返回可直接执行的毫米坐标。
2. LocateAnything-3B：按query在当前RGB中返回一个或多个2D框/点。其坐标按官方`[0,1000]`量化格式转换成当前图像像素；原始响应与帧ID全部保存。
3. RGB-D几何层：对框/点对应的同帧depth做ROI清理、点云建模、表面拟合和接触点选择。
4. 机器人本体层：提供采集时刻的EEF FK、夹爪状态、工具尺寸、工作空间和腕部相机外参。

## 数据流

```text
RGB + depth + K + T_base_camera(capture time)
  → query ROI / point
  → ROI depth validity and connected components
  → XYZ point cloud in base frame
  → surface / edge / candidate contact patches
  → robot reachability and swept-link clearance
  → target point candidates with covariance
```

RGB、depth、K和T必须来自同一`FrameBundle`。相机外参使用capture时刻的机器人状态；不能使用模型返回时刻的外参解释旧帧。`agentview`和腕部相机的点云在进入关联前转换到同一base frame。来自同一depth图的depth、point cloud和centroid保留provenance，不能作为三条独立测量重复Kalman更新。

## 抽屉正面推点算法

这是首版`PUSH_VISIBLE_SURFACE`，不假定把手存在。

1. LocateAnything给出drawer front候选框。框只限定ROI，不把框中心当点。
2. 按深度有效性、深度范围和局部3D连通性去除背景；机器人自点只用已声明的机器人模型和本体状态剔除，不能用MuJoCo segmentation ID。
3. 点云体素初值：目标ROI约2–3mm，周围占据约5mm；最多保留约5k目标点、20k场景点。阈值以录制数据的速度和细节保留率校准。
4. 对目标ROI运行RANSAC平面拟合，再用支持点SVD重拟合。计算：平面法向`n`、残差`r_plane`、支持比例、可见边界和法向协方差。若平面退化、残差过大或支持比例不足，返回`geometry_unknown`。
5. 在平面内生成规则网格候选点。删除距离可见边界小于`tool_contact_radius + 2*sigma_position + margin`的点；删除机器人运动学不可达、工具扫掠会进入已观察占据体、或当前相机不可见的点。
6. 对每个剩余点计算：EEF到点的法向距离、切向误差、法向夹角、局部点密度、深度/标定协方差、可见障碍间距、点到边界裕量。以这些量产生候选排序和拒绝原因；几何层可给出首选点，但如果Laya要选择点，必须把多个合法点作为带稳定ID的候选。
7. 输出`TargetPointCandidate`。坐标计算和评分依据如下，后面是字段示例。

坐标计算使用针孔模型：`x=(u-cx)*z/fx`、`y=(v-cy)*z/fy`、`p_base=T_base_camera*[x,y,z,1]`。对像素位置/深度误差的局部Jacobian `J`，以`Sigma_base≈R*J*Sigma_uvz*J^T*R^T+Sigma_calib`保守传播到base frame；`Sigma_calib`覆盖外参标定下限，不能靠更多同帧点使它消失。RANSAC在`tool_radius+2*sigma_position`腐蚀后的目标面内部选支持点，SVD重拟合面及法向。候选评分只在通过边缘、可达和扫掠硬门槛的点里比较：优先更大的可见障碍间距/边缘裕量，更小的面残差、位置不确定度和到EEF的距离；每项指标记录原值，权重用标注集校准。这个排序为视觉规则基线服务；Laya使用相同合法候选时不能由规则预先只留一个“最佳点”。

```json
{
  "point_id": "drawer_front_patch_04_p12",
  "track_id": "drawer_2",
  "position_base_m": [0.21, -0.08, 0.34],
  "normal_base": [0.0, -1.0, 0.0],
  "covariance_m2": [[0.000004,0,0],[0,0.000009,0],[0,0,0.000004]],
  "edge_margin_m": 0.018,
  "eef_distance_m": 0.036,
  "normal_alignment_deg": 4.2,
  "visible_clearance_m": 0.025,
  "quality": "usable",
  "source_frame_seq": 118,
  "calibration_version": "agentview-v1"
}
```

示例数值不是测量结果。真实系统必须由同一帧计算并记录单位、来源和误差。

## 把手或抓取点

把手不能由drawer框中心替代。若任务需要handle：

- Qwen/LocateAnything先输出`drawer handle` query和候选ROI；
- ROI点云分割细长/凸起连通组件；
- 用局部PCA和可见端点生成抓取中心、主轴和夹爪接近方向；
- 仅保留夹爪开度、工具包络、视线和点云支持均满足的候选；
- 目标被夹爪遮挡后停止假设视觉仍看得见，转用本体夹爪反馈/力或重新观察。

如果没有足够点云支持，则输出`handle_unknown`，动作只能HOLD/REOBSERVE。不能从抽屉任务JSON读取真实把手坐标或滑轨轴。

## 两相机一致性检查

当`agentview`和腕部相机同时看到同一track：

1. 各自用本帧K/T得到3D候选；
2. 只在共同base frame中做3D门控；
3. 对候选面法向和位置做协方差加权一致性检查；
4. 超过门限时保留两个来源并标记`view_disagreement`，不平均成看似精确的点；
5. 目标点必须通过至少一个来源的可见边界、深度支持和机器人可达性检查。

两相机共享同一目标并不意味着它们是独立真值；要保留source provenance和相关误差。

## 真机阶段的具体硬件

仿真阶段不采购硬件。若之后迁移到桌面机械臂，先试一个固定工作区D435i（官方理想范围约0.3–3m）加一个腕部D405（约7–50cm）。这是基于工作距离互补的候选配置，不是已经验证的末端安装方案。须检查机械干涉、USB/算力、工具遮挡、RGB成像质量和手眼标定；若工作区布置让固定相机离目标太近，就重新选镜头/机位。

D435i官方最大分辨率的最小深度约28cm，靠近夹爪末端时不能依赖它；D405官方50cm处深度误差标为约±2%，即深度方向约10mm的量级，尚未包括外参和工具校准误差。D405在接触最后约7cm和夹爪遮挡时也会失去可靠深度。接触反馈只能来自实际具备的夹爪开度/力矩等本体传感，不能伪造触觉。此阶段没有证据支持购买传统旋转激光雷达来估计小型抽屉把手。

## 目标点质量门控

`usable`至少需要：深度有效比例达标、平面/局部几何残差达标、边界裕量达标、位置协方差小于配置上限、目标未LOST、采集帧未过期、点到工具扫掠通道可达。否则是`uncertain`或`unknown`。

- `usable`：允许APPROACH/ALIGN；接触动作还需最新帧和更严格年龄。
- `uncertain`：只允许自由空间小步、HOLD或REOBSERVE。
- `unknown`：禁止PUSH/GRASP/RELEASE/ROTATE。

完成关闭抽屉还需要固定柜体参照和可见活动面。只看到目标“不再移动”不能证明已经关闭；遮挡或没有闭合间隙时，VERIFY必须返回`verification_unknown`。

## 评测

先用至少50个不同初始状态/视角/遮挡帧人工标注可接触面内部区域；报告：

- 目标面/部件查询选择准确率；
- 2D框IoU和目标track错误率；
- 候选点到人工可接触区域边界的距离；
- 位置和法向误差、协方差覆盖率；
- `usable/uncertain/unknown`比例；
- 视角不一致、遮挡、重定位、过期帧比例；
- 最终动作失败原因。

先验证非方形图像的K顺序和RGB/depth上下翻转：给定像素、深度及已知T，反投影与重投影的合成误差应在数值容差内；另做双相机真实渲染的同一物理平面跨视角一致性测试。人工点标注只供离线误差评测，不供运行策略。

比较单`agentview`、双RGB-D、RGB-only和oracle上界；oracle只用于离线误差，不进入policy。目标点算法通过后，再比较Qwen3-VL-4B与Qwen2.5-VL-7B的大脑选择，不能把模型定位点直接当几何真值。

## 一手来源

- LIBERO环境封装（双相机、20Hz、默认关闭depth）：https://raw.githubusercontent.com/Lifelong-Robot-Learning/LIBERO/master/libero/libero/envs/env_wrapper.py
- robosuite相机K/T和metric depth：https://raw.githubusercontent.com/ARISE-Initiative/robosuite/v1.4.1/robosuite/utils/camera_utils.py
- Open3D点云下采样、离群过滤、RANSAC平面：https://www.open3d.org/docs/release/tutorial/geometry/pointcloud.html
- Qwen3-VL-4B模型卡：https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct
- Qwen3-VL作者代码：https://github.com/QwenLM/Qwen3-VL
- LocateAnything模型卡和解析格式：https://huggingface.co/nvidia/LocateAnything-3B
- RealSense D405官方产品页：https://www.realsenseai.com/products/d405/
- RealSense D435i官方产品页：https://www.realsenseai.com/products/d435i/

RealSense D405的7–50cm是理想工作距离，官方“7cm处<1mm”是最小可检测物体指标，不是端到端手眼目标点精度。真机接触仍需夹爪/力反馈或控制器反馈；不要把深度中值宣传成毫米级抓取精度。
