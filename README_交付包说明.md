# 交付包结构说明

> **基于深度学习的智能宠物视觉信息系统** · 交付压缩包内容指南
>
> 学号：**2023117319** · 姓名：**陈登科** · 课程：**智能信息系统综合实践（挑战项 D）**

本文档专门用于说明本次提交的压缩包内容、目录结构与运行方式。
完整的项目技术说明请参见 `源码/README.md`。

---

## 1. 包顶层结构

解压后顶层目录如下，**源码** / **实验报告 PDF** / **答辩 PPT** / **项目录屏** 四者并列：

```text
2023117319_陈登科_智能宠物视觉系统/
├── 源码/                    # 全部前后端代码 + README（模型权重需外挂下载，详见 § 4）
├── 实验报告.pdf             # 实验报告 PDF（完整实验过程与结果分析，45 页）
├── 智能宠物视觉系统.pptx    # 答辩 PPT（PowerPoint 源文件）
└── 项目录屏.mp4             # 项目功能演示录屏（1080p、约 15 MB）
```

> ⚠️ 因提交平台 80 MB 限制，**模型权重文件 (266 MB) 已从本包中移除**，
> 需从网盘单独下载后放回 `源码/backend/weights/` 目录。具体见§ 4。

## 2. 源码目录结构

```text
源码/
├── README.md                       # 项目主文档（详细技术说明，500+ 行）
├── README_交付包说明.md            # 本文件
├── docker-compose.yml              # Docker 一键编排（前 + 后端）
├── .gitignore                      # 工程化配置
│
├── backend/                        # 后端服务（FastAPI + PyTorch）
│   ├── app/                        ├─ 全部源码 (16 个 .py)
│   │   ├── main.py                 │   ├─ FastAPI 入口
│   │   ├── core/                   │   ├─ 配置 / 限流
│   │   ├── routers/                │   ├─ 5 个 REST 路由
│   │   ├── services/               │   ├─ 5 个推理服务（含 Grad-CAM）
│   │   ├── schemas/                │   ├─ Pydantic 响应模型
│   │   └── utils/                  │   └─ 图像 IO + 可视化
│   ├── weights/                    ├─ 训练好的模型权重（4 个 .pth）
│   │   ├── cls_torch.pth           │   ├─ ResNet-34 ImageNet 预训练（81 MB）
│   │   ├── cls_torch_random_init.pth │   ├─ ResNet-34 随机初始化对照（81 MB）
│   │   ├── cls_simple_cnn.pth      │   ├─ SimpleCNN 4 层卷积（10 MB）
│   │   └── seg_unet.pth            │   └─ U-Net 分割模型（93 MB）
│   ├── artifacts/                  ├─ 训练产物（指标 / 混淆矩阵 / 数据可视化）
│   │   ├── classification/         │   ├─ metrics.json / confusion_matrix.png
│   │   ├── segmentation/           │   ├─ U-Net 评估输出
│   │   └── augmentation_preview/   │   └─ 数据增强可视化样例
│   ├── tests/                      ├─ pytest 测试用例（12 个）
│   ├── Dockerfile                  ├─ 后端容器镜像构建
│   ├── nginx.conf                  ├─ Nginx 反向代理 + gzip
│   ├── requirements.txt            └─ Python 依赖清单
│   └── .dockerignore
│
├── frontend/                       # 前端应用（Vue 3 + Vite）
│   ├── src/                        ├─ 全部源码 (15 个文件)
│   │   ├── views/                  │   ├─ 5 个页面（首页 / 数据集 / 推理 / 分析 / 扩展）
│   │   ├── components/             │   ├─ 公共组件
│   │   ├── api/                    │   ├─ axios 封装
│   │   ├── i18n/                   │   ├─ 中英文案
│   │   └── router/                 │   └─ Vue Router 配置
│   ├── public/                     ├─ 静态资源
│   ├── tests/                      ├─ vitest 单元测试（22 个）
│   ├── package.json                ├─ npm 依赖清单
│   ├── vite.config.js              ├─ Vite 构建配置（含 manualChunks）
│   ├── Dockerfile                  └─ 前端容器镜像构建
│   └── ...
│
└── training/                       # 训练 / 评估脚本（10 个 .py）
    ├── train_cls_torch.py          ├─ ResNet-34 分类训练
    ├── train_cls_simple_cnn.py     ├─ SimpleCNN 训练
    ├── train_cls_fastai.py         ├─ FastAI 备选实现
    ├── train_seg_unet.py           ├─ U-Net 分割训练
    ├── eval_cls_torch.py           ├─ 分类评估（含 Top-5 / 混淆矩阵）
    ├── eval_cls_simple_cnn.py      ├─ SimpleCNN 评估
    ├── eval_seg_unet.py            ├─ 分割评估（Dice / mIoU / Pixel Acc）
    ├── simple_cnn.py               ├─ SimpleCNN 网络定义
    └── split_utils.py              └─ 7:2:1 数据集划分工具
```

## 3. 文件统计

| 一级目录 | 文件数 | 主要体积 | 说明 |
|----------|-------:|---------:|------|
| `源码/backend/` | ~30 | ~22 MB | 代码、测试、训练产物（权重已外挂） |
| `源码/frontend/` | ~30 | ~600 KB | 不含 `node_modules`（260 MB） |
| `源码/training/` | 10 | ~50 KB | 训练评估脚本 |
| `源码/` 顶层 | 4 | ~30 KB | README + 配置 |
| `实验报告.pdf` | 1 | ~20 MB | 实验报告 |
| `智能宠物视觉系统.pptx` | 1 | ~100 KB | 答辩 PPT |
| `项目录屏.mp4` | 1 | ~15 MB | 项目功能演示录屏（1080p 压缩版） |
| **合计** | **~75** | **~65 MB** | 包体　**需额外下载 266 MB 权重** |

