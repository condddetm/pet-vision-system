# 基于深度学习的智能宠物视觉信息系统（题目 D：分类 + 分割）

本项目为课程大作业实现，基于 **Oxford-IIIT Pet** 数据集完成多任务视觉分析。
面向 **挑战项 D（多任务视觉分析）**，在同一系统中完成 **图像分类 + 图像分割** 双任务，并通过共享 ResNet-34 主干进行训练。

## 核心能力

- **图像分类** — 37 类宠物品种，ResNet-34，Test Accuracy = **0.9865**
- **图像分割** — 宠物前景二值分割，U-Net，Test Dice = **0.9374** / mIoU = **0.8895** / Pixel Acc = **0.9709**
- **多模型对比** — ResNet-34 (ImageNet 预训练) / ResNet-34 (随机初始化) / 自定义 SimpleCNN (4 层 CNN) 同图三模型对比推理
- **Grad-CAM 可解释性** — ResNet-34 `layer4[-1]` Hook + 反向传播生成类激活热力图
- **实时摄像头识别** — `getUserMedia` 抓帧直接调用推理 API
- **批量并发推理** — 多图同时上传，3 路并发，支持单张重试 + CSV 导出
- **WebSocket 实时日志** — 推理过程逐阶段（解码 / 分类 / 分割 / 叠加）流式推送
- **PDF 报告导出** — html2canvas-pro + jsPDF 切片输出多页 A4 实验报告
- **错误反馈闭环** — 用户标注误判结果写入 JSONL，用于后续模型迭代
- **中英双语切换** — vue-i18n 全站文案中 / 英 一键切换

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | FastAPI · PyTorch · torchvision · OpenCV · Pillow |
| 前端 | Vue 3 · Vite · Element Plus · ECharts · vue-i18n · html2canvas-pro · jsPDF |
| 模型 | ResNet-34 (ImageNet pretrained) · U-Net (ResNet-34 encoder) · SimpleCNN (custom) |
| 数据 | Oxford-IIIT Pet (37 类，7,390 张) |

训练脚本默认采用固定随机种子的 `7:2:1` 划分（训练 / 验证 / 测试），
评估脚本使用独立测试集输出最终指标与混淆矩阵。

## 最新结果

| 任务 | 模型 | 指标 | 数值 | 评估集样本数 |
|------|------|------|------|-------------|
| 图像分类 | ResNet-34 | Accuracy | 0.9865 | 741 |
| 图像分类 | ResNet-34 | Precision (macro) | 0.9872 | 741 |
| 图像分类 | ResNet-34 | Recall (macro) | 0.9865 | 741 |
| 图像分类 | ResNet-34 | F1 (macro) | 0.9865 | 741 |
| 图像分割 | U-Net (ResNet-34 Encoder) | Dice | 0.9374 | 739 |
| 图像分割 | U-Net (ResNet-34 Encoder) | mIoU | 0.8895 | 739 |
| 图像分割 | U-Net (ResNet-34 Encoder) | Pixel Accuracy | 0.9709 | 739 |

## 1. 项目结构

