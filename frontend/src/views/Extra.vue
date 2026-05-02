<script setup>
import { computed, onMounted, ref, nextTick } from 'vue'
import * as echarts from 'echarts'
import { getConfusionMatrix, getDatasetStats } from '../api'
import { getTopErrorClasses, resolveConfusionData } from '../utils/confusion'

const cmpChartEl = ref(null)
const errorDistrib = ref([])
const rareClassText = ref('staffordshire_bull_terrier（191）、scottish_terrier（199）')

const transferStats = {
  clsGain: '+30.3%',
  segGain: '+11.6%',
  baselineCls: 68.31,
  baselineSeg: 82.13,
}

const parameterGroups = [
  {
    title: '分类模型',
    accent: '#4f46e5',
    items: [
      ['Backbone', 'ResNet-34（ImageNet 预训练）'],
      ['Epochs', '100'],
      ['Batch Size', '32'],
      ['Optimizer', 'Adam · lr=3e-4'],
      ['Scheduler', 'ReduceLROnPlateau'],
      ['Loss', 'CrossEntropyLoss'],
      ['输入尺寸', '224 × 224'],
    ],
  },
  {
    title: '自定义分类模型（SimpleCNN）',
    accent: '#f59e0b',
    items: [
      ['Backbone', '4层卷积 + 2层全连接（随机初始化）'],
      ['Epochs', '50'],
      ['Batch Size', '32'],
      ['Optimizer', 'Adam · lr=1e-3'],
      ['Scheduler', 'ReduceLROnPlateau'],
      ['Loss', 'CrossEntropyLoss'],
      ['输入尺寸', '224 × 224'],
    ],
  },
  {
    title: '分割模型',
    accent: '#059669',
    items: [
      ['Backbone', 'U-Net + ResNet-34 Encoder'],
      ['Epochs', '30'],
      ['Batch Size', '8'],
      ['Optimizer', 'Adam · lr=1e-3'],
      ['Loss', 'BCEWithLogitsLoss'],
      ['输入尺寸', '256 × 256'],
    ],
  },
]

const limitationItems = computed(() => [
  ['相似品种混淆', '分类', 'Abyssinian、Bengal、Siamese 等外观接近，误差集中在纹理和颜色相近的类别。', '#4f46e5'],
  ['分割边界模糊', '分割', '细毛发、轮廓转折和 trimap 边界区域仍是 Dice 波动的主要来源。', '#d97706'],
  ['复杂场景泛化', '泛化', '遮挡、复杂背景、幼年宠物或艺术化图像会降低分类和分割稳定性。', '#0f766e'],
  ['小目标宠物', '推理', '主体占比过低时分割结果会变粗，实际使用时更适合先裁剪主体区域。', '#0284c7'],
  ['类别轻微不平衡', '采样', `${rareClassText.value} 样本略少，尾部类别召回更容易受随机划分影响。`, '#dc2626'],
  ['部署资源约束', '部署', '两个模型串行推理在 CPU 环境下约 400–800ms，后续可做并行推理或蒸馏。', '#7c3aed'],
])

const futureWork = [
  ['多任务联合训练', '统一优化分类与分割损失，观察共享特征是否带来协同收益。', '#4f46e5'],
  ['注意力机制', '在骨干中加入 CBAM 或 SE，提高对面部、纹理和轮廓区域的关注。', '#059669'],
  ['更强基线对比', '加入 EfficientNet、Swin Transformer 等模型，做更完整的横向比较。', '#d97706'],
  ['半监督学习', '利用未标注宠物图像扩展预训练阶段，增强复杂场景泛化。', '#0284c7'],
]

const summaryCards = computed(() => {
  const leading = errorDistrib.value[0]
  return [
    ['分类提升', transferStats.clsGain, `98.65% / ${transferStats.baselineCls}%`, 'blue'],
    ['分割提升', transferStats.segGain, `93.74 / ${transferStats.baselineSeg}`, 'green'],
    ['最高错误率', leading ? `${leading.rate}%` : '—', leading ? shortLabel(leading.breed) : '等待数据', 'red'],
    ['低样本类别', '2 类', '最低 191 / 199 张', 'cyan'],
  ]
})

