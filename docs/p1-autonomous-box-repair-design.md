# P1 自主 BOX grounding repair：設計與 held-out 計畫

狀態：**設計交付，尚未實作、採集或推理。** 凍結 execution
`ed487281457264772daf1d235d5e6fc9f58ad7a2` 及 evidence checkpoint `2278cd4`。
既有25個 wrist development frames 與 init25/26 不再作修復測試或調參。

本輪選擇先改 semantic BOX grounding 是**工程優先選擇**。上一輪完整
matched21結果 HH/HO/OH/OO=21/21/21/10，兩種替換救回相同11幀，未證明
prompt repair 比 geometry-domain repair 更優。本方案不改寫這項結論。

## 1. 唯一最小修復：BOX 請求使用簡短、正向的部件描述

只更換 LocateAnything **BOX request 的 description 字串**。不新增模型、
二次裁圖、反覆詢問、bbox縮放、負點、幾何回饋或候選選擇器。

對照 A 的原字串完整保留：

```text
the flat outward-facing front panel of the open top drawer of the small cabinet on the tabletop, excluding its handle, inner cavity, rim, and tabletop
```

修復 B 的唯一字串預先固定為：

```text
the exterior front panel of the open top drawer in the small tabletop cabinet
```

兩組共用現有 `infer_audited` 的外層模板，不增加額外回答格式要求：

```text
Locate a single instance that matches the following description: {query}.
```

假說：縮短描述並直接指向 exterior front panel，可能減少長排除清單與
整個cabinet/桌面之間的語義混淆。這只是可否證假說，不是成功保證；模型
可能仍輸出整個櫃體、錯誤部件，或因沒有EOS而拒絕。

**POINT 不跟著改。** 每張新RGB只以原 query 和原模板生成一次自動POINT：
`Point to: {A原字串}.` 同一份raw/typed POINT結果供A/B兩組使用。POINT不完整、
錯位、出框或無depth時保留失敗，不能用human point、box center或另一個
模型POINT補洞。也不能順便移除POINT需求改跑BOX-only作為救援條件。

完整鏈路仍是：

```text
full RGB → A或B自動BOX
full RGB → 固定原query自動POINT（兩組共享相同結果）
→ 現有POINT/BOX/depth admission
→ 現有SAM，保留每個合法BOX的全部native multimasks
→ 原BOX同時作現有geometry ROI
→ 原component/plane/edge/uncertainty/tool gates
→ 候選集合或UNKNOWN
```

因此本次**不解除BOX與geometry ROI的綁定**，不改SAM、geometry、控制接口，
不新增frame-specific recipe。修復可以無人工輸入自行執行；但能否產生可靠
感知輸出，以及能否完成P1，均待驗證。

## 2. 不可變條件與資訊邊界

- LocateAnything同一checkpoint/content ID：
  `4b5384cddedaa8d10e7205536ebde4893d8e20c396ad861dda2a32ed3bbcd10f`。
  同一依賴鎖、processor、dtype與已封存GPU條件；256-token budget、hybrid、
  temperature0、do_sample=false、use_cache=true均不变。EOS與typed規則不變。
- POINT原query/模板/decoder/typed contract不變。每次請求新建messages；不得
  延續聊天history、隱式使用先前回答或保留跨圖片的語義cache。
- SAM source `2b90b9f5ceec907a1c18123530e92e794ad901a4`、SAM2.1 tiny權重SHA
  `7402e0d864fa82708a20fbd15bc84245c2f26dff0eb43a4b5b93452deb34be69`、FP32、seed1、
  deterministic grid overlay、threshold0、無postprocessing維持封存條件。
- `configs/p1_geometry.json`檔案SHA
  `7f9795086d0406287aa60492a22dfd9f338c58c5cf5f25b0cab6316df1d57d85`；解析配置hash
  `f3abcfd935087aa5992df6419bac6068b49fadc782e51b841ffc557808ef5da8`。
  native-mask-depth/2、所有geometry/tool gates、seed0、candidate ordering不變。