```text
可视化/
├── README.md                    # 本文件
├── start_all.bat                # Windows 一键启动后端 + 前端
├── docker-compose.yml           # Docker 一键编排 (backend + frontend)
├── .gitignore                   # 排除 node_modules / __pycache__ 等
│
├── docs/                        # 使用手册 LaTeX + PDF (32 页交付物)
│   ├── usage_manual.tex
│   ├── usage_manual.pdf
│   └── README.md                # 编译说明
│
├── backend/                     # FastAPI 后端
│   ├── requirements.txt
│   ├── Dockerfile               # 后端镜像构建 (Python 3.10-slim, ~2.3 GB)
│   ├── pytest.ini               # 测试配置
│   ├── tests/                   # pytest 单元测试 (12 用例)
│   ├── app/
│   │   ├── main.py              # FastAPI 入口 (CORS / 限流 / static mounts)
│   │   ├── core/
│   │   │   ├── config.py        # 路径常量 (TMP_DIR / WEIGHTS_DIR / ARTIFACTS_DIR)
│   │   │   └── rate_limit.py    # slowapi 限流配置
│   │   ├── routers/             # 5 个路由模块
│   │   │   ├── infer.py         # /api/infer/{multitask,compare,gradcam}
│   │   │   ├── ws_infer.py      # /ws/infer (WebSocket 流式日志)
│   │   │   ├── dataset.py       # /api/dataset/{stats,samples,augmentation}
│   │   │   ├── metrics.py       # /api/metrics/{summary,curves,cases,...}
│   │   │   └── feedback.py      # /api/feedback (错误反馈)
│   │   ├── services/            # 5 个推理服务
│   │   │   ├── classify_service.py    # ResNet-34 分类
│   │   │   ├── segment_service.py     # U-Net 分割
│   │   │   ├── multitask_service.py   # 分类+分割联合调度
│   │   │   ├── compare_service.py     # 三模型同图对比
│   │   │   └── gradcam_service.py     # Grad-CAM 热力图生成
│   │   ├── schemas/response.py  # Pydantic 响应模型
│   │   └── utils/               # image_io / visualize
│   ├── weights/                 # 模型权重 (cls_torch.pth / seg_unet.pth / cls_simple_cnn.pth)
│   └── artifacts/               # 评估产物
│       ├── classification/      # metrics / curves / confusion_matrix / 案例图
│       │   └── simple_cnn/      # SimpleCNN 单独评估产物
│       ├── segmentation/        # seg_metrics / seg_curves
│       ├── augmentation_preview/# 数据增强示例 (8 种 × 6 品种)
│       ├── dataset_samples/     # 原图 + mask + overlay 三联展示
│       └── feedback/            # 用户反馈 JSONL (运行时自动创建)
│
├── frontend/                    # Vue 3 + Vite 前端
│   ├── package.json
│   ├── vite.config.js           # Vite 配置 (含手动分包 + vitest)
│   ├── Dockerfile               # 前端镜像构建 (Node 构建 + Nginx 部署, ~50 MB)
│   ├── nginx.conf               # Nginx 反向代理配置 (API + WebSocket)
│   ├── test/                    # vitest 单元测试 (22 用例)
│   ├── public/
│   │   ├── favicon.svg          # 自定义宠物爪印 favicon
│   │   └── samples/             # 单张推理示例图
│   └── src/
│       ├── main.js
│       ├── App.vue              # Shell + Sidebar + Topbar
│       ├── style.css
│       ├── router/index.js      # 5 个页面路由
│       ├── api/{http.js,index.js}
│       ├── i18n/                # 中英双语
│       │   └── locales/{zh.js,en.js}
│       ├── utils/confusion.js
│       └── views/               # 5 个核心页面
│           ├── Intro.vue        # 项目介绍 (Hero / 模型 / 架构 / 系统亮点 / 技术栈)
│           ├── Dataset.vue      # 数据集展示 (统计 / 样本 / 类别分布)
│           ├── Predict.vue      # 模型预测 (Single / Batch / Compare 三模式)
│           ├── Analysis.vue     # 实验分析 (曲线 / 混淆矩阵 / 案例 / PDF 导出)
│           └── Extra.vue        # 扩展分析 (三模型对比 / 局限性)
│
├── training/                    # 训练 + 评估脚本
│   ├── train_cls_torch.py       # ResNet-34 分类训练 (支持 --no-pretrained 开关)
│   ├── train_cls_simple_cnn.py  # SimpleCNN 分类训练
│   ├── train_cls_fastai.py      # fastai 风格快速 baseline
│   ├── train_seg_unet.py        # U-Net 分割训练
│   ├── eval_cls_torch.py        # ResNet 分类评估 (生成混淆矩阵 + 案例)
│   ├── eval_cls_simple_cnn.py   # SimpleCNN 评估
│   ├── eval_seg_unet.py         # U-Net 评估
│   ├── split_utils.py           # 7:2:1 固定种子划分
│   └── models/simple_cnn.py     # 自定义 4 层 CNN
│
└── data/pets/                   # Oxford-IIIT Pet 原始数据集
    ├── images/                  # 7,390 张 .jpg
    └── annotations/trimaps/     # 像素级 trimap 分割标注
```

## 2. 环境安装

建议 Python 3.10+，Node 18+，Windows / Linux 均可。

### 2.1 后端依赖

```bash
cd backend
pip install -r requirements.txt
```

CUDA 版 PyTorch（推荐）：