const insightItems = computed(() => {
  const first = errorDistrib.value[0]
  const second = errorDistrib.value[1]
  return [
    first
      ? `最高错误类别为 ${first.breed}，错误率 ${first.rate}%（${first.errorCount}/${first.total}）。`
      : '逐类错误率正在从混淆矩阵读取。',
    second
      ? `${second.breed} 等类别的误差说明相似品种仍是主要挑战。`
      : '错误类别排名会随评估产物自动更新。',
    `当前低样本类别为 ${rareClassText.value}，后续可使用重采样或类平衡损失。`,
  ]
})

const topErrorHighlights = computed(() => errorDistrib.value.slice(0, 4))

onMounted(async () => {
  try {
    const [cmRes, statsRes] = await Promise.all([
      getConfusionMatrix(),
      getDatasetStats(),
    ])
    const { labels, matrix } = resolveConfusionData(cmRes.data)
    errorDistrib.value = getTopErrorClasses(labels, matrix, 6)

    const rareClasses = (statsRes.data?.class_distribution ?? [])
      .slice()
      .sort((a, b) => a.count - b.count || a.name.localeCompare(b.name))
      .filter(item => item.count < 200)
      .slice(0, 2)
      .map(item => `${item.name}（${item.count}）`)
      .join('、')

    if (rareClasses) rareClassText.value = rareClasses
  } catch (error) {
    console.error('Extra fetch failed', error)
  }

  await nextTick()
  renderCmpChart()
})

function shortLabel(label) {
  return label.length > 18 ? `${label.slice(0, 16)}…` : label
}

function renderCmpChart() {
  if (!cmpChartEl.value) return
  echarts.init(cmpChartEl.value).setOption({
    color: ['#2563eb', '#94a3b8', '#f59e0b'],
    tooltip: {
      trigger: 'axis',
      formatter: (params) =>
        `${params[0].axisValue}<br/>${params.map(item => `${item.seriesName}: <b>${item.value}</b>`).join('<br/>')}`,
    },
    legend: { data: ['ResNet-34 预训练', 'ResNet-34 随机初始化', 'SimpleCNN 自定义'], top: 0, right: 0, textStyle: { fontSize: 11 } },
    grid: { left: 24, right: 12, bottom: 24, top: 42, containLabel: true },
    xAxis: {
      type: 'category',
      data: ['分类 Acc', '分割 Dice×100'],
      axisLabel: { color: '#64748b', fontSize: 11 },
      axisLine: { lineStyle: { color: '#dbe3ef' } },
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      splitNumber: 5,
      axisLabel: { color: '#94a3b8' },
      splitLine: { lineStyle: { color: '#eef2f7' } },
    },
    series: [
      {
        name: 'ResNet-34 预训练',
        type: 'bar',
        barWidth: 24,
        data: [98.65, 93.74],
        itemStyle: { borderRadius: [4, 4, 0, 0] },
        label: { show: true, position: 'top', formatter: '{c}', color: '#334155', fontWeight: 700 },
      },
      {
        name: 'ResNet-34 随机初始化',
        type: 'bar',
        barWidth: 24,
        data: [68.31, 82.13],
        itemStyle: { borderRadius: [4, 4, 0, 0] },
        label: { show: true, position: 'top', formatter: '{c}', color: '#64748b', fontWeight: 600 },
      },
      {
        name: 'SimpleCNN 自定义',
        type: 'bar',
        barWidth: 24,
        data: [51.15, 0],
        itemStyle: { borderRadius: [4, 4, 0, 0] },
        label: { show: true, position: 'top', formatter: '{c}', color: '#f59e0b', fontWeight: 600 },
      },
    ],
  })
}

</script>