- Geometry只用當幀RGB-D、K/T標定、合法EEF本體資料。模型只讀RGB與已註冊文字。
  不讀MuJoCo target pose/body/site/contact/segmentation、official success或標註。
  init state僅供隔離的capture harness重置與provenance，不是感知輸入。
- 模型分數／IoU不視為校準機率；`calibrated_confidence=null`。
  沒有reachability/sweep證據的候選繼續 `usable_status=UNKNOWN`。
- 全部native masks、所有合法BOX、全部拒絕與raw candidates保留；無largest/
  nearest component、無predicted-IoU winner、無first-VALID停止。

## 3. 新 held-out manifest：事先選身份，不按畫面或結果挑樣本

計畫集合 `P1-BOX-HO23-v1`：同一 `top_drawer` 任務
`libero_90/KITCHEN_SCENE10_close_the_top_drawer_of_the_cabinet`，seed1，
**init27..49全部23個state**，384×256，原camera配置與reset settling。
首個capture bundle的 `robot0_eye_in_hand` 為唯一模型評測來源。agentview可隨
同bundle原樣存檔，不跑模型、不作fallback、不計作另23個獨立樣本。
不改相機位置、不做接近、遮擋干預或post-reset robot command。

這是23個新的reset states，不能用同一state的相鄰靜態幀湊成50個獨立例子。
原P1至少50-frame觀測要求已有歷史評測；此處是新的有界repair held-out test，
不是聲稱新增完整temporal/viewpoint/generalization驗證。後續10段temporal仍需做。

**可執行前的兩段式預註冊：**

1. 先freeze本方案、A/B字串、ID清單、執行code/config/dependency hashes。
   只讀metadata檢查init27..49存在且此前未被研究使用；審查既有run manifests、
   init-state hashes及archive inventory。當前P1配置檢查未發現使用27..49，但
   全歷史archive查核尚待執行，現在不宣稱其獨立性已驗證。
2. 按固定ID各fresh reset一次，保留第一個capture；生成sensor manifest，記錄
   init source hash、RGB/depth、K/T、proprio、camera/frame/episode IDs與時間戳。
   封存並比對歷史RGB hashes，然後才允許模型推理。內容hash在採集前尚不存在，
   不填造假值。重複／已暴露／缺失state、校準或source mismatch時停下記錄，
   不自動換ID、重採到滿額或從新畫面挑好看的。

## 4. 盲標註與配對執行

region標註語義鎖定到已封存 `human-annotation-packet-v2-20261005/annotation_rules.md`，
SHA256 `d595017579fd4acabe16c563b74de8486ca64e5ee9650c294d78b30d7048ecfe`。
現有通用validator已是rules/3，不能直接套用再默默升級規則；新packet工具須
明確驗證這份rules/2的hash與新ID清單，重用image-binding/polygon等不變helpers，
保留真實version，不把v2標成v3。這是資料封裝相容性，不改標註對象或可見性定義。

- 沿用現有人工region規則與schema的語義，不新增AI draft。標註者只看原RGB，
  不展示A/B條件標識、BOX、POINT、masks或geometry輸出；允許VISIBLE/UNKNOWN/NOT_VISIBLE。
  drawer_front_pushable_region沿用原可接觸內部區域規則；原schema其他欄位
  維持原規則，但本次不評估fixed reference，也不新增reference推理。
- 標註完成後封存。Annotation export不能出現在inference/SAM/geometry的輸入
  manifest或可讀目錄；離線scoring在模型與geometry全數封存後才開啟標註。
  尚無真人標註時可完成模型輸出封存，但不能生成虛構評分或宣稱通過。
- 每張frame一次POINT及A/B各一次BOX，**共69次LocateAnything request slots**。
  三者只讀同一full RGB；POINT一次生成後逐byte共用。偶數init先A後B，奇數
  init先B後A；每次皆獨立conversation，固定seed/decoder。process receipts記錄
  順序、GPU UUID、依賴、token IDs、EOS及latency。無模型實驗跨arm共享history。
