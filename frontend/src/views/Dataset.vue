<script setup>
import { onMounted, ref, nextTick, computed } from 'vue'
import * as echarts from 'echarts'
import { getDatasetStats, getDatasetSamples, getAugmentationPreview } from '../api'

const stats   = ref(null)
const samples = ref([])
const barChartEl  = ref(null)
const pieChartEl  = ref(null)
const distExpanded = ref(false)

const augItems = ref([])
const augBreed = ref('samoyed')
const augLoading = ref(false)
const originalAugUrl = computed(() => {
  const orig = augItems.value.find(x => x.key === 'original')
  return orig ? BACKEND + orig.url : ''
})
const augBreedOptions = ['samoyed', 'Abyssinian', 'Bengal', 'pug', 'beagle', 'Siamese', 'boxer', 'Persian']

const BACKEND = 'http://127.0.0.1:8000'

const CAT_BREEDS = ['Abyssinian','Bengal','Birman','Bombay','British_Shorthair',
                    'Egyptian_Mau','Maine_Coon','Persian','Ragdoll','Russian_Blue',
                    'Siamese','Sphynx']

const statCards = computed(() => {
  if (!stats.value) return []
  const s = stats.value
  return [
    { icon: '📦', value: s.name,         label: '数据集名称', accent: false },
    { icon: '🏷️', value: s.num_classes,  label: '品种类别数', unit: '类',  accent: true },
    { icon: '🖼️', value: Number(s.total_samples).toLocaleString(),
                                          label: '图片总数',   unit: '张',  accent: true },
    { icon: '✂️',  value: `${s.split.train*100} / ${s.split.val*100} / ${s.split.test*100}`,
                                          label: '训练/验证/测试', unit: '%', accent: false },
  ]
})

const catCount = computed(() => {
  if (!stats.value) return 0
  return stats.value.class_distribution
    .filter(d => CAT_BREEDS.includes(d.name))
    .reduce((a, b) => a + b.count, 0)
})
const dogCount = computed(() => {
  if (!stats.value) return 0
  return stats.value.total_samples - catCount.value
})

async function loadAugmentation(breed) {
  augLoading.value = true
  try {
    const res = await getAugmentationPreview(breed)
    augItems.value = res.data.items || []
  } catch (e) { console.error('Augmentation fetch failed', e) }
  finally { augLoading.value = false }
}

onMounted(async () => {
  try {
    const [statsRes, samplesRes] = await Promise.all([
      getDatasetStats(),
      getDatasetSamples(),
    ])
    stats.value   = statsRes.data
    samples.value = samplesRes.data
    await nextTick()
    renderBarChart(statsRes.data.class_distribution)
    renderPieChart()
    loadAugmentation(augBreed.value)
  } catch (e) {
    console.error('Dataset stats fetch failed', e)
  }
})