<template>
  <div class="extra-page">
    <section class="report">
      <header class="report-head">
        <div>
          <div class="label">扩展分析</div>
          <h2>实验补充视图</h2>
          <p>聚焦迁移学习收益、错误来源、模型边界和后续优化方向。</p>
        </div>
      </header>

      <div class="metric-strip">
        <div v-for="[label, value, helper, tone] in summaryCards" :key="label" class="metric" :class="tone">
          <span>{{ label }}</span>
          <strong>{{ value }}</strong>
          <small>{{ helper }}</small>
        </div>
      </div>
    </section>

    <section class="report">
      <div class="two-col primary">
        <article class="block">
          <div class="block-head">
            <div>
              <h3>三模型对比</h3>
              <p>ResNet-34 预训练 / 随机初始化 / 自定义 SimpleCNN 对比。</p>
            </div>
            <span class="pill">核心实验</span>
          </div>
          <div ref="cmpChartEl" class="chart compare-chart"></div>
        </article>

        <article class="block quiet">
          <div class="block-head">
            <div>
              <h3>关键结论</h3>
              <p>从实测结果提炼出的页面摘要。</p>
            </div>
          </div>

          <div class="insights">
            <p v-for="item in insightItems" :key="item">{{ item }}</p>
          </div>

          <div class="error-list">
            <div v-for="item in topErrorHighlights" :key="item.breed" class="error-row">
              <strong>{{ item.rate }}%</strong>
              <div>
                <b>{{ item.breed }}</b>
                <small>{{ item.errorCount }}/{{ item.total }} · {{ item.similar }}</small>
              </div>
            </div>
          </div>
        </article>
      </div>
    </section>

    <section class="report">
      <article class="block">
        <div class="block-head">
          <div>
            <h3>高错误率品种 Top-6</h3>
            <p>来自 confusion_matrix.json 的逐类实测错误率，按错误率降序。</p>
          </div>
          <span class="pill danger">评估集实测</span>
        </div>
        <div class="error-table" v-if="errorDistrib.length">
          <div class="et-row et-head">
            <span class="et-rank">#</span>
            <span class="et-breed">品种</span>
            <span class="et-rate">错误率</span>
            <span class="et-bar">分布</span>
            <span class="et-count">误判数</span>
          </div>
          <div v-for="(item, idx) in errorDistrib" :key="item.breed" class="et-row">
            <span class="et-rank" :class="idx === 0 ? 'et-rank-top' : ''">{{ idx + 1 }}</span>
            <span class="et-breed">{{ item.breed }}</span>
            <span class="et-rate" :class="item.rate >= 10 ? 'et-rate-high' : ''">{{ item.rate }}%</span>
            <span class="et-bar">
              <span class="et-bar-track">
                <span class="et-bar-fill" :style="{
                  width: (item.rate / Math.max(...errorDistrib.map(e => e.rate)) * 100) + '%',
                  background: item.rate >= 10 ? 'linear-gradient(90deg,#FCA5A5,#DC2626)' : 'linear-gradient(90deg,#FCD34D,#F59E0B)'
                }"></span>
              </span>
            </span>
            <span class="et-count">{{ item.errorCount ? `${item.errorCount}/${item.total}` : '—' }}</span>
          </div>
        </div>
      </article>
    </section>

    <section class="report">
      <article class="block">
        <div class="block-head">
          <div>
            <h3>超参数配置</h3>
            <p>按分类与分割任务拆分，三组模型配置一目了然。</p>
          </div>
        </div>

        <div class="params">
          <div v-for="group in parameterGroups" :key="group.title" class="param-group">
            <h4 :style="{ color: group.accent }">{{ group.title }}</h4>
            <div v-for="[label, value] in group.items" :key="`${group.title}-${label}`" class="param-row">
              <span>{{ label }}</span>
              <b>{{ value }}</b>
            </div>
          </div>
        </div>
      </article>
    </section>

    <section class="report">
      <div class="section-head">
        <h3>模型局限性</h3>
        <p>按分类、分割、泛化、推理、采样、部署 6 个维度归纳。</p>
      </div>
      <div class="note-grid">
        <div v-for="[title, label, desc, color] in limitationItems" :key="title" class="note" :style="{ '--accent': color }">
          <span>{{ label }}</span>
          <b>{{ title }}</b>
          <p>{{ desc }}</p>
        </div>
      </div>
    </section>

    <section class="report">
      <div class="section-head">
        <h3>未来研究方向</h3>
        <p>围绕训练方式、模型结构和数据利用继续扩展。</p>
      </div>
      <div class="future-grid">
        <div v-for="[title, desc, color] in futureWork" :key="title" class="future" :style="{ '--accent': color }">
          <b>{{ title }}</b>
          <p>{{ desc }}</p>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