- 每個typed BOX依原canonical ordinal處理；同一POINT與BOX相容才調用SAM。
  型別不符、no-EOS、POINT不可用、BOX不包point等都是對應失敗，不追加query。
  全部可生成的SAM masks走原geometry，不因POINT-mask矛盾省略raw geometry；
  既有point-containment admission另外記錄。每個arm獨立sealed outputs。
- 正常no-EOS／abstention／gate rejection仍完成其餘固定batch。
  crash/OOM/source mismatch則保留未完成狀態與failure receipt並停止，不自動重試。
  可修序列化、路徑等純harness bug，但需獨立commit+針對性測試；若首次嘗試
  已產生輸出，不得覆寫或偷偷改成retry後成功。涉及科學條件則停下。

## 5. 四層指標：分母與失敗不可合併

| 層 | 預先定義的指標 | 分母／限制 |
|---|---|---|
| BOX | complete-EOS/typed有效率；每個BOX的human-region coverage、purity及對human region包圍框的IoU | all23與VISIBLE分開；多BOX全部報，不選winner |
| POINT | complete-EOS、typed、depth-available；point落在human region內比例；對A/B BOX各自的相容率 | 原自動POINT共用；all23以及相容條件分母分開，不能用humanPOINT替代 |
| SAM support | 每native mask的target coverage/purity、point containment、depth availability、components與原gate first rejection | 只對真正生成的masks算條件統計；未生成另列，不偽稱SAM失敗 |
| 最終候選 | any-correct existence、raw/admitted wrong-target counts、clean candidate-set rate、各stage fail taxonomy | all23和VISIBLE雙報；另報A/B共同生成子集，不丟失端到端失敗 |

BOX的二值「target-support localization correct」只用於離線評分：
**同一BOX**對VISIBLE人工region的coverage≥0.90，且與該region最小包圍框
IoU≥0.50。報每BOX；frame的existence與「全部BOX均正確」分別報告，不用
後者挑選輸入。這些是新評測標準，不是新增runtime/geometry gates。
因人工region是可推內部區域，IoU不是整個front-panel精確輪廓ground truth；
需同時報連續coverage/purity/IoU，不能把一個低IoU直接當作語義不存在。

`clean candidate-set`：VISIBLE frame內，既有admission後至少一個候選投影在
人工region內，且**該frame所有admitted候選均在region內**。無POINT、无BOX、
无mask、geometry拒絕均不算成功；不允許只挑其中一個好mask冒充完整鏈通過。
UNKNOWN/NOT_VISIBLE與生成失敗始終保留，所有比例同時給numerator/denominator。
raw wrong-target即使被原有point-containment排除也單獨保留；無新filter。
候選「符合標註」不代表可執行，兩種狀態不得混稱。

## 6. 預註冊決策與停止條件

**不在完成前看結果修改字串、標註規則或門檻。** paired差異按frame（不是
mask）報gains/losses與rate difference；附比例區間及exact discordance descriptive
統計，23個同task樣本不作廣泛泛化或因果優越性宣稱。

一次batch後最多作出以下結論：

1. **可進下一輪temporal驗證的spatial-ready訊號**：至少19/23人工VISIBLE；
   修復B至少19/23為clean candidate-set，VISIBLE條件clean rate≥80%；VISIBLE
   上admitted wrong-target candidate總數0；來源與資訊邊界檢查全部通過。
   A/B改善至少3個net clean frames才稱「本batch有實質工程改善」。若A、B皆
   達spatial-ready但差異<3，記為equal-ready/no demonstrated BOX gain，不硬稱
   B更優。80%與zero-wrong-identity沿用現有P1空間門檻精神；≥3為事先固定的
   工程差異門檻，不是統計顯著性標準，也不放寬geometry gates。
2. **BOX改善但全鏈不改善**：例如BOX定位率增加而POINT不可用／錯位、SAM支持
   或候選污染仍阻塞。明確記 partial interface improvement / end-to-end blocked；
   不換POINT、不移除POINT、不用人工提示、不啟動控制。
