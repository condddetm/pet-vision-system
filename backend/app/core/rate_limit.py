"""
API 限流配置 — 基于 slowapi (令牌桶 + 内存存储)

用途:
  - 防止恶意/误用导致后端资源被瞬时打满 (如批量推理时连击)
  - 保护 GPU 显存与 CPU 推理队列

策略:
  - 推理接口 (重负载): 30 次 / 分钟
  - 反馈接口 (轻量写入): 10 次 / 分钟
  - 静态/数据集接口不限流

如需在多副本部署中共享计数器，可将 storage_uri 切换为 Redis。
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],  # 全局默认不限流，按端点显式声明
)

# 各端点限流速率（集中管理，便于调整）
INFER_RATE = "30/minute"
FEEDBACK_RATE = "10/minute"