function renderBarChart(dist) {
  if (!barChartEl.value) return
  const chart = echarts.init(barChartEl.value)
  const catSet = new Set(CAT_BREEDS)
  /* 按数量升序，把异常值（< 200）置顶突出 */
  const sorted = [...dist].sort((a, b) => a.count - b.count)
  const STANDARD = 200
  const minCount = Math.min(...sorted.map(d => d.count))
  /* x 轴起点贴近异常值，让差异可见 */
  const axisMin = Math.max(0, minCount - 5)

  chart.setOption({
    tooltip: {
      trigger: 'axis', axisPointer: { type: 'shadow' },
      formatter: (p) => {
        const d = p[0]
        const isCat = catSet.has(d.name)
        const delta = d.value - STANDARD
        return `<b>${d.name}</b><br/>样本数: <b>${d.value}</b> ${delta < 0 ? `<span style="color:#F59E0B">(${delta})</span>` : ''}<br/>类型: ${isCat ? '🐱 猫科' : '🐶 犬科'}`
      }
    },
    grid: { left: 150, right: 60, top: 10, bottom: 36 },
    xAxis: {
      type: 'value', name: '样本数', min: axisMin, max: STANDARD + 2,
      nameTextStyle: { color: '#94a3b8', fontSize: 11 },
      axisLabel: { color: '#94a3b8', fontSize: 11 },
      splitLine: { lineStyle: { color: '#F1F5F9' } },
      /* 标准线 */
    },
    yAxis: {
      type: 'category',
      data: sorted.map(d => d.name),
      axisLabel: {
        fontSize: 11,
        color: (val) => catSet.has(val) ? '#A855F7' : '#3B82F6',
        fontWeight: (val) => sorted.find(d => d.name === val)?.count < STANDARD ? 700 : 500,
      },
      axisTick: { show: false },
      axisLine: { lineStyle: { color: '#E2E8F0' } }
    },
    series: [{
      type: 'bar',
      data: sorted.map(d => {
        const below = d.count < STANDARD
        const isCat = catSet.has(d.name)
        return {
          value: d.count,
          itemStyle: {
            color: below
              ? new echarts.graphic.LinearGradient(1, 0, 0, 0, [{ offset: 0, color: '#FCD34D' }, { offset: 1, color: '#F59E0B' }])
              : (isCat
                  ? new echarts.graphic.LinearGradient(1, 0, 0, 0, [{ offset: 0, color: '#E9D5FF' }, { offset: 1, color: '#A855F7' }])
                  : new echarts.graphic.LinearGradient(1, 0, 0, 0, [{ offset: 0, color: '#BFDBFE' }, { offset: 1, color: '#3B82F6' }])),
            borderRadius: [0, 4, 4, 0],
          }
        }
      }),
      barMaxWidth: 14,
      label: {
        show: true, position: 'right', fontSize: 11,
        formatter: (p) => p.value < STANDARD ? `${p.value} ⚠` : `${p.value}`,
        color: (p) => p.value < STANDARD ? '#F59E0B' : '#94A3B8',
        fontWeight: (p) => p.value < STANDARD ? 700 : 500,
      },
      markLine: {
        symbol: 'none',
        silent: true,
        lineStyle: { color: '#94A3B8', type: 'dashed', width: 1.2 },
        label: { show: false },
        data: [{ xAxis: STANDARD }]
      }
    }]
  })
}

function renderPieChart() {
  if (!pieChartEl.value || !stats.value) return
  const cat = catCount.value
  const dog = dogCount.value
  echarts.init(pieChartEl.value).setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} 张 ({d}%)' },
    legend: { orient: 'vertical', right: 10, top: 'center',
              textStyle: { fontSize: 12, color: '#374151' } },
    series: [{
      type: 'pie',
      radius: ['48%', '76%'],
      center: ['40%', '50%'],
      avoidLabelOverlap: false,
      label: { show: false },
      emphasis: {
        label: { show: true, fontSize: 14, fontWeight: 700, formatter: '{b}\n{c} 张' }
      },
      data: [
        {
          value: cat, name: '猫科 (12 类)',
          itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#f472b6' }, { offset: 1, color: '#a855f7' }
          ])}
        },
        {
          value: dog, name: '犬科 (25 类)',
          itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#22d3ee' }, { offset: 1, color: '#6366f1' }
          ])}
        }
      ]
    }]
  })
}
</script>