3. **修復無效、退步或不可判定**：保留raw與完整failure taxonomy；結束此condition。
   不產生第二條BOX query，也不追加新frames追到成功。若VISIBLE少於19，記
   observability-limited/inconclusive；不剔除NOT_VISIBLE來製造高比例。

任一未達完整鏈路標準的結果都先報告停止，下一輪才**評估**獨立geometry
search-domain方案；不是自動實作它。若failure breakdown指出主要是POINT
缺失，明確指出domain獨立化也未被證明能補上該缺口，不藉失敗同時修改兩層。

即使spatial-ready，也只賦予下一輪10段temporal evaluation的依據。
P1總PASS仍需temporal association/lineage與freshness；reference/VERIFY仍可UNKNOWN。
P1 Gate A/B/C之後才按原路線進P2a/B0，不能直接由本batch進PUSH或Qwen/Laya。

## 7. 實施位置、重用與依賴順序（下一輪，這輪不改程式）

| 批次／位置 | 最小工作 | 重用／不改 |
|---|---|---|
| R0 `configs/p1_box_grounding_heldout_v1.json`（新） | A/B/POINT三條實際query、27..49清單、指標/stop rules、source/dependency hashes | 不改歷史configs、QUERIES或已封存manifest |
| R1 `experiments/p1_box_grounding_heldout.py`（新） | explicit manifest capture、exposure inventory、stage sealing；只記錄sensor，不跑manual ROI或tracker | 重用 `LiberoSensorEnv`、`FrameRecorder`；不能直接調用含manual seed/tracker的 `p1_rgbd_probe.process_recording` |
| R2 `experiments/p1_heldout_annotation_packet.py`（新） | 支持明確23個新image identities的raw-RGB標註packet與完整性檢查 | 重用annotation HTML/rules/identity validators；原50-frame工具不改、不偽裝init0..24 |
| R3 同一heldout runner | 自動POINT once/frame、BOX A/B、原SAM/geometry；分別記錄box_query/point_query、frame/target ID及raw hashes | 重用 `infer_audited`、`infer_point`、typed parser、`point_prompt`、`estimate_segmented_patch` |
| R4 `experiments/p1_box_grounding_heldout_scoring.py`（新） | 只在封存後讀標註；四層metrics、完整分母、matched差異與全部native可視化 | 重用 `score_mask`、polygon rasterization和投影；原scorers保持原樣 |
| R5 `tests/test_p1_box_grounding_heldout.py`（新） | 少量synthetic/mocked邊界測試；source pin/static checks；報告與checkpoint | 不拿舊25frames作regression推理或repair測試 |

R3的query綁定要特別注意：現有 `point_prompt` 核對的是POINT自己的query，
因此兩組都傳實際 `POINT_QUERY=A原字串`。BOX generation的query另存A或B，
SAM mask binding保留實際BOX response來源與query。兩者以同一sensor identity
與宣告target key對齊。不能把POINT record的query改成B來騙過驗證；也不需要
修改 `semantic_prompt.py` 或控制消息以放寬query檢查。新runner不直接套用
`p1_identity_prompt._masks` 中「一個row.query供所有請求」的假設。

測試只覆蓋必要風險：
- A/B僅BOX字串不同；自動POINT raw hash共享且原query不可偽造；annotation
  path/schema不能進生成輸入；錯frame/target來源拒絕。
- no-EOS、BOX外POINT、source-mask unavailable保留，canonical多BOX/3native
  全數評估；不讀標註選mask、不把未生成算成功。
- 新23-frame packet身份/duplicates/exposure驗證；clean候選集合遇一個wrong
  point即不算clean；UNKNOWN不轉VISIBLE，分母包含所有23attempt slots。

執行順序：R0/R1/R2 → code/config prereg freeze → metadata檢查與capture封存 →
獨立人工標註及R3模型/geometry各自封存 → R4 scoring/inspection → stop/report。
不引入新runtime branch，不實作tracker或servo。本設計是單一BOX query repair；
所有harness新增只服務可追溯、公平且不洩漏標註的A/B比較。