## 4. 已排除内容（需自行恢复）

为适配提交平台 80 MB 上限，以下内容已从压缩包中移除：

| 排除项 | 原大小 | 恢复方式 |
|--------|-------:|----------|
| **`backend/weights/` (4 个 `.pth`)** | **266 MB** | **从网盘下载（链接见下方）后放入 `源码/backend/weights/`** |
| `data/` | 783 MB | 见下方「数据集获取」（Oxford-IIIT Pet 公开数据集） |
| `frontend/node_modules/` | 260 MB | `npm install` 自动恢复 |
| `frontend/dist/` | 63 MB | `npm run build` 自动重建 |
| `**/__pycache__/` | — | Python 运行时自动生成 |
| `**/*.pyc`, `**/.pytest_cache/` | — | 缓存文件，可忽略 |

### 4.1 模型权重下载

本项目提供的 4 个训练好的模型权重文件（共 266 MB）需从网盘下载：

> 📦 **网盘链接**：`<在此填写你的网盘分享链接>`
>
> 提取码：`<如有则填写>`

包含以下 4 个文件：

| 文件名 | 大小 | 说明 |
|--------|-----:|------|
| `cls_torch.pth` | 81 MB | ResNet-34 ImageNet 预训练主模型 |
| `cls_torch_random_init.pth` | 81 MB | ResNet-34 随机初始化对照 |
| `cls_simple_cnn.pth` | 10 MB | SimpleCNN 4 层卷积对照 |
| `seg_unet.pth` | 94 MB | U-Net 分割模型 |

下载后将 4 个 `.pth` 文件直接放入 `源码/backend/weights/` 目录即可。

## 5. 环境要求

| 组件 | 版本要求 | 说明 |
|------|---------|------|
| Python | 3.10+ | 后端运行时 |
| Node.js | 18+ | 前端构建 |
| GPU | 可选 | 推理 CPU 即可；训练建议 6 GB 显存以上 |
| Docker | 20+ | 用于一键部署（可选） |

## 6. 快速启动

> 所有命令均在 `源码/` 目录下执行。

### 方案 A：Docker 一键启动（推荐）

```bash
cd 源码
docker-compose up -d
```

启动后访问：
- 前端：<http://localhost>
- 后端 API 文档：<http://localhost:8000/docs>

### 方案 B：本地手动启动

**后端**：

```bash
cd 源码/backend
python -m venv venv
# Windows
venv\Scripts\activate
# Linux / macOS
source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**前端**：

```bash
cd 源码/frontend
npm install
npm run dev          # 开发模式 → http://localhost:5173
# 或
npm run build        # 生产构建 → frontend/dist/
npm run preview      # 预览生产包
```

## 7. 数据集获取

本项目使用 **Oxford-IIIT Pet Dataset**（37 类宠物，7,390 张图像，公开数据集）：

```bash
mkdir -p 源码/data && cd 源码/data
# 图像
wget https://www.robots.ox.ac.uk/~vgg/data/pets/data/images.tar.gz
# 标注（含分类标签 + 分割掩码 + 边界框）
wget https://www.robots.ox.ac.uk/~vgg/data/pets/data/annotations.tar.gz

tar -xzf images.tar.gz
tar -xzf annotations.tar.gz
```

> 数据集仅用于**重新训练**或**数据集页面预览**。
> 本包 `源码/backend/weights/` 内已包含**训练完成的权重**，可直接用于推理与系统演示，**无需重新训练**。

## 8. 测试

```bash
# 后端 pytest（12 个用例：健康检查 / OpenAPI / 推理参数 / 反馈）
cd 源码/backend
pytest tests/ -v

# 前端 vitest（22 个用例：混淆矩阵工具 / API 封装）
cd 源码/frontend
npm test
```

## 9. 关键性能指标

| 任务 | 模型 | 指标 | 数值 |
|------|------|------|-----:|
| 图像分类 | ResNet-34 (ImageNet 预训练) | Accuracy | **0.9865** |
| 图像分类 | ResNet-34 (随机初始化) | Accuracy | 0.6831 |
| 图像分类 | SimpleCNN (4 层 CNN) | Accuracy | 0.5115 |
| 图像分割 | U-Net (ResNet-34 Encoder) | Dice | **0.9374** |
| 图像分割 | U-Net (ResNet-34 Encoder) | mIoU | 0.8895 |
| 图像分割 | U-Net (ResNet-34 Encoder) | Pixel Accuracy | 0.9709 |

详细分析（混淆矩阵 / 高错品种 / Grad-CAM 观察）请参见包内顶层的 **`实验报告.pdf`**。

## 10. 包内文档索引

| 文档 | 位置 | 说明 |
|------|------|------|
| 项目主文档 | `源码/README.md` | 完整技术说明（架构 / API / 训练流程 / 部署等） |
| 包结构说明 | `源码/README_交付包说明.md` | 本文档 |
| 实验报告 | `实验报告.pdf` | 完整实验过程、结果分析、Grad-CAM 可解释性研究（45 页） |
| 答辩 PPT | `智能宠物视觉系统.pptx` | 课堂答辩用 PowerPoint 源文件 |
| 项目录屏 | `项目录屏.mp4` | 项目功能演示录屏（1080p 压缩版，约 15 MB） |

---

**交付时间**：2026 年 5 月  ·  **包大小**：约 65 MB（需额外下载 266 MB 权重）
