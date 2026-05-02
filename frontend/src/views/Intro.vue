<script setup>
/* 统一蓝色基调，分类/分割两类指标用同色系区分 */
const keyStats = [
  { value: '37',     unit: '类', label: '宠物品种',   accent: 'neutral' },
  { value: '7,390',  unit: '张', label: '标注图片',   accent: 'neutral' },
  { value: '98.65%', unit: '',   label: '分类准确率', accent: 'cls'     },
  { value: '0.9374', unit: '',   label: '分割 Dice',  accent: 'seg'     },
]

const pipeline = [
  { icon: 'Download',     label: '数据获取',  sub: 'Oxford-IIIT Pet Dataset',    color: '#2563EB', bg: 'rgba(37,99,235,.08)',  border: 'rgba(37,99,235,.18)'  },
  { icon: 'Setting',      label: '预处理增强', sub: 'Resize · Flip · Normalize', color: '#0891B2', bg: 'rgba(8,145,178,.08)',  border: 'rgba(8,145,178,.18)'  },
  { icon: 'Cpu',          label: '模型训练',  sub: 'ResNet-34 · U-Net',          color: '#7C3AED', bg: 'rgba(124,58,237,.08)', border: 'rgba(124,58,237,.18)' },
  { icon: 'TrendCharts',  label: '评估验证',  sub: 'Accuracy · Dice · mIoU',     color: '#D97706', bg: 'rgba(217,119,6,.08)',  border: 'rgba(217,119,6,.18)'  },
  { icon: 'Promotion',    label: '系统部署',  sub: 'FastAPI + Vue 3',            color: '#059669', bg: 'rgba(5,150,105,.08)',  border: 'rgba(5,150,105,.18)'  },
]

const modelCards = [
  {
    badge: 'CLS',
    badgeColor: '#6366f1',
    badgeBg: 'rgba(99,102,241,.12)',
    title: 'ResNet-34 分类器',
    acc: '98.65%',
    accLabel: 'Top-1 Accuracy',
    desc: '基于 ImageNet 预训练权重迁移学习，100 个 Epoch 训练，ReduceLROnPlateau 动态调整学习率，最新评估集准确率达到 98.65%。',
    tags: ['Adam lr=3e-4', 'BS=32', 'CrossEntropyLoss', '100 Epochs'],
    metric2: '99.9%', metric2label: 'Top-5 Accuracy',
  },
  {
    badge: 'SEG',
    badgeColor: '#10b981',
    badgeBg: 'rgba(16,185,129,.12)',
    title: 'U-Net 分割网络',
    acc: '0.9374',
    accLabel: 'Dice Score',
    desc: '编码器复用 ResNet-34 分类主干，解码器逐层上采样恢复分辨率，像素级二值分割（前景宠物 vs 背景），最新评估集 Dice 达到 0.9374。',
    tags: ['Adam lr=1e-3', 'BS=8', 'BCEWithLogitsLoss', '30 Epochs'],
    metric2: '0.8895', metric2label: 'mIoU',
  },
]

const techStack = [
  { name: 'PyTorch',      color: '#ee4c2c', bg: 'rgba(238,76,44,.08)'   },
  { name: 'ResNet-34',    color: '#6366f1', bg: 'rgba(99,102,241,.08)'  },
  { name: 'U-Net',        color: '#10b981', bg: 'rgba(16,185,129,.08)'  },
  { name: 'FastAPI',      color: '#059669', bg: 'rgba(5,150,105,.08)'   },
  { name: 'Vue 3',        color: '#41b883', bg: 'rgba(65,184,131,.08)'  },
  { name: 'Element Plus', color: '#409eff', bg: 'rgba(64,158,255,.08)'  },
  { name: 'ECharts',      color: '#aa344d', bg: 'rgba(170,52,77,.08)'   },
  { name: 'Vite',         color: '#a259f7', bg: 'rgba(162,89,247,.08)'  },
  { name: 'Oxford Pet',   color: '#f59e0b', bg: 'rgba(245,158,11,.08)'  },
]
</script>