<template>
  <!-- 已加载 -->
  <div v-if="stats">
    <!-- 统计卡片 -->
    <div class="stat-grid">
      <div v-for="c in statCards" :key="c.label" class="stat-tile">
        <div class="stat-icon">{{ c.icon }}</div>
        <div class="stat-val" :class="{ accent: c.accent }">
          {{ c.value }}<span v-if="c.unit" class="stat-unit"> {{ c.unit }}</span>
        </div>
        <div class="stat-lbl">{{ c.label }}</div>
      </div>
    </div>

    <!-- 猫狗构成 + 预处理 增强 -->
    <div class="dataset-overview-grid">
      <!-- 猫狗饼图 -->
      <el-card class="overview-card">
          <template #header><span style="font-weight:600">🐾 猫科 / 犬科 构成</span></template>
          <div ref="pieChartEl" style="width:100%;height:200px"></div>
          <div class="species-row">
            <div class="species-badge cat">
              <span class="sp-dot cat-dot"></span>
              猫科 12 类 · {{ catCount.toLocaleString() }} 张
            </div>
            <div class="species-badge dog">
              <span class="sp-dot dog-dot"></span>
              犬科 25 类 · {{ dogCount.toLocaleString() }} 张
            </div>
          </div>
      </el-card>

      <!-- 预处理 + 增强 -->
      <div class="prep-grid">
            <el-card class="overview-card">
              <template #header><span style="font-weight:600">🖼️ 图像预处理</span></template>
              <el-descriptions :column="1" border>
                <el-descriptions-item label="分类输入尺寸">224 × 224 px</el-descriptions-item>
                <el-descriptions-item label="分割输入尺寸">256 × 256 px</el-descriptions-item>
                <el-descriptions-item label="归一化均值">[0.485, 0.456, 0.406]</el-descriptions-item>
                <el-descriptions-item label="归一化标准差">[0.229, 0.224, 0.225]</el-descriptions-item>
              </el-descriptions>
            </el-card>
            <el-card class="overview-card">
              <template #header><span style="font-weight:600">🔄 数据增强（训练集）</span></template>
              <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px">
                <el-tag v-for="aug in stats.augmentation.train" :key="aug"
                  type="success" effect="plain" size="small">{{ aug }}</el-tag>
              </div>
              <div style="color:#64748b;font-size:12.5px">
                验证 / 测试集仅做 Resize + Normalize，不做随机增强
              </div>
            </el-card>
      </div>
    </div>

    <!-- 样本展示：原图 + Mask + Overlay -->
    <el-card style="margin-bottom:16px" v-if="samples.length">
      <template #header>
        <span style="font-weight:600">🖼️ 数据集样本展示（原图 · Trimap · 叠加）</span>
      </template>
      <div class="sample-main-grid">
        <div v-for="s in samples" :key="s.breed" class="sample-card">
          <div class="sample-breed-label">
            <span class="sample-species-dot"
              :style="{ background: s.species === '猫科' ? '#a855f7' : '#6366f1' }"></span>
            {{ s.breed }}
            <el-tag :type="s.species === '猫科' ? 'warning' : 'primary'"
              size="small" effect="plain" style="margin-left:4px">{{ s.species }}</el-tag>
          </div>
          <div class="sample-imgs">
            <div class="sample-img-wrap">
              <img :src="BACKEND + s.image_url" class="sample-img" />
              <div class="sample-img-cap">原图</div>
            </div>
            <div class="sample-img-wrap">
              <img :src="BACKEND + s.mask_url" class="sample-img" />
              <el-tooltip placement="top" effect="dark">
                <template #content>
                  <div style="font-size:12px;line-height:1.7;max-width:240px">
                    <b style="color:#FCD34D">Trimap = Tri-region Map</b><br/>
                    像素级三类标注，是分割任务的标注格式：<br/>
                    <span style="color:#4ADE80">●</span> 前景 (foreground，宠物)<br/>
                    <span style="color:#94A3B8">●</span> 背景 (background)<br/>
                    <span style="color:#F59E0B">●</span> 边界 (boundary，毛发/轮廓不确定区)
                  </div>
                </template>
                <div class="sample-img-cap with-info">
                  Trimap Mask
                  <el-icon :size="11" style="margin-left:3px;vertical-align:middle"><InfoFilled /></el-icon>
                </div>
              </el-tooltip>
            </div>
            <div class="sample-img-wrap">
              <img :src="BACKEND + s.overlay_url" class="sample-img" />
              <div class="sample-img-cap">叠加可视化</div>
            </div>
          </div>
        </div>
      </div>
      <div class="sample-legend">
        <span class="sl-dot" style="background:#48c78e"></span>前景（宠物）
        <span class="sl-dot" style="background:#1e1e28;margin-left:14px"></span>背景
        <span class="sl-dot" style="background:#ffc832;margin-left:14px"></span>边界区域
      </div>
    </el-card>

    <!-- 数据增强预览 -->
    <el-card style="margin-bottom:16px">
      <template #header>
        <div style="display:flex;align-items:center;justify-content:space-between">
          <span style="font-weight:600">🔄 数据增强效果预览</span>
          <div style="display:flex;align-items:center;gap:8px">
            <span style="font-size:12px;color:#64748b">选择品种：</span>
            <el-select v-model="augBreed" size="small" style="width:140px"
              @change="loadAugmentation">
              <el-option v-for="b in augBreedOptions" :key="b" :label="b" :value="b" />
            </el-select>
          </div>
        </div>
      </template>
      <div v-loading="augLoading">
        <div class="aug-tip" v-if="augItems.length">
          <el-icon :size="13"><InfoFilled /></el-icon>
          <span>悬停任一卡片可叠加显示<b>原图</b>对比，快速识别增强变化</span>
        </div>
        <div class="aug-grid" v-if="augItems.length">
          <div v-for="(item, idx) in augItems" :key="item.key"
            class="aug-card" :class="{ 'aug-card-original': item.key === 'original' }">
            <div class="aug-img-wrap">
              <img :src="BACKEND + item.url" class="aug-img aug-img-after" :alt="item.name" />
              <!-- hover 显示原图 -->
              <img v-if="item.key !== 'original' && originalAugUrl"
                :src="originalAugUrl" class="aug-img aug-img-before" alt="原图对比" />
              <span v-if="item.key !== 'original'" class="aug-hover-hint">悬停看原图</span>
              <span v-else class="aug-original-tag">基线</span>
            </div>
            <div class="aug-info">
              <div class="aug-name">{{ item.name }}</div>
              <div class="aug-desc">{{ item.desc }}</div>
            </div>
          </div>
        </div>
        <el-empty v-else description="暂无数据" :image-size="60" />
      </div>
    </el-card>

    <!-- 分布图 -->
    <el-card>
      <template #header>
        <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap">
          <div>
            <div style="font-weight:700;font-size:14px">37 类样本分布</div>
            <div style="font-size:11px;color:#94A3B8;margin-top:2px;font-weight:500">
              按样本数升序，X 轴聚焦末段（虚线为标准 200 张/类）；不足 200 张的类别标橙色 ⚠
            </div>
          </div>
          <div style="display:flex;gap:12px;align-items:center;font-size:12px;color:#475569;flex-wrap:wrap;justify-content:flex-end">
            <span style="display:inline-flex;align-items:center;gap:5px">
              <span class="legend-dot" style="background:linear-gradient(90deg,#FCD34D,#F59E0B)"></span>样本不足
            </span>
            <span style="display:inline-flex;align-items:center;gap:5px">
              <span class="legend-dot" style="background:linear-gradient(90deg,#E9D5FF,#A855F7)"></span>猫科
            </span>
            <span style="display:inline-flex;align-items:center;gap:5px">
              <span class="legend-dot" style="background:linear-gradient(90deg,#BFDBFE,#3B82F6)"></span>犬科
            </span>
            <el-button size="small" plain @click="distExpanded = !distExpanded"
              style="font-weight:600">
              <el-icon style="margin-right:3px">
                <component :is="distExpanded ? 'ArrowUp' : 'ArrowDown'" />
              </el-icon>
              {{ distExpanded ? '折叠图表' : '查看完整 37 类' }}
            </el-button>
          </div>
        </div>
      </template>
      <div class="dist-chart-wrap" :class="{ collapsed: !distExpanded }">
        <div ref="barChartEl" style="width:100%; height:820px"></div>
        <div v-if="!distExpanded" class="dist-fade"></div>
      </div>
    </el-card>
  </div>

  <!-- 加载中 -->
  <div v-else class="loading-wrap">
    <div class="stat-grid">
      <div class="skeleton" style="height:96px; border-radius:12px" v-for="i in 4" :key="i"></div>
    </div>
    <div class="dataset-overview-grid">
      <div class="skeleton" style="height:280px;border-radius:12px"></div>
      <div class="skeleton" style="height:280px;border-radius:12px"></div>
    </div>
    <div class="skeleton" style="height:820px; border-radius:12px"></div>
  </div>