```bash
pip uninstall -y torch torchvision torchaudio
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### 2.2 前端依赖

```bash
cd frontend
npm install
```

关键前端依赖：

| 包 | 用途 |
|---|---|
| `vue@3` + `vue-router@4` | 单页应用框架 |
| `element-plus` + `@element-plus/icons-vue` | UI 组件库 + 图标 |
| `echarts` | 训练曲线 / 混淆矩阵 / 雷达图 |
| `vue-i18n@9` | 中英双语国际化 |
| `html2canvas-pro` + `jspdf` | PDF 多页报告导出 |
| `axios` | HTTP 客户端 |

### 2.3 模型权重

三个权重文件统一存放于 `backend/weights/`，后端服务启动时自动加载：

| 权重文件 | 大小 | 模型 | 生成命令 |
|---|---|---|---|
| `backend/weights/cls_torch.pth` | ~85 MB | ResNet-34 (ImageNet pretrained, 100 ep) | `python training/train_cls_torch.py ...` |
| `backend/weights/seg_unet.pth` | ~98 MB | U-Net (ResNet-34 encoder, 30 ep) | `python training/train_seg_unet.py ...` |
| `backend/weights/cls_simple_cnn.pth` | ~14 MB | SimpleCNN (自定义 4 层 CNN, 50 ep) | `python training/train_cls_simple_cnn.py ...` |
| `backend/weights/cls_torch_random_init.pth` | ~85 MB | ResNet-34 (随机初始化对比组) | 加 `--no-pretrained` 开关 |

> 本项目后端启动时会检查以上文件。若未训练，请参考 §4 训练命令生成。训练脚本默认输出到以上路径，无需手动移动。

## 3. 数据集准备

### 3.1 目录结构

```text
data/pets/
├── images/                  # 7,390 张宠物图片 (*.jpg)
└── annotations/
    ├── trimaps/             # 像素级 trimap 分割标注 (*.png)
    ├── list.txt             # 原始官方清单
    ├── trainval.txt
    └── test.txt
