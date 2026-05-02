# 实验报告图片清单

实验报告 `experiment_report.tex` 会自动在以下位置引用本目录下的图片。
**文件缺失时会显示灰色占位框并提示「待插入」**，不会编译失败。

---

## 📁 cover/ — 封面图片（必需）

| 文件名 | 尺寸建议 | 用途 |
|---|---|---|
| `nwu_logo.png` | 300×300，透明背景 | 西北大学校徽（圆形带 NORTHWEST UNIVERSITY XIAN CHINA 字样） |
| `nwu_name.png` | 900×200，透明背景 | 西北大学手写体校名（书法字） |

**获取方式**：
- 校徽：从学校官网下载，或搜索「西北大学 校徽 PNG」
- 校名：从学校官网下载，或搜索「西北大学 手写体 PNG」
- 已有你之前发的两张图，可以直接保存到本目录

---

## 📁 screenshots/ — 系统截图（可选，用于正文插图）

建议按下述清单截图。每张需为 **PNG 格式**，建议宽度 ≥ 1200 px，清晰可辨。

### 章节 1 · 研究背景

| 文件名 | 截图位置 | 推荐内容 |
|---|---|---|
| `system_features.png` | `/` 中部 | 「系统核心能力」卡片墙（多任务 / Top-K / Grad-CAM / 实时摄像头 / 批量 / 反馈 / 双语 / PDF）|

### 章节 2 · 数据集

| 文件名 | 截图位置 | 推荐内容 |
|---|---|---|
| `dataset_overview.png` | `/dataset` 顶部 | 4 个统计卡（图像数 / 类别数 / 划分比 / 平均尺寸）+ 类别分布饼图 |
| `dataset_samples.png`  | `/dataset` 中部 | 6 品种的「原图 + mask + 叠加」三联样本网格 |
| `dataset_augmentation.png` | `/dataset` 中部 | 数据增强 8 变体预览（HFlip / Rotate / Crop / ColorJitter / Blur …）|
| `dataset_distribution.png` | `/dataset` 底部 | 37 类详细分布条形图（展开后）|
| `dataset_pie.png` | `/dataset` 顶部 | 犬科 vs 猫科占比饼图（25 vs 12）|

### 章节 4 · 实验结果

| 文件名 | 截图位置 | 推荐内容 |
|---|---|---|
| `analysis_metrics.png` | `/analysis` 顶部 | 深色双任务指标横幅（Acc/P/R/F1 + Dice/mIoU/PixelAcc）|
| `analysis_curves.png`  | `/analysis` 中部 | 训练曲线（Loss / Accuracy / Dice）|
| `analysis_segmentation.png` | `/predict` 单张推理（分割结果区） | 分割三联：原图 / 预测 mask / 叠加 |
| `predict_top5_bar.png` | `/predict` 单张推理（分类卡片）| Top-5 概率条形图特写（带品种名 + 百分比）|
| `extra_models.png`     | `/extra` 顶部   | 三模型横向对比条形图（Acc / P / R / F1）|

### 章节 5 · 系统实现

| 文件名 | 截图位置 | 推荐内容 |
|---|---|---|
| `system_intro.png`     | `/`         | 首页 Hero 横幅 + 关键指标 |
| `system_api_docs.png`  | `/docs`（FastAPI 自带）| Swagger UI 接口文档列表 |
| `dataset_detail.png`   | `/dataset` 全屏 | 完整数据集页（统计 + 样本 + 增强 + 分布）滚动截屏 |
| `system_predict_single.png` | `/predict` 单张推理 | 上传 + 分类 Top-5 + 分割掩膜 + Grad-CAM 四联图（界面整体）|
| `predict_demo_cat_short.png`  | `/predict` 单张推理 | **预测功能演示**：上传一张短毛猫（如 `Abyssinian_1.jpg`）后的完整推理结果（结果区截图，含 Top-5 + 分割 + Grad-CAM）|
| `predict_demo_dog_long.png`   | `/predict` 单张推理 | **预测功能演示**：上传一张长毛狗（如 `samoyed_1.jpg` 或 `pomeranian_1.jpg`）后的完整推理结果 |
| `predict_demo_dog_short.png`  | `/predict` 单张推理 | **预测功能演示**：上传一张短毛狗（如 `pug_1.jpg` 或 `boxer_1.jpg`）后的完整推理结果 |
| `predict_demo_difficult.png`  | `/predict` 单张推理 | **预测功能演示**：上传一张困难样本（如 `Maine_Coon_1.jpg` 或 `Russian_Blue_1.jpg`），展示模型在亲缘相近品种上的表现 |
| `system_predict_batch.png`  | `/predict` 批量推理 | 进度卡 + 批量列表 + CSV 导出按钮 |
| `system_predict_compare.png` | `/predict` 三模型对比 | 三张模型卡片并排 + 对比洞察 |
| `system_websocket.png` | `/predict` 启用「实时日志」开关 | WebSocket 终端风格深色日志面板特写 |
| `system_feedback_form.png` | 任意结果卡片点「反馈错误」| 错误反馈弹窗（品种选择下拉 + 备注框）|
| `system_camera.png` | `/predict` 单张推理 → 摄像头按钮 | 摄像头实时预览 + 抓拍按钮 |
| `system_history.png` | 任意页面 → 历史记录侧栏 | 推理历史列表（缩略图 + 时间戳 + 重新查看）|

### 章节 6 · 结果分析

| 文件名 | 截图位置 | 推荐内容 |
|---|---|---|
| `analysis_confusion.png` | `/analysis` 中部 | 37×37 混淆矩阵热力图（含坐标标签）|
| `analysis_cases.png`   | `/analysis` 中部 | 5 正确 + 5 错误案例组合图 |
| `analysis_gradcam.png` | `/predict` 单张推理结果 | Grad-CAM 热力图细节特写（面部关注区域清晰可见）|
| `analysis_gradcam_compare.png` | 多次推理后拼接 | 4 个不同品种的 Grad-CAM 对比（短毛猫 / 长毛狗 / 错误样本 / 正确样本）|
| `extra_toperrors.png`  | `/extra` 中部   | Top-6 高错品种与混淆对（带百分比）|
| `analysis_seg_gallery.png` | `/predict` 多次分割 | 分割结果画廊（4 个不同体型 / 毛色品种）|

---

## 🚀 使用流程

1. **准备图片**：按上述清单截图并按文件名保存到对应子目录
2. **无需手动改 LaTeX**：`experiment_report.tex` 已经用 `\IfFileExists` 智能引用，有图就显示图，无图就显示占位框
3. **重新编译**：

```powershell
cd docs
xelatex experiment_report.tex
xelatex experiment_report.tex
```

4. **清理中间文件**（可选）：

```powershell
Remove-Item *.aux, *.log, *.out, *.toc -Force
```

---

## 📋 优先级建议

| 优先级 | 图片 | 理由 |
|---|---|---|
| 🔴 必需 | `cover/nwu_logo.png` + `cover/nwu_name.png` | 封面学校标识 |
| 🟡 推荐 | `analysis_metrics.png` + `analysis_curves.png` + `analysis_confusion.png` | 实验数据可视化，最有说服力 |
| 🟡 推荐 | `system_predict_single.png` + `system_predict_compare.png` | 系统核心功能演示 |
| 🟢 锦上添花 | 其余截图 | 让报告更丰满 |

最少只需准备 **2 张封面图**即可完整重编报告；其余截图缺失时会显示占位框，不影响编译成功。