<template>
  <div>
    <!-- ===== Hero ===== -->
    <div class="hero">
      <div class="hero-grid-bg"></div>
      <div class="hero-glow"></div>
      <div class="hero-glow2"></div>
      <div class="hero-content">
        <div class="hero-badge">
          <span class="badge-dot"></span>
          多任务视觉系统 (D) &nbsp;·&nbsp; Oxford-IIIT Pet &nbsp;·&nbsp; 2026 课程项目
        </div>
        <h1 class="hero-title">基于深度学习的<br><span class="hero-title-accent">智能宠物视觉</span>信息系统</h1>
        <p class="hero-desc">
          以 Oxford-IIIT Pet 为基础，同时完成 <b>37 类品种识别</b>与<b>像素级宠物分割</b>，
          实现从原始图片到可视化结果的端到端在线推理。
        </p>

        <div class="hero-stats">
          <div class="hero-stat" v-for="s in keyStats" :key="s.label">
            <div class="hero-stat-value" :class="`hs-${s.accent}`">
              {{ s.value }}<span class="hero-stat-unit">{{ s.unit }}</span>
            </div>
            <div class="hero-stat-label">{{ s.label }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- ===== 系统流程 ===== -->
    <el-card style="margin-bottom:16px">
      <template #header>
        <span style="display:inline-flex;align-items:center;gap:8px;font-weight:600">
          <el-icon color="#2563EB" :size="16"><Connection /></el-icon>完整处理流程
        </span>
      </template>
      <div class="pipeline">
        <div v-for="(step, idx) in pipeline" :key="step.label" class="pipe-step-wrap">
          <div class="pipe-step" :style="{ '--step-c': step.color }">
            <div class="pipe-icon" :style="{ background: step.bg, borderColor: step.border }">
              <el-icon :size="20" :color="step.color"><component :is="step.icon" /></el-icon>
            </div>
            <div class="pipe-label">{{ step.label }}</div>
            <div class="pipe-sub">{{ step.sub }}</div>
          </div>
          <div v-if="idx < pipeline.length - 1" class="pipe-arrow">→</div>
        </div>
      </div>
    </el-card>

    <!-- ===== 模型详情 ===== -->
    <el-row :gutter="16" style="margin-bottom:16px">
      <el-col :span="12" v-for="m in modelCards" :key="m.badge">
        <el-card style="height:100%">
          <template #header>
            <div class="model-header">
              <span class="model-badge" :style="{ background: m.badgeBg, color: m.badgeColor }">{{ m.badge }}</span>
              <span style="font-size:15px;font-weight:700">{{ m.title }}</span>
            </div>
          </template>
          <div class="model-body">
            <div class="model-metrics">
              <div class="model-metric-main">
                <div class="model-metric-val" :style="{ color: m.badgeColor }">{{ m.acc }}</div>
                <div class="model-metric-lbl">{{ m.accLabel }}</div>
              </div>
              <div class="model-metric-sub">
                <div style="font-weight:700;font-size:15px;color:var(--c-dark, #0F172A)">{{ m.metric2 }}</div>
                <div style="font-size:11px;color:#94a3b8">{{ m.metric2label }}</div>
              </div>
            </div>
            <p class="model-desc">{{ m.desc }}</p>
            <div class="model-tags">
              <span v-for="t in m.tags" :key="t" class="model-tag"
                :style="{ background: m.badgeBg, color: m.badgeColor, borderColor: m.badgeColor + '30' }">
                {{ t }}
              </span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- ===== 网络架构图 ===== -->
    <el-card style="margin-bottom:16px">
      <template #header>
        <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap">
          <span style="display:inline-flex;align-items:center;gap:8px;font-weight:600">
            <el-icon color="#2563EB" :size="16"><Share /></el-icon>多任务网络架构
          </span>
          <span style="font-size:11px;color:#94A3B8;font-weight:500">
            ResNet-34 backbone 共享 → 双头分支输出
          </span>
        </div>
      </template>
      <div class="arch-diagram">
        <svg viewBox="0 0 920 280" class="arch-svg" preserveAspectRatio="xMidYMid meet">
          <!-- 渐变定义 -->
          <defs>
            <linearGradient id="gradInput" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0" stop-color="#94A3B8" />
              <stop offset="1" stop-color="#64748B" />
            </linearGradient>
            <linearGradient id="gradBackbone" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0" stop-color="#7C3AED" />
              <stop offset="1" stop-color="#A855F7" />
            </linearGradient>
            <linearGradient id="gradCls" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0" stop-color="#3B82F6" />
              <stop offset="1" stop-color="#60A5FA" />
            </linearGradient>
            <linearGradient id="gradSeg" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0" stop-color="#059669" />
              <stop offset="1" stop-color="#34D399" />
            </linearGradient>
            <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill="#94A3B8" />
            </marker>
          </defs>

          <!-- 输入 -->
          <g class="arch-block">
            <rect x="20" y="115" width="120" height="60" rx="10" fill="url(#gradInput)" />
            <text x="80" y="142" text-anchor="middle" fill="#fff" font-size="13" font-weight="700">输入图像</text>
            <text x="80" y="160" text-anchor="middle" fill="#E2E8F0" font-size="10" font-family="Fira Code, monospace">224 × 224 × 3</text>
          </g>
          <line x1="140" y1="145" x2="180" y2="145" stroke="#94A3B8" stroke-width="2" marker-end="url(#arrow)" />

          <!-- ResNet-34 backbone -->
          <g class="arch-block">
            <rect x="180" y="95" width="200" height="100" rx="12" fill="url(#gradBackbone)" />
            <text x="280" y="125" text-anchor="middle" fill="#fff" font-size="14" font-weight="800">ResNet-34</text>
            <text x="280" y="145" text-anchor="middle" fill="#E9D5FF" font-size="11" font-weight="600">Shared Backbone</text>
            <text x="280" y="166" text-anchor="middle" fill="#E9D5FF" font-size="10" font-family="Fira Code, monospace">ImageNet pretrained</text>
            <text x="280" y="183" text-anchor="middle" fill="#FCE7F3" font-size="9" font-family="Fira Code, monospace">conv1 → layer1~4</text>
          </g>

          <!-- 分叉点 -->
          <line x1="380" y1="120" x2="440" y2="60"  stroke="#94A3B8" stroke-width="2" marker-end="url(#arrow)" />
          <line x1="380" y1="170" x2="440" y2="230" stroke="#94A3B8" stroke-width="2" marker-end="url(#arrow)" />

          <!-- 分类头 -->
          <g class="arch-block">
            <rect x="440" y="20" width="180" height="80" rx="10" fill="url(#gradCls)" />
            <text x="530" y="46" text-anchor="middle" fill="#fff" font-size="12" font-weight="800">分类头 (CLS)</text>
            <text x="530" y="65" text-anchor="middle" fill="#DBEAFE" font-size="10" font-family="Fira Code, monospace">GAP + FC(512→37)</text>
            <text x="530" y="83" text-anchor="middle" fill="#DBEAFE" font-size="10" font-family="Fira Code, monospace">+ Softmax</text>
          </g>
          <line x1="620" y1="60" x2="680" y2="60" stroke="#94A3B8" stroke-width="2" marker-end="url(#arrow)" />
          <g class="arch-block">
            <rect x="680" y="20" width="220" height="80" rx="10" fill="#0F172A" stroke="#3B82F6" stroke-width="1.5" />
            <text x="790" y="46" text-anchor="middle" fill="#60A5FA" font-size="12" font-weight="800">37 类品种概率</text>
            <text x="790" y="65" text-anchor="middle" fill="#94A3B8" font-size="10" font-family="Fira Code, monospace">Top-1 / Top-5</text>
            <text x="790" y="83" text-anchor="middle" fill="#34D399" font-size="11" font-weight="700">Acc 98.65%</text>
          </g>

          <!-- 分割头 (U-Net 解码器) -->
          <g class="arch-block">
            <rect x="440" y="190" width="180" height="80" rx="10" fill="url(#gradSeg)" />
            <text x="530" y="216" text-anchor="middle" fill="#fff" font-size="12" font-weight="800">分割头 (SEG)</text>
            <text x="530" y="234" text-anchor="middle" fill="#D1FAE5" font-size="10" font-family="Fira Code, monospace">U-Net Decoder</text>
            <text x="530" y="252" text-anchor="middle" fill="#D1FAE5" font-size="10" font-family="Fira Code, monospace">UpConv × 5</text>
          </g>
          <line x1="620" y1="230" x2="680" y2="230" stroke="#94A3B8" stroke-width="2" marker-end="url(#arrow)" />
          <g class="arch-block">
            <rect x="680" y="190" width="220" height="80" rx="10" fill="#0F172A" stroke="#10B981" stroke-width="1.5" />
            <text x="790" y="216" text-anchor="middle" fill="#34D399" font-size="12" font-weight="800">前景 Mask</text>
            <text x="790" y="234" text-anchor="middle" fill="#94A3B8" font-size="10" font-family="Fira Code, monospace">256×256 binary</text>
            <text x="790" y="252" text-anchor="middle" fill="#60A5FA" font-size="11" font-weight="700">Dice 0.9374</text>
          </g>
        </svg>
        <div class="arch-legend">
          <span class="al-item"><span class="al-dot" style="background:#7C3AED"></span>共享主干（参数共用，加速训练）</span>
          <span class="al-item"><span class="al-dot" style="background:#3B82F6"></span>分类分支（37 类 Softmax）</span>
          <span class="al-item"><span class="al-dot" style="background:#10B981"></span>分割分支（像素级二值）</span>
        </div>
      </div>
    </el-card>

    <!-- ===== 系统亮点 ===== -->
    <el-card style="margin-bottom:16px">
      <template #header>
        <span style="display:inline-flex;align-items:center;gap:8px;font-weight:600">
          <el-icon color="#F59E0B" :size="16"><Star /></el-icon>系统亮点
        </span>
      </template>
      <div class="extra-grid">
        <div class="extra-card">
          <div class="extra-card-icon" style="background:linear-gradient(135deg,#10B981,#059669)">
            <el-icon :size="20" color="#fff"><VideoCamera /></el-icon>
          </div>
          <div class="extra-card-body">
            <div class="extra-card-title">实时摄像头识别</div>
            <div class="extra-card-desc">
              调用 <code>getUserMedia</code> 抓帧 → 直接走 ResNet-34 + U-Net 推理，无需上传文件。
            </div>
          </div>
        </div>

        <div class="extra-card">
          <div class="extra-card-icon" style="background:linear-gradient(135deg,#EF4444,#DC2626)">
            <el-icon :size="20" color="#fff"><Aim /></el-icon>
          </div>
          <div class="extra-card-body">
            <div class="extra-card-title">Grad-CAM 可解释性</div>
            <div class="extra-card-desc">
              在 ResNet-34 <code>layer4[-1]</code> 注册 hook，对 top-1 类反向传播生成热力图叠加。
            </div>
          </div>
        </div>

        <div class="extra-card">
          <div class="extra-card-icon" style="background:linear-gradient(135deg,#7C3AED,#6D28D9)">
            <el-icon :size="20" color="#fff"><DataLine /></el-icon>
          </div>
          <div class="extra-card-body">
            <div class="extra-card-title">三模型同图对比</div>
            <div class="extra-card-desc">
              ResNet-34 (预训练) vs ResNet-34 (随机初始化) vs SimpleCNN，直观验证迁移学习价值。
            </div>
          </div>
        </div>

        <div class="extra-card">
          <div class="extra-card-icon" style="background:linear-gradient(135deg,#3B82F6,#2563EB)">
            <el-icon :size="20" color="#fff"><Download /></el-icon>
          </div>
          <div class="extra-card-body">
            <div class="extra-card-title">PDF 报告导出</div>
            <div class="extra-card-desc">
              <code>html2canvas-pro</code> + <code>jsPDF</code> 切片输出多页 A4 完整实验分析报告。
            </div>
          </div>
        </div>

        <div class="extra-card">
          <div class="extra-card-icon" style="background:linear-gradient(135deg,#F59E0B,#D97706)">
            <el-icon :size="20" color="#fff"><Files /></el-icon>
          </div>
          <div class="extra-card-body">
            <div class="extra-card-title">批量并发推理</div>
            <div class="extra-card-desc">
              支持任意数量图片，最大 3 路并发；单张可重试 + 结果导出 CSV。
            </div>
          </div>
        </div>

        <div class="extra-card">
          <div class="extra-card-icon" style="background:linear-gradient(135deg,#22D3EE,#0891B2)">
            <el-icon :size="20" color="#fff"><Connection /></el-icon>
          </div>
          <div class="extra-card-body">
            <div class="extra-card-title">WebSocket 实时日志</div>
            <div class="extra-card-desc">
              推理过程逐阶段（解码/分类/分割/叠加）流式推送，类终端面板可视化。
            </div>
          </div>
        </div>
      </div>
    </el-card>

    <!-- ===== 技术栈 ===== -->
    <el-card style="margin-bottom:16px">
      <template #header>
        <span style="display:inline-flex;align-items:center;gap:8px;font-weight:600">
          <el-icon color="#2563EB" :size="16"><Tools /></el-icon>技术栈
        </span>
      </template>
      <div class="tech-wrap">
        <div v-for="t in techStack" :key="t.name" class="tech-chip"
          :style="{ background: t.bg, color: t.color, borderColor: t.color + '30' }">
          {{ t.name }}
        </div>
      </div>
    </el-card>

    <!-- ===== 项目说明 ===== -->
    <el-card>
      <template #header>
        <span style="display:inline-flex;align-items:center;gap:8px;font-weight:600">
          <el-icon color="#2563EB" :size="16"><Document /></el-icon>项目说明
        </span>
      </template>
      <div class="note-grid">
        <div class="note-block">
          <div class="note-title">
            <el-icon :size="14"><Aim /></el-icon>任务设计
          </div>
          <p class="note-text">
            分类与分割共用 ResNet-34 作为特征提取骨干，形成「一图两用」的多任务架构。
            分类头输出 37 类 Softmax 概率，分割头则通过 U-Net 解码器逐层上采样至 256×256 分辨率，
            输出宠物前景的像素级二值 Mask。
          </p>
        </div>
        <div class="note-block">
          <div class="note-title">
            <el-icon :size="14"><MagicStick /></el-icon>迁移学习
          </div>
          <p class="note-text">
            两个任务均从 ImageNet 预训练的 ResNet-34 出发，而非随机初始化。
            实验证明迁移学习使分类 Accuracy 提升约 <b>+30.3%</b>，分割 Dice 提升约 <b>+11.6%</b>，
            在仅 7390 张图片的小样本场景下效果尤为显著，最新测试集中有 <b>28 类达到 100% 准确率</b>。
          </p>
        </div>
        <div class="note-block">
          <div class="note-title">
            <el-icon :size="14"><FolderOpened /></el-icon>数据集
          </div>
          <p class="note-text">
            Oxford-IIIT Pet 包含 37 个品种（12 猫 + 25 狗），每类约 200 张，
            附带像素级 trimap 标注（前景 / 背景 / 边界三类）。
            划分比例 7:2:1，训练集约 5173 张，验证集约 1478 张，测试集约 739 张。
          </p>
        </div>
        <div class="note-block">
          <div class="note-title">
            <el-icon :size="14"><Monitor /></el-icon>系统架构
          </div>
          <p class="note-text">
            后端以 FastAPI + Uvicorn 承载推理服务，接收图片后同时调用分类模型和分割模型，
            返回 JSON（含品种、置信度、mask 路径等），前端 Vue 3 通过 REST API 请求并实时渲染可视化结果。
          </p>
        </div>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
/* ═══ Hero — Professional Banner ═══ */
.hero {
  position: relative; border-radius: var(--radius-lg, 16px);
  overflow: hidden; margin-bottom: 20px;
  background: linear-gradient(135deg, #0F172A 0%, #1E293B 50%, #0F172A 100%);
}
.hero-grid-bg { display: none; }
.hero-glow {
  position: absolute; width: 400px; height: 300px;
  right: -80px; top: -60px;
  background: radial-gradient(ellipse, rgba(59,130,246,.15) 0%, transparent 65%);
  pointer-events: none;
}
.hero-glow2 { display: none; }
.hero-content {
  position: relative; z-index: 1;
  padding: 40px 36px 32px;
}
.hero-badge {
  display: inline-flex; align-items: center; gap: 8px;
  background: rgba(59,130,246,.1);
  border: 1px solid rgba(59,130,246,.2);
  color: #93C5FD;
  font-size: 11.5px; font-weight: 700; letter-spacing: .4px;
  padding: 5px 14px; border-radius: 100px; margin-bottom: 16px;
}
.badge-dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: #3B82F6;
  box-shadow: 0 0 6px rgba(59,130,246,.6);
  animation: pulse 2s infinite;
}
.hero-title {
  margin: 0 0 12px; font-size: 32px; font-weight: 800;
  color: #F1F5F9; line-height: 1.25; letter-spacing: -.5px;
}
.hero-title-accent {
  color: #60A5FA;
  -webkit-text-fill-color: #60A5FA;
}
.hero-desc {
  margin: 0 0 28px; font-size: 14px; color: #94A3B8; line-height: 1.8; max-width: 600px;
}
.hero-desc b { color: #CBD5E1; font-weight: 700; }
.hero-stats {
  display: flex; gap: 0; flex-wrap: wrap;
  padding-top: 20px;
  border-top: 1px solid rgba(255,255,255,.08);
}
.hero-stat {
  padding: 0 28px;
  border-right: 1px solid rgba(255,255,255,.06);
}
.hero-stat:first-child { padding-left: 0; }
.hero-stat:last-child { border-right: 0; }
.hero-stat-value {
  font-size: 32px; font-weight: 800; line-height: 1.1; margin-bottom: 4px;
  font-family: 'Fira Code', monospace;
}
.hero-stat-value.hs-neutral { color: #F1F5F9; }
.hero-stat-value.hs-cls     { color: #60A5FA; }
.hero-stat-value.hs-seg     { color: #34D399; }
.hero-stat-unit  { font-size: 14px; font-weight: 500; color: #64748B; margin-left: 2px; }
.hero-stat-label { font-size: 11px; color: #94A3B8; letter-spacing: .3px; font-weight: 600; }

/* ═══ Pipeline — Clean Steps ═══ */
.pipeline {
  display: flex; align-items: center; gap: 0;
  flex-wrap: nowrap; overflow-x: auto; padding: 8px 0 10px;
}
.pipe-step-wrap { display: flex; align-items: center; gap: 0; flex-shrink: 0; }
.pipe-step {
  display: flex; flex-direction: column; align-items: center; gap: 6px;
  padding: 14px 18px; border-radius: var(--radius, 12px);
  background: var(--c-card, #FFFFFF);
  border: 1px solid var(--c-border, #E2E8F0);
  transition: all .2s ease; cursor: default; min-width: 110px;
  box-shadow: var(--shadow-xs);
}
.pipe-step:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
  border-color: var(--step-c, #BFDBFE);
}
.pipe-icon  {
  width: 40px; height: 40px; border-radius: 10px;
  border: 1px solid;
  display: flex; align-items: center; justify-content: center;
  margin-bottom: 2px;
}
.pipe-label { font-size: 13px; font-weight: 700; color: var(--c-dark, #0F172A); }
.pipe-sub   { font-size: 10.5px; color: var(--c-muted, #64748B); text-align: center; }
.pipe-arrow {
  font-size: 16px; padding: 0 6px; flex-shrink: 0;
  color: #CBD5E1;
}

/* ═══ Architecture Diagram ═══ */
.arch-diagram {
  background: linear-gradient(135deg, #F8FAFC, #EFF6FF);
  border: 1px solid #E2E8F0; border-radius: var(--radius, 12px);
  padding: 14px 18px;
}
.arch-svg {
  width: 100%; height: auto; max-height: 320px;
  display: block;
}
.arch-block rect { transition: all .25s ease; }
.arch-block:hover rect { filter: brightness(1.08); }
.arch-legend {
  display: flex; flex-wrap: wrap; gap: 18px; justify-content: center;
  margin-top: 10px; padding-top: 12px; border-top: 1px dashed #CBD5E1;
}
.al-item { display: inline-flex; align-items: center; gap: 6px; font-size: 12px; color: var(--c-text-body, #334155); font-weight: 600; }
.al-dot { display: inline-block; width: 10px; height: 10px; border-radius: 3px; }

/* ═══ Model Cards — Clean Metrics ═══ */
.model-header { display: flex; align-items: center; gap: 11px; }
.model-badge {
  padding: 4px 10px; border-radius: 6px;
  font-size: 11px; font-weight: 700; letter-spacing: .4px;
}
.model-body { padding: 0; }
.model-metrics { display: flex; align-items: flex-end; gap: 20px; margin-bottom: 14px; }
.model-metric-val {
  font-size: 34px; font-weight: 800; line-height: 1;
  font-family: 'Fira Code', monospace;
}
.model-metric-lbl { font-size: 11px; color: var(--c-muted); margin-top: 4px; font-weight: 600; }
.model-desc { font-size: 13px; color: var(--c-text-body, #334155); line-height: 1.8; margin: 0 0 14px; }
.model-tags { display: flex; flex-wrap: wrap; gap: 6px; }
.model-tag {
  padding: 4px 10px; border-radius: 6px;
  font-size: 11px; font-weight: 600; border: 1px solid;
  transition: all .2s ease; cursor: default;
}
.model-tag:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0,0,0,.06);
}

/* ═══ Extra Capabilities Grid ═══ */
.extra-grid {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px;
}
.extra-card {
  position: relative; display: flex; align-items: flex-start; gap: 12px;
  padding: 14px 16px; border-radius: 12px;
  background: linear-gradient(180deg, #FAFBFC 0%, #FFFFFF 100%);
  border: 1px solid var(--c-border, #E2E8F0);
  transition: all .25s cubic-bezier(.33,1,.68,1);
}
.extra-card:hover {
  transform: translateY(-2px);
  border-color: rgba(99,102,241,.4);
  box-shadow: 0 8px 22px rgba(15,23,42,.06);
}
.extra-card-icon {
  flex-shrink: 0; width: 40px; height: 40px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 4px 12px rgba(0,0,0,.1);
}
.extra-card-body { flex: 1; min-width: 0; }
.extra-card-title {
  font-size: 13.5px; font-weight: 700; color: var(--c-dark, #0F172A);
  line-height: 1.3; margin-bottom: 4px;
}
.extra-card-desc {
  font-size: 11.5px; color: var(--c-text-body, #475569); line-height: 1.65;
}
.extra-card-desc code {
  padding: 1px 6px; border-radius: 4px;
  background: rgba(99,102,241,.08); color: #4F46E5;
  font-family: 'Fira Code', monospace; font-size: 10.5px;
}
@media (max-width: 1100px) {
  .extra-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 700px) {
  .extra-grid { grid-template-columns: 1fr; }
}

/* ═══ Tech — Clean Chips ═══ */
.tech-wrap { display: flex; flex-wrap: wrap; gap: 8px; }
.tech-chip {
  padding: 6px 14px; border-radius: 8px;
  font-size: 13px; font-weight: 600; border: 1px solid;
  transition: all .2s ease; cursor: default;
}
.tech-chip:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0,0,0,.06);
}

/* ═══ Notes — Color-coded Cards ═══ */
.note-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.note-block {
  position: relative;
  padding: 16px 18px; border-radius: var(--radius, 12px);
  background: var(--c-card, #FFFFFF);
  border: 1px solid var(--c-border, #E2E8F0);
  transition: all .2s ease;
  overflow: hidden;
}
.note-block::before {
  content: '';
  position: absolute; top: 0; left: 0; right: 0; height: 3px;
}
.note-block:nth-child(1) { --note-c: #1E40AF; }
.note-block:nth-child(2) { --note-c: #059669; }
.note-block:nth-child(3) { --note-c: #F59E0B; }
.note-block:nth-child(4) { --note-c: #DC2626; }
.note-block::before { background: var(--note-c); }
.note-block:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
  border-color: #BFDBFE;
}
.note-title {
  display: inline-flex; align-items: center; gap: 6px;
  font-size: 14px; font-weight: 700; margin-bottom: 8px;
  color: var(--note-c);
}
.note-text  { font-size: 13px; color: var(--c-text-body, #334155); line-height: 1.8; margin: 0; }
.note-text b { font-weight: 700; color: var(--c-dark, #0F172A); }

@media (max-width: 900px) {
  .hero-content { padding: 28px 24px 24px; }
  .hero-title { font-size: 24px; }
  .hero-stats { gap: 0; }
  .hero-stat { padding: 0 20px; }
  .note-grid { grid-template-columns: 1fr; }
}

</style>
