# =============================================================================
# 前端 Dockerfile — Pet MultiTask System (Vue 3 + Vite + Nginx)
# 多阶段构建：Node 阶段构建静态文件，Nginx 阶段提供生产服务，最终镜像 ~50 MB
# =============================================================================

# ─── 阶段 1: 构建静态资源 ─────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# 利用层缓存：先 package*.json，再源码
COPY package*.json ./
RUN npm ci --registry=https://registry.npmmirror.com

COPY . .
RUN npm run build

# ─── 阶段 2: Nginx 提供静态服务 ─────────────────────────────────────────────
FROM nginx:1.27-alpine

# 移除默认配置，使用自定义反向代理配置
RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 拷贝构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -qO- http://localhost/ > /dev/null || exit 1

CMD ["nginx", "-g", "daemon off;"]