</template>

<style scoped>
/* ═══ Class Distribution Chart Wrapper ═══ */
.dist-chart-wrap {
  position: relative;
  transition: max-height .35s cubic-bezier(.33,1,.68,1);
}
.dist-chart-wrap.collapsed {
  max-height: 460px;
  overflow: hidden;
}
.dist-fade {
  position: absolute; left: 0; right: 0; bottom: 0; height: 90px;
  background: linear-gradient(180deg, rgba(255,255,255,0) 0%, #FFFFFF 80%);
  pointer-events: none;
}

/* ═══ Stat Grid — Gradient Tiles ═══ */
.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(160px, 1fr));
  gap: 14px; margin-bottom: 16px;
}
.stat-tile {
  position: relative; overflow: hidden;
  border-radius: var(--radius, 12px);
  padding: 20px 16px 16px;
  border: 1px solid var(--c-border, #E2E8F0);
  background: var(--c-card, #FFFFFF);
  box-shadow: var(--shadow, 0 1px 3px rgba(0,0,0,.06));
  transition: all .2s ease;
  text-align: center; cursor: default;
}
.stat-tile::before {
  content: '';
  position: absolute; top: 0; left: 0; right: 0; height: 3px;
}
.stat-tile:nth-child(1)::before { background: var(--c-primary, #1E40AF); }
.stat-tile:nth-child(2)::before { background: var(--c-accent, #F59E0B); }
.stat-tile:nth-child(3)::before { background: var(--c-primary-soft, #3B82F6); }
.stat-tile:nth-child(4)::before { background: var(--c-green, #059669); }
.stat-tile:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md, 0 4px 12px rgba(0,0,0,.08));
  border-color: #BFDBFE;
}
.stat-icon { font-size: 24px; margin-bottom: 8px; }
.stat-val {
  font-size: 22px; font-weight: 800; color: var(--c-dark, #0F172A);
  font-family: 'Fira Code', monospace;
  line-height: 1.2; margin-bottom: 3px;
  word-break: normal; overflow-wrap: anywhere;
}
.stat-val.accent {
  color: var(--c-primary, #1E40AF); font-size: 28px;
  -webkit-text-fill-color: var(--c-primary, #1E40AF);
}
.stat-unit { font-size: 12px; font-weight: 500; color: var(--c-muted, #64748B); }
.stat-lbl  { font-size: 11.5px; color: var(--c-muted, #64748B); margin-top: 3px; font-weight: 600; }

/* ═══ Overview ═══ */
.dataset-overview-grid {
  display: grid;
  grid-template-columns: minmax(260px, .8fr) minmax(0, 1.2fr);
  gap: 14px; margin-bottom: 16px; align-items: stretch;
}
.prep-grid {
  display: grid; grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px; height: 100%;
}
.overview-card { height: 100%; }
.overview-card :deep(.el-card__body) { height: calc(100% - 52px); }

/* Species badges */
.species-row { display: flex; gap: 10px; padding: 10px 0 0; flex-wrap: wrap; }
.species-badge {
  flex: 1; display: flex; align-items: center; gap: 7px;
  padding: 9px 12px; border-radius: 10px;
  font-size: 12.5px; font-weight: 700;
  transition: all .2s ease;
}
.species-badge.cat {
  background: linear-gradient(135deg, rgba(244,114,182,.06), rgba(168,85,247,.04));
  color: #a855f7; border: 1px solid rgba(168,85,247,.18);
}
.species-badge.dog {
  background: linear-gradient(135deg, rgba(34,211,238,.06), rgba(99,102,241,.04));
  color: #6366f1; border: 1px solid rgba(99,102,241,.18);
}
.species-badge:hover { transform: translateX(3px); }
.sp-dot  { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; box-shadow: 0 0 6px currentColor; }
.cat-dot { background: linear-gradient(135deg, #f472b6, #a855f7); }
.dog-dot { background: linear-gradient(135deg, #22d3ee, #6366f1); }

/* Legend */
.legend-dot {
  display: inline-block; width: 22px; height: 7px;
  border-radius: 4px; vertical-align: middle; margin-right: 3px;
}
.loading-wrap { padding: 0; }

/* ═══ Samples — Card Glow ═══ */
.sample-main-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 14px; }
.sample-card {
  position: relative; overflow: hidden;
  background: rgba(255,255,255,.8); border-radius: 14px;
  padding: 12px 14px 14px;
  border: 1px solid rgba(99,102,241,.08);
  backdrop-filter: blur(10px);
  transition: all .25s ease;
}
.sample-card::before {
  content: '';
  position: absolute; top: 0; left: 0; right: 0; height: 2px;
  background: linear-gradient(90deg, #6366f1, #22d3ee, #a78bfa);
  background-size: 200% 100%;
  animation: gradientShift 6s ease infinite;
  opacity: .6;
}
.sample-card:hover {
  border-color: rgba(99,102,241,.16);
  box-shadow: 0 8px 28px rgba(99,102,241,.08), 0 0 0 1px rgba(99,102,241,.04);
  transform: translateY(-2px);
}
.sample-breed-label {
  display: flex; align-items: center; gap: 7px;
  font-size: 13px; font-weight: 800; color: var(--c-dark, #0F172A); margin-bottom: 10px;
}
.sample-species-dot {
  width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0;
  box-shadow: 0 0 6px currentColor;
}
.sample-imgs { display: grid; grid-template-columns: repeat(3, 1fr); gap: 7px; }
.sample-img-wrap { text-align: center; }
.sample-img {
  width: 100%; aspect-ratio: 1; object-fit: cover;
  border-radius: 10px; border: 1px solid rgba(226,232,240,.5);
  display: block; transition: all .25s ease; cursor: zoom-in;
}
.sample-img:hover {
  transform: scale(1.06);
  box-shadow: 0 8px 24px rgba(99,102,241,.15);
  position: relative; z-index: 5;
}
.sample-img-cap { font-size: 10.5px; color: var(--c-muted, #94A3B8); margin-top: 4px; font-weight: 600; }
.sample-img-cap.with-info {
  cursor: help; color: var(--c-primary, #2563EB);
  text-decoration: underline dotted; text-underline-offset: 3px;
}
.sample-legend {
  display: flex; align-items: center; gap: 7px;
  font-size: 11.5px; color: var(--c-muted, #64748B); margin-top: 14px;
  padding: 8px 12px; background: rgba(255,255,255,.6);
  border-radius: 10px; border: 1px solid rgba(99,102,241,.08);
  backdrop-filter: blur(6px);
}
.sl-dot { display: inline-block; width: 12px; height: 12px; border-radius: 4px; flex-shrink: 0; }

/* ═══ Responsive ═══ */
@media (max-width: 1180px) {
  .stat-grid { grid-template-columns: repeat(2, minmax(160px, 1fr)); }
  .dataset-overview-grid { grid-template-columns: 1fr; }
}
@media (max-width: 760px) {
  .stat-grid, .prep-grid, .sample-main-grid { grid-template-columns: 1fr; }
  .stat-tile { padding: 16px 14px; }
  .species-badge { flex-basis: 100%; }
  .sample-legend { flex-wrap: wrap; }
}

/* ═══ Augmentation Preview ═══ */
.aug-tip {
  display: inline-flex; align-items: center; gap: 6px;
  font-size: 12px; color: var(--c-muted, #64748B);
  background: rgba(59,130,246,.06); border: 1px solid rgba(59,130,246,.15);
  padding: 6px 12px; border-radius: 8px; margin-bottom: 12px;
}
.aug-tip b { color: var(--c-primary, #1E40AF); font-weight: 700; }
.aug-grid {
  display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px;
}
.aug-card {
  border-radius: var(--radius, 12px); overflow: hidden;
  border: 1px solid var(--c-border, #E2E8F0);
  background: var(--c-card, #FFFFFF);
  transition: all .2s ease;
}
.aug-card-original { border-color: var(--c-primary-soft, #3B82F6); }
.aug-card-original .aug-name { color: var(--c-primary, #1E40AF); }
.aug-card:hover { box-shadow: var(--shadow-md); transform: translateY(-2px); }

.aug-img-wrap { position: relative; overflow: hidden; aspect-ratio: 1; }
.aug-img {
  width: 100%; height: 100%; object-fit: cover; display: block;
  position: absolute; inset: 0;
}
.aug-img-after { z-index: 1; }
.aug-img-before {
  z-index: 2; opacity: 0; transition: opacity .25s ease;
}
.aug-card:hover .aug-img-before { opacity: 1; }
.aug-hover-hint {
  position: absolute; left: 6px; bottom: 6px; z-index: 3;
  padding: 2px 8px; border-radius: 100px;
  background: rgba(15,23,42,.75); backdrop-filter: blur(6px);
  color: #F1F5F9; font-size: 10px; font-weight: 600;
  opacity: .85; transition: all .2s ease;
}
.aug-card:hover .aug-hover-hint {
  background: rgba(99,102,241,.85);
  opacity: 1;
}
.aug-card:hover .aug-hover-hint::before {
  content: '原图 · '; opacity: .85;
}
.aug-original-tag {
  position: absolute; left: 6px; top: 6px; z-index: 3;
  padding: 2px 8px; border-radius: 100px;
  background: var(--c-primary, #2563EB); color: #fff;
  font-size: 10px; font-weight: 700; letter-spacing: .3px;
}

.aug-info { padding: 8px 10px; }
.aug-name { font-size: 13px; font-weight: 700; color: var(--c-dark, #0F172A); margin-bottom: 2px; }
.aug-desc { font-size: 11px; color: var(--c-muted, #64748B); line-height: 1.5; }

@media (max-width: 1180px) { .aug-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 600px) { .aug-grid { grid-template-columns: 1fr; } }

</style>