```

说明：项目展示页与统计接口统一按 `data/pets/images` 下实际图片文件数计算，总计 `7,390` 张；
原始 `data/pets/annotations/list.txt` 中可解析条目为 `7,349`，两者统计口径不同，现已统一以前者为准。

### 3.2 下载地址

- images: https://www.robots.ox.ac.uk/~vgg/data/pets/data/images.tar.gz
- annotations: https://www.robots.ox.ac.uk/~vgg/data/pets/data/annotations.tar.gz

下载后解压到项目根目录 `data/pets/`。

## 4. 训练命令

### 4.1 分类训练（100轮）

```bash
python training/train_cls_torch.py --images_dir data/pets/images --epochs 100 --bs 32 --img_size 224 --patience 1000
```

训练完成后自动保存 `backend/artifacts/classification/curves.json`

### 4.2 自定义 CNN 分类训练（SimpleCNN，50轮）

```bash
python training/train_cls_simple_cnn.py --images_dir data/pets/images --epochs 50 --bs 32 --img_size 224 --patience 8
```

训练完成后自动保存 `backend/weights/cls_simple_cnn.pth` 和 `backend/artifacts/classification/curves_simple_cnn.json`

### 4.3 分割训练（30轮）

```bash
python training/train_seg_unet.py --images_dir data/pets/images --trimaps_dir data/pets/annotations/trimaps --epochs 30 --bs 8 --img_size 256 --num_workers 6
```

训练完成后自动保存 `backend/artifacts/segmentation/seg_curves.json`

## 5. 评估命令

### 5.1 分类评估（生成混淆矩阵 + 案例图片）

```bash
python training/eval_cls_torch.py --images_dir data/pets/images --ckpt backend/weights/cls_torch.pth --out_dir backend/artifacts/classification --img_size 224
```

输出：
- `metrics.json`（Acc/P/R/F1）
- `confusion_matrix.png` + `confusion_matrix.json`
- `correct_1..5.jpg` + `error_1..5.jpg`（正确/错误案例）

### 5.2 SimpleCNN 分类评估

```bash
python training/eval_cls_simple_cnn.py --images_dir data/pets/images --ckpt backend/weights/cls_simple_cnn.pth --out_dir backend/artifacts/classification/simple_cnn --img_size 224
```

输出：
- `metrics.json`（Acc/P/R/F1）
- `confusion_matrix.png` + `confusion_matrix.json`
- `correct_1..5.jpg` + `error_1..5.jpg`（正确/错误案例）

### 5.3 分割评估（生成 mIoU / Dice / PixelAcc）

```bash
python training/eval_seg_unet.py --images_dir data/pets/images --trimaps_dir data/pets/annotations/trimaps --ckpt backend/weights/seg_unet.pth
```

输出：`backend/artifacts/segmentation/seg_metrics.json`（mIoU / Dice / PixelAcc）

## 6. 对比实验复现

本项目包含三组对比实验：ResNet-34 ImageNet 预训练、ResNet-34 随机初始化、自定义 SimpleCNN（4层卷积+2层全连接，随机初始化）。训练/验证/测试划分、输入尺寸和评估脚本保持一致。

### 6.1 分类随机初始化

```bash
python training/train_cls_torch.py --images_dir data/pets/images --epochs 100 --bs 32 --img_size 224 --patience 1000 --no-pretrained --out backend/weights/cls_torch_random_init.pth --curves_out backend/artifacts/classification/curves_random_init.json
python training/eval_cls_torch.py --images_dir data/pets/images --ckpt backend/weights/cls_torch_random_init.pth --out_dir backend/artifacts/classification/random_init --img_size 224
```

### 6.2 分割随机初始化

```bash
python training/train_seg_unet.py --images_dir data/pets/images --trimaps_dir data/pets/annotations/trimaps --epochs 30 --bs 8 --img_size 256 --num_workers 6 --encoder_weights none --out backend/weights/seg_unet_random_init.pth --curves_out backend/artifacts/segmentation/seg_curves_random_init.json
python training/eval_seg_unet.py --images_dir data/pets/images --trimaps_dir data/pets/annotations/trimaps --ckpt backend/weights/seg_unet_random_init.pth --out_dir backend/artifacts/segmentation/random_init
```

### 6.3 SimpleCNN 自定义基线

```bash
python training/train_cls_simple_cnn.py --images_dir data/pets/images --epochs 50 --bs 32 --img_size 224 --patience 8
python training/eval_cls_simple_cnn.py --images_dir data/pets/images --ckpt backend/weights/cls_simple_cnn.pth --out_dir backend/artifacts/classification/simple_cnn --img_size 224
```

### 6.4 当前对比结果

| 任务 | ResNet-34 预训练 | ResNet-34 随机初始化 | SimpleCNN 自定义 |
|------|-----------------|---------------------|-----------------|
| 图像分类 Accuracy | 0.9865 | 0.6831 | 0.5115 |
| 图像分割 Dice | 0.9374 | 0.8213 | — |

前端 `/analysis` 和 `/extra` 页面展示三模型对比图、复现命令和分析结论。

### 6.5 Grad-CAM 可解释性

推理时自动对 ResNet-34 最后一个残差块（`layer4[-1]`）注册 forward + backward hook，对 top-1 类反向传播获取梯度，按通道全局平均池化加权激活后 ReLU，再 cv2 JET 上色与原图按 0.55:0.45 alpha 混合。

该功能集成在 `/predict` 单张推理页面，推理完成后异步触发，结果出现在「多维度可视化对比」第 4 张缩略图中，无需额外配置。

后端实现：`backend/app/services/gradcam_service.py`  
API 端点：`POST /api/infer/gradcam`

## 7. 启动系统

### 7.1 Windows 一键启动（推荐）

项目根目录提供自包含的 `start_all.bat`，双击即可自动在两个独立控制台窗口中同时启动后端和前端：

```text
start_all.bat           # 同时启动后端 (8000) + 前端 (5173)
```

如需单独运行只启动后端或只启动前端，请参考 §7.3 / §7.4 手动命令。

### 7.2 Docker 一键部署（跨平台）

```bash
docker compose up -d --build
```

构建完成后访问 `http://localhost`（前端走 80，Nginx 反代 API 与 WebSocket 到后端容器）。

### 7.3 手动启动后端

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

该命令会按顺序加载 `backend/weights/` 下三个模型权重 (参见 §2.3)，并挂载静态资源目录 `backend/artifacts/`。

### 7.4 手动启动前端

```bash
cd frontend
npm run dev          # 开发模式
npm run build        # 生产构建（输出到 frontend/dist/）
npm run preview      # 预览生产构建（端口 4173）
```

### 7.5 访问地址