/* ═══ Page ═══ */
.extra-page { display: grid; gap: 14px; }

/* ═══ Report Card — Clean ═══ */
.report {
  position: relative; overflow: hidden;
  background: var(--c-card, #FFFFFF);
  border: 1px solid var(--c-border, #E2E8F0);
  border-radius: var(--radius, 12px);
  box-shadow: var(--shadow);
  transition: all .2s ease;
}
.report::before {
  content: '';
  position: absolute; top: 0; left: 0; right: 0; height: 3px;
  background: var(--c-primary, #1E40AF);
}
.report:hover { box-shadow: var(--shadow-md); transform: translateY(-1px); }

.report-head { padding: 18px 18px 0; }
.label {
  color: var(--c-primary, #1E40AF);
  font-size: 12px; font-weight: 700;
}
.report h2, .block-head h3, .section-head h3 { margin: 0; color: var(--c-dark, #0F172A); font-weight: 800; letter-spacing: -.02em; }
.report h2 { margin-top: 6px; font-size: 24px; line-height: 1.25; }
.report-head p, .block-head p, .section-head p { margin: 5px 0 0; color: var(--c-muted, #64748B); font-size: 12.5px; line-height: 1.65; }

/* ═══ Metric Strip — Clean Indicators ═══ */
.metric-strip { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 0; margin-top: 16px; border-top: 1px solid var(--c-border, #E2E8F0); }
.metric { position: relative; min-height: 88px; padding: 14px 16px; border-right: 1px solid var(--c-border, #E2E8F0); }
.metric:last-child { border-right: 0; }
.metric::before {
  content: ''; position: absolute; left: 16px; top: 14px; width: 20px; height: 3px;
  border-radius: 99px; background: var(--c-primary, #1E40AF);
}
.metric.green::before { background: var(--c-green, #059669); }
.metric.red::before   { background: var(--c-red, #DC2626); }
.metric.cyan::before  { background: var(--c-cyan, #0891B2); }
.metric span { display: block; margin-top: 10px; color: var(--c-muted, #64748B); font-size: 12px; font-weight: 600; }
.metric strong { display: block; margin-top: 7px; color: var(--c-dark, #0F172A); font-size: 24px; line-height: 1; font-weight: 800; font-family: 'Fira Code', monospace; letter-spacing: -.02em; }
.metric small { display: block; margin-top: 7px; color: var(--c-muted, #64748B); font-size: 11px; line-height: 1.4; }

/* ═══ Two-col ═══ */
.two-col { display: grid; grid-template-columns: minmax(0, 1fr) minmax(320px, .9fr); gap: 0; }
.two-col.primary { grid-template-columns: minmax(0, 1.35fr) minmax(300px, .85fr); }
.block { padding: 16px; border-right: 1px solid var(--c-border, #E2E8F0); }
.block:last-child { border-right: 0; }
.block.quiet { background: var(--c-bg, #F8FAFC); }
.block-head, .section-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; margin-bottom: 12px; }
.block-head h3, .section-head h3 { font-size: 17px; line-height: 1.3; }

.pill {
  flex-shrink: 0; padding: 4px 9px; border-radius: 999px;
  background: rgba(30,64,175,.08); color: var(--c-primary, #1E40AF);
  border: 1px solid rgba(30,64,175,.2); font-size: 11px; font-weight: 700;
}
.pill.danger { color: var(--c-red, #DC2626); background: rgba(220,38,38,.08); border-color: rgba(220,38,38,.2); }

.chart { width: 100%; }
.compare-chart { height: 280px; }

/* ─── Error Table ─── */
.error-table {
  margin-top: 8px;
  border: 1px solid var(--c-border, #E2E8F0);
  border-radius: 10px; overflow: hidden;
  background: var(--c-card, #FFFFFF);
}
.et-row {
  display: grid;
  grid-template-columns: 40px minmax(140px, 1fr) 70px minmax(120px, 1.4fr) 80px;
  gap: 12px; align-items: center;
  padding: 10px 14px;
  border-bottom: 1px solid var(--c-border, #E2E8F0);
  font-size: 13px;
}
.et-row:last-child { border-bottom: 0; }
.et-row:not(.et-head):hover { background: #F8FAFC; }
.et-head {
  background: #F8FAFC;
  font-size: 11px; font-weight: 700;
  color: var(--c-muted, #64748B); letter-spacing: .3px;
  text-transform: uppercase;
}
.et-rank {
  width: 24px; height: 24px; border-radius: 6px;
  background: #F1F5F9; color: #94A3B8;
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 800; font-family: 'Fira Code', monospace;
}
.et-head .et-rank { background: transparent; }
.et-rank-top {
  background: linear-gradient(135deg, #FCA5A5, #DC2626) !important;
  color: #fff !important;
  box-shadow: 0 2px 6px rgba(220,38,38,.25);
}
.et-breed {
  font-weight: 700; color: var(--c-dark, #0F172A);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.et-rate {
  font-weight: 800; font-family: 'Fira Code', monospace;
  color: #F59E0B; font-size: 14px;
}
.et-rate-high { color: #DC2626; }
.et-bar-track {
  display: block; width: 100%; height: 8px;
  background: #F1F5F9; border-radius: 100px; overflow: hidden;
}
.et-bar-fill { display: block; height: 100%; border-radius: 100px; transition: width .4s var(--ease, ease); }
.et-count {
  text-align: right; font-family: 'Fira Code', monospace;
  font-size: 12px; color: var(--c-muted, #64748B);
}

/* Insights */
.insights { display: grid; gap: 9px; }
.insights p {
  margin: 0; padding-left: 12px;
  border-left: 3px solid var(--c-primary, #1E40AF);
  color: var(--c-text-body, #334155); font-size: 12.5px; line-height: 1.75;
}

/* Error list */
.error-list { display: grid; gap: 8px; margin-top: 14px; padding-top: 14px; border-top: 1px solid var(--c-border, #E2E8F0); }
.error-row {
  display: grid; grid-template-columns: 50px minmax(0, 1fr); gap: 10px; align-items: center; padding: 8px 0;
  transition: all .2s ease;
}
.error-row:hover { transform: translateX(3px); }
.error-row strong { color: var(--c-red, #DC2626); font-size: 17px; }
.error-row b, .note b, .future b { display: block; color: var(--c-dark, #0F172A); font-size: 13px; font-weight: 800; }
.error-row small { display: block; color: var(--c-muted, #64748B); font-size: 11px; line-height: 1.45; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

/* ═══ Params — Clean Groups ═══ */
.params { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }
.param-group {
  position: relative; overflow: hidden;
  border: 1px solid var(--c-border, #E2E8F0); border-radius: var(--radius, 12px);
  background: var(--c-card, #FFFFFF);
}
.param-group::before {
  content: '';
  position: absolute; top: 0; left: 0; right: 0; height: 3px;
}
.param-group:nth-child(1) { --pg-c: var(--c-primary, #1E40AF); }
.param-group:nth-child(2) { --pg-c: var(--c-green, #059669); }
.param-group:nth-child(3) { --pg-c: var(--c-accent, #F59E0B); }
.param-group:nth-child(1)::before { background: var(--pg-c); }
.param-group:nth-child(2)::before { background: var(--pg-c); }
.param-group:nth-child(3)::before { background: var(--pg-c); }
.param-group h4 {
  margin: 0; padding: 10px 12px;
  background: var(--c-bg, #F8FAFC);
  font-size: 13px; font-weight: 700; color: var(--c-dark, #0F172A);
}
.param-row { display: grid; grid-template-columns: 90px minmax(0, 1fr); gap: 8px; padding: 8px 12px; border-top: 1px solid var(--c-border, #E2E8F0); }
.param-row span { color: var(--c-muted, #64748B); font-size: 12px; font-weight: 600; }
.param-row b { color: var(--c-text-body, #334155); font-size: 12.5px; line-height: 1.5; font-weight: 600; }

/* ═══ Section head ═══ */
.section-head { padding: 16px 16px 0; position: relative; }
.section-head::before {
  content: ''; position: absolute; left: 16px; bottom: -12px; width: 40px; height: 3px;
  border-radius: 999px;
  background: var(--c-primary, #1E40AF);
}

/* ═══ Note / Future grids — Clean ═══ */
.note-grid, .future-grid { display: grid; gap: 0; border-top: 1px solid var(--c-border, #E2E8F0); }
.note-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.future-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); }
.note, .future {
  position: relative; padding: 14px 16px;
  border-right: 1px solid var(--c-border, #E2E8F0); border-bottom: 1px solid var(--c-border, #E2E8F0);
  background: var(--c-card, #FFFFFF);
  transition: all .2s ease;
}
.note::before, .future::before {
  content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 3px;
  background: var(--accent);
}
.note:hover, .future:hover {
  background: var(--c-bg, #F8FAFC);
  transform: translateX(2px);
}
.note:nth-child(3n), .future:nth-child(4n) { border-right: 0; }
.note:nth-last-child(-n + 3), .future:nth-last-child(-n + 4) { border-bottom: 0; }
.note span {
  display: inline-flex; margin-bottom: 7px; padding: 3px 8px; border-radius: 999px;
  background: color-mix(in srgb, var(--accent) 10%, white); color: var(--accent);
  font-size: 11px; font-weight: 800;
}
.note p, .future p { margin: 7px 0 0; color: var(--c-muted, #64748B); font-size: 12px; line-height: 1.7; }

/* ═══ Responsive ═══ */
@media (max-width: 1180px) {
  .metric-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .metric:nth-child(2) { border-right: 0; }
  .metric:nth-child(-n + 2) { border-bottom: 1px solid var(--c-border, #E2E8F0); }
  .two-col, .two-col.primary, .note-grid, .future-grid { grid-template-columns: 1fr; }
  .block, .note, .future { border-right: 0; }
  .block:first-child { border-bottom: 1px solid var(--c-border, #E2E8F0); }
  .note, .future { border-bottom: 1px solid var(--c-border, #E2E8F0); }
  .note:last-child, .future:last-child { border-bottom: 0; }
  .params { grid-template-columns: 1fr; }
}
@media (max-width: 760px) {
  .extra-page { gap: 10px; }
  .report { border-radius: 12px; }
  .report-head { padding: 14px 14px 0; }
  .report h2 { font-size: 21px; }
  .metric-strip { grid-template-columns: 1fr; }
  .metric, .metric:nth-child(2) { border-right: 0; }
  .metric:nth-child(-n + 3) { border-bottom: 1px solid var(--c-border, #E2E8F0); }
  .metric { min-height: auto; display: grid; grid-template-columns: 68px minmax(0, 1fr); column-gap: 8px; row-gap: 3px; padding: 10px 14px; }
  .metric::before { left: 0; top: 0; bottom: 0; width: 3px; height: auto; border-radius: 0; }
  .metric span, .metric strong, .metric small { margin-top: 0; }
  .metric span { align-self: center; font-size: 11px; }
  .metric strong { font-size: 19px; text-align: right; }
  .metric small { grid-column: 2; text-align: right; }
  .block, .section-head, .note, .future { padding-left: 14px; padding-right: 14px; }
  .block-head, .section-head { flex-direction: column; margin-bottom: 8px; }
  .compare-chart { height: 230px; }
  .et-row { grid-template-columns: 32px minmax(100px, 1fr) 56px 70px; gap: 8px; padding: 8px 10px; font-size: 12px; }
  .et-bar { display: none; }
  .block.quiet { order: -1; }
  .param-row { grid-template-columns: 84px minmax(0, 1fr); }
}

</style>
