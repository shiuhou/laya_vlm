# P1 獨立真人盲標交接

使用者已選擇保留原盲評測要求，改由**未看過 AI 草稿的新真人標註者**完成。此前提交原樣保留於[收件紀錄](evidence/p1_grounding/annotation_receipt_20261005/README.md)，不能作為本條件的盲標真值，也不匯入新資料包。

## 給標註者的材料與步驟

只交付 `/home/junhongli/projects/laya/p1_blind_annotation_independent_v3_50views.zip`，不要交付本研究的模型輸出、舊標註、AI 草稿、軌跡或評測結果。標註者若接觸過這批圖像的上述資訊，不符合本輪資格。身份與未接觸聲明均為本人自我聲明，軟體不能獨立證明。

1. 解壓 ZIP，用瀏覽器打開資料夾內的 `index.html`；不需連網或啟動服務。
2. 先讀資料包內的 `annotation_rules.md`，再從空白標註全部 50 張原始 RGB。頁面不展示 depth、模型 ROI、幾何候選或演算法結果。
3. 每張分別標註 drawer-front 潛在推動區及 fixed cabinet reference；允許 `VISIBLE`、`UNKNOWN`、`NOT_VISIBLE`，按照規則填理由。不要猜測被遮擋部分或把窄區域加寬。
4. 定期匯出部分進度備份；完成全部圖像後填本人聲明並匯出完整 JSON。不要匯入 v2 或其他人的標註，也不要參照模型結果修改標註。
5. 將完整匯出另存為 `/home/junhongli/projects/laya/p1_annotations_inbox/annotations.independent-v3.complete.json`，不要覆蓋此前的 `annotations.complete.json`。

交接者可以解釋工具與既定規則，不得提示個別圖像應如何圈選或分類。標註僅用於離線評測；不能直接成為執行 ROI、推點或 VERIFY 真值。靜態 RGB 標註不證明物理固定性、可達性或安全性。

## 封存與版本

- 空白包：`runs/p1/human-annotation-packet-independent-v3-20261005/`。
- Dataset ID：`b4f09b3fae2529cb80cbaaab99280b0420366d1e3399845a734af4d5d516c4ae`。
- Rules：`p1-rgb-annotation-rules/3`，SHA256 `1b0dc9af5491fbe4d26cc8dfd7664c4351e0da0cef71499dc58af0e82df18202`。
- ZIP SHA256：`a17932aac8c87c67e9af36d827c7d52938987a846eee36718d22cc868e258fe4`。
- 預註冊：`runs/p1/grounding-preregistration-independent-v3-20261005.json`。
- [交接審計及測試](evidence/p1_grounding/independent_annotation_v3_20261005/handoff-audit.json)：同一批原始 RGB 綁定；query、模型、生成設定、幾何程式／設定、調用順序與 mask upper-bound 條件保持不變。只變更規則版本、標註者資格與相應資料包／註冊身份。

新版 dataset ID 隔離舊瀏覽器 autosave；舊版匯入會被拒絕。瀏覽器 QA 的合成單圖標註僅在 `/tmp`，不作人工評測證據。已完成 501 項回歸測試及實際 Chromium 頁面 QA；未進行 LocateAnything 推論。

## 收件後才能執行

在倉庫根目錄驗證完整匯出：

```sh
.venv-p1/bin/python -m embodied_runtime.experiments.p1_annotation_packet validate \
  --packet runs/p1/human-annotation-packet-independent-v3-20261005 \
  --annotations /home/junhongli/projects/laya/p1_annotations_inbox/annotations.independent-v3.complete.json
```

通過完整性、圖像綁定及盲標聲明檢查後，再封存原始匯出，檢查 GPU 配置，按[實驗交接文件](p1-grounding-observability.md)執行固定條件評測。缺標、資格衝突或版本不符時停止；不改 query 或 geometry gate 來通過。Qwen、Laya、PUSH 與完整 P2 均未啟動。
