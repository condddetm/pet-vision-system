# =============================================================================
# 后端 Dockerfile — Pet MultiTask System (FastAPI + PyTorch)
# 多阶段构建：编译阶段安装依赖，运行阶段仅保留必需文件，最终镜像 ~2.3 GB
# =============================================================================

FROM python:3.10-slim AS base

# 系统依赖：OpenCV 需要 libgl1 和 libglib2.0；模型加载需 build-essential
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 先复制依赖文件，最大化利用 Docker 层缓存
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
        -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制应用代码
COPY app ./app

# 权重与产物目录通过 volume 挂载（避免镜像膨胀）
RUN mkdir -p /app/weights /app/artifacts /app/tmp

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/').read()" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