- 前端页面：`http://localhost:5173`（开发）或 `http://localhost`（Docker）
- 后端 API：`http://127.0.0.1:8000`
- 后端交互式 API 文档：`http://127.0.0.1:8000/docs`
- 静态资源（训练产物、推理临时文件）：`http://127.0.0.1:8000/static/...`

## 8. 系统页面说明

| 页面 | 路由 | 主要功能 |
|------|------|------|
| **项目介绍** | `/` | Hero 横幅 / 关键指标 / 模型卡片 / 多任务架构图 / 系统亮点 / 技术栈 / 项目说明 |
| **数据集展示** | `/dataset` | 数据集卡片 / 类别分布 / 预处理参数 / 6 张原图+mask+叠加样本 / 数据增强 8 变体 / 37 类分布条形图（折叠） |
| **模型预测** | `/predict` | **三模式 Tab 切换**：<br>· **单张推理**：上传 / 摄像头抓拍 → ResNet-34 分类 + U-Net 分割 + Grad-CAM 热力图<br>· **批量推理**：拖拽多图，3 路并发推理，可重试 / 导出 CSV<br>· **三模型对比**：同图调用 ResNet-34(预训练) / ResNet-34(随机) / SimpleCNN<br>额外功能：实时 WebSocket 日志面板、错误反馈表单、历史记录、Top-5 置信度 |
| **实验分析** | `/analysis` | Dark Banner 双任务指标 / 训练曲线 / 混淆矩阵 / 5 正确+5 错误案例 / 类别精度排行 / 复现命令 / **PDF 多页导出** |
| **扩展分析** | `/extra` | 三模型对比图 / Top-6 高错品种 / 完整超参数表（CLS / SimpleCNN / SEG 三列） / 6 项模型局限性 / 4 项未来方向 |

## 9. API 端点速查

### REST API

| 方法 | 路径 | 说明 |
|---|---|---|
| `POST` | `/api/infer/multitask` | 单张图片 → 分类 + 分割结果 |
| `POST` | `/api/infer/compare` | 同图三模型对比推理 |
| `POST` | `/api/infer/gradcam` | 生成 Grad-CAM 热力图 |
| `GET`  | `/api/dataset/stats` | 数据集统计（类别分布等） |
| `GET`  | `/api/dataset/samples` | 原图+mask+叠加 三联样本 |
| `GET`  | `/api/dataset/augmentation?breed=` | 数据增强 8 变体预览 |
| `GET`  | `/api/metrics/summary` | 分类 + 分割汇总指标 |
| `GET`  | `/api/metrics/curves` | 训练 loss / val 曲线 |
| `GET`  | `/api/metrics/cases` | 正确 / 错误案例图 |
| `GET`  | `/api/metrics/confusion-matrix` | 混淆矩阵原始数据 |
| `GET`  | `/api/metrics/comparison` | 三模型对比指标 |
| `POST` | `/api/feedback` | 提交错误反馈 |
| `GET`  | `/api/feedback/recent` | 查询最近反馈 |
| `GET`  | `/api/feedback/stats` | 反馈统计 |

### WebSocket

| 路径 | 说明 |
|---|---|
| `/ws/infer` | 流式推送推理过程 (`info` / `ok` / `error` / `done` 阶段) |

## 10. 评分点对照表（参考课程要求）

| 评分模块（20 分） | 实现位置 |
|---|---|
| 数据集处理与分析 | `/dataset` 页面 + `data/pets/` + `training/split_utils.py` |
| 深度学习模型训练 | `training/train_*.py` 三组训练脚本 + 共享 backbone 设计 |
| 实验对比与评价指标 | `/analysis` + `/extra` (三模型对比 + 完整指标表) |
| 系统页面与交互功能 | 5 个 Vue 页面 + 上传 / 批量 / 摄像头 / 反馈 / WebSocket |
| 结果分析与报告质量 | `/analysis` 案例分析 + `/extra` 局限性 + PDF 报告导出 |

### 加分项实现清单

- ✅ Top-5 预测 (`/predict` 单张)
- ✅ 迁移学习 vs 从零训练对比 (`/predict` Compare 模式)
- ✅ 推理时间对比（每模型显示 latency）
- ✅ 多模型对比 (3 个分类模型)
- ✅ Grad-CAM 可解释性
- ✅ 实时摄像头采集
- ✅ 历史记录
- ✅ 错误反馈闭环
- ✅ PDF 报告导出
- ✅ WebSocket 流式日志
- ✅ 中英双语
- ✅ 批量并发推理 + CSV 导出

## 11. 工程化实践

本项目除了完成深度学习任务本身，还实现了一套贴近生产级别的工程化体系。

### 11.1 Docker 容器化部署

| 文件 | 说明 |
|---|---|
| `backend/Dockerfile` | 多阶段构建，Python 3.10-slim 基础镜像，安装 OpenCV 系统依赖 |
| `frontend/Dockerfile` | Node 构建 + Nginx 部署两阶段构建，最终镜像约 50 MB |
| `frontend/nginx.conf` | Nginx 配置 SPA 路由回退、API 反代、WebSocket 升级、gzip 压缩 |
| `docker-compose.yml` | 编排 backend + frontend 双服务，含健康检查与依赖等待 |
| `backend/.dockerignore` / `frontend/.dockerignore` | 排除构建产物与缓存，减小上下文 |

启动命令：

```bash
docker compose up -d --build       # 构建并启动
docker compose logs -f             # 查看日志
docker compose down                # 停止
```

### 11.2 API 限流（slowapi）

后端集成 [`slowapi`](https://github.com/laurentS/slowapi) 防止瞬时高并发冲击：

| 端点 | 速率 | 用途 |
|---|---|---|
| `/api/infer/multitask` | 30 / 分钟 | 单张推理 |
| `/api/infer/compare` | 30 / 分钟 | 三模型对比 |
| `/api/infer/gradcam` | 30 / 分钟 | Grad-CAM 生成 |
| `/api/feedback` | 10 / 分钟 | 错误反馈写入 |

配置集中在 `backend/app/core/rate_limit.py`，便于调整或切换至 Redis 共享计数器。

### 11.3 自动化测试

#### 后端 pytest（12 用例）

```bash
cd backend
pytest                  # 运行全部测试
pytest --tb=short -v    # 详细失败信息
```

测试覆盖：健康检查、OpenAPI Schema、推理端点参数校验、反馈接口写入与统计。

#### 前端 vitest（22 用例）

```bash
cd frontend
npm test                # 运行全部测试
npm run test:watch      # 监听模式
```

测试覆盖：混淆矩阵工具函数（`utils/confusion.js`）、API 封装层 URL 与 FormData 构造。

### 11.4 前端构建优化

`vite.config.js` 配置手动分包（`manualChunks`），将大型第三方库拆出独立 chunk：

| 分包 | 内容 | 体积（gzip 后） |
|---|---|---|
| `vendor-vue` | vue / vue-router / vue-i18n | ~61 KB |
| `vendor-element` | element-plus + 图标 | ~332 KB |
| `vendor-echarts` | echarts | ~343 KB |
| `vendor-pdf` | html2canvas-pro / jsPDF | ~187 KB |
| 业务代码 | 5 个页面 + 共享逻辑 | ~61 KB |

主业务 chunk 从单文件 **3 MB → 165 KB**（缩小 95%），浏览器可并发加载第三方库且支持长缓存。

### 11.5 安全加固

- **CORS 限域**：默认白名单 `localhost:5173 / 127.0.0.1:5173 / localhost:4173`，生产环境通过 `ALLOWED_ORIGINS` 环境变量覆盖。
- **文件类型校验**：所有图片接口校验 `Content-Type` 必须以 `image/` 开头，拦截非法上传。
- **请求体大小限制**：FastAPI 默认配合 Uvicorn 的请求体大小限制保护内存。
- **输入校验**：Pydantic 严格类型 + `Field(ge=0.0, le=1.0)` 等约束。

## 12. 常见问题

### pip 下载超时

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --timeout 120 --retries 10
```

### 训练误用 CPU

若日志显示 `Using device: cpu`，请重装 CUDA 版 PyTorch 并验证：

```bash
python -c "import torch; print(torch.cuda.is_available())"
```

### 摄像头权限被拒

浏览器需 HTTPS 或 `localhost`/`127.0.0.1` 才能调用 `getUserMedia`。本地开发默认满足；如部署到内网 IP 需配置 HTTPS 或在 Chrome `chrome://flags/#unsafely-treat-insecure-origin-as-secure` 加入白名单。

### PDF 导出时报色彩函数错误

确保使用 `html2canvas-pro`（已在 `package.json` 中），原版 `html2canvas@1.4.1` 不支持 `color-mix()` 等现代 CSS 颜色函数。
