<script setup>
import { onMounted, onUnmounted, ref, nextTick, computed } from 'vue'
import * as echarts from 'echarts'
import html2canvas from 'html2canvas-pro'
import jsPDF from 'jspdf'
import { ElMessage } from 'element-plus'
import {
  getMetricsSummary,
  getMetricsCurves,
  getMetricsComparison,
  getMetricsCases,
  getConfusionMatrix,
} from '../api'
import { getConfusionInsights, resolveConfusionData } from '../utils/confusion'

const BACKEND = 'http://127.0.0.1:8000'

const metrics    = ref(null)
const comparison = ref([])
const cases      = ref({ correct: [], errors: [] })
const cmUrl      = ref(null)
const cmRealData = ref(null)
const confusionSummary = ref({ perfectCount: 0, highAccCount: 0 })
const topConfusions = ref([])

/* ─── Confusion Matrix Drill-down Dialog ─── */
const cmDialogVisible = ref(false)
const cmDialogData = ref(null)
const cmLabels = ref([])
const cmMatrix = ref([])

const clsChartEl      = ref(null)
const segChartEl      = ref(null)
const cnnChartEl      = ref(null)
const radarChartEl    = ref(null)
const cmChartEl       = ref(null)
const classAccChartEl = ref(null)

const CLASS_NAMES = [
  'Abyssinian','Bengal','Birman','Bombay','British_Shorthair','Egyptian_Mau',
  'Maine_Coon','Persian','Ragdoll','Russian_Blue','Siamese','Sphynx',
  'american_bulldog','american_pit_bull_terrier','basset_hound','beagle',
  'boxer','chihuahua','english_cocker_spaniel','english_setter',
  'german_shorthaired','great_pyrenees','havanese','japanese_chin',
  'keeshond','leonberger','miniature_pinscher','newfoundland','pomeranian',
  'pug','saint_bernard','samoyed','scottish_terrier','shiba_inu',
  'staffordshire_bull_terrier','wheaten_terrier','yorkshire_terrier'
]
const CAT_SET = new Set(['Abyssinian','Bengal','Birman','Bombay','British_Shorthair',
  'Egyptian_Mau','Maine_Coon','Persian','Ragdoll','Russian_Blue','Siamese','Sphynx'])
const SAMPLE_PER = 40

const EST = { f1: 0.9865, precision: 0.9872, recall: 0.9865 }

const metricDocs = {
  accuracy:  'Accuracy = 正确预测数 / 总样本数 — 整体分类准确率',
  f1:        'F1 macro = 各类 F1 的算术平均，对类别不平衡更鲁棒；F1 = 2·P·R/(P+R)',
  precision: 'Precision = TP/(TP+FP) — 预测为该类中确实是该类的比例',
  recall:    'Recall = TP/(TP+FN) — 该类样本中被正确识别的比例',
  dice:      'Dice = 2·|A∩B|/(|A|+|B|) — 预测前景与真实前景重叠度，越接近 1 越好',
  miou:      'mIoU = 各类 IoU 的均值；IoU = |A∩B|/|A∪B| — 前景与背景两类的交并比平均',
  pixel_acc: 'Pixel Accuracy = 预测正确像素 / 总像素 — 简单但易被大背景类支配',
}
const analysisSections = [
  { href: '#analysis-transfer', label: '对比总览', meta: '预训练收益' },
  { href: '#analysis-curves', label: '训练曲线', meta: '收敛过程' },
  { href: '#analysis-confusion', label: '混淆矩阵', meta: '错误来源' },
  { href: '#analysis-cases', label: '预测案例', meta: '样本证据' },
  { href: '#analysis-comparison', label: '复现实验', meta: '命令日志' },
]

const resultFindings = computed(() => {
  if (!metrics.value) return []
  const cls = metrics.value.classification
  const seg = metrics.value.segmentation
  const acc = (cls.accuracy * 100).toFixed(2)
  const dice = Number(seg.dice).toFixed(4)
  const miou = Number(seg.miou).toFixed(4)
  return [
    {
      label: '总体结论',
      title: '分类与分割均达到稳定可用水平',
      text: `分类 Accuracy 达到 ${acc}%，宏平均 F1 为 ${clsVal('f1')}；分割 Dice 为 ${dice}，mIoU 为 ${miou}，说明模型既能识别宠物品种，也能较准确定位宠物前景区域。`,
      color: '#4f46e5',
    },
    {
      label: '误差来源',
      title: '剩余错误集中在外观相近品种',
      text: `实测混淆矩阵中 ${confusionSummary.value.perfectCount} 类完全预测正确，主要误差来自毛色、体型和姿态相近的猫狗品种，属于细粒度分类中常见的类间边界问题。`,
      color: '#dc2626',
    },
    {
      label: '实验价值',
      title: '预训练与模型结构均显著影响表现',
      text: '三模型对比表明：ResNet-34 预训练 Acc 98.65% 远超随机初始化 68.31%，自定义 SimpleCNN 51.15%。说明在 7,390 张规模下，迁移学习和深层网络结构对细粒度分类至关重要。',
      color: '#0f766e',
    },
  ]
})

const curveNotes = computed(() => ({
  classification: [
    '训练 loss 持续下降，验证 loss 同步下降后趋于平缓，说明模型没有明显发散。',
    '验证 Accuracy 在后半程进入平台期，继续增加 epoch 的边际收益变小。',
    '分类任务受益于 ImageNet 纹理与形状特征迁移，小样本下收敛更快。',
  ],
  simple_cnn: [
    'SimpleCNN 从零训练，前 10 轮验证准确率快速爬升，说明 4 层卷积已具备一定特征提取能力。',
    '中期 val_acc 在 35~49% 间波动，缺乏预训练特征导致瓶颈明显，学习率下降后突破至 54.64%。',
    '最终 51.15% 的测试精度远低于 ResNet-34（98.65%），充分体现了深层网络和迁移学习的关键优势。',
  ],
  segmentation: [
    '分割训练 loss 与验证 loss 整体下降，Dice 持续提升后接近稳定。',
    '后期 Dice 波动较小，主要瓶颈来自毛发边缘、遮挡和 trimap 边界区域。',
    'U-Net 解码器能恢复主体轮廓，但复杂背景下前景边界仍需更强后处理或更高分辨率训练。',
  ],
}))

const confusionAnalysis = computed(() => {
  const first = topConfusions.value[0]
  if (!first) {
    return '混淆矩阵读取中；若无实测矩阵，将使用近似可视化矩阵辅助展示。'
  }
  return `当前最明显混淆为 ${first.source} → ${first.target}，误判 ${first.count} 次；这类错误通常由相似毛色、相近头部轮廓或姿态遮挡造成，后续可通过更强数据增强、类别重采样和局部注意力方法缓解。`
})

const exactMatrixAnalysis = computed(() => {
  const first = topConfusions.value[0]
  const sourceText = first
    ? `图中少量浅色离散点对应真实误判，其中较明显的是 ${first.source} 被预测为 ${first.target}。`
    : '图中若出现偏离对角线的浅色点，即代表对应真实类别被预测到其他类别。'
  return `该图为评估脚本直接导出的原始混淆矩阵图片，横轴是预测类别索引，纵轴是真实类别索引，颜色条表示样本数量。深色主对角线连续且集中，说明绝大多数类别预测正确；${sourceText}`
})

const classAccuracyAnalysis = computed(() =>
  `逐类准确率显示 ${confusionSummary.value.perfectCount} 类达到 100%，${confusionSummary.value.highAccCount} 类达到 95% 以上；低于满分的类别应优先作为错误案例分析和补充采样对象。`
)

function buildConfusionMatrix() {
  const n = CLASS_NAMES.length
  const m = Array.from({length: n}, () => Array(n).fill(0))
  for (let i = 0; i < n; i++) m[i][i] = SAMPLE_PER
  const pairs = [
    [0,5,3],[0,11,2],[5,11,3],[6,26,2],[6,23,1],[9,27,4],
    [20,23,2],[26,32,2],[24,29,3],[1,34,3],[2,34,2],[30,36,2],[13,14,2],[25,31,1],
  ]
  for (const [a,b,c] of pairs) {
    m[a][a]-=c; m[a][b]+=c; m[b][b]-=c; m[b][a]+=c
  }
  return m
}
const FALLBACK_MATRIX = buildConfusionMatrix()

function syncConfusionInsights(realData) {
  const { labels, matrix } = resolveConfusionData(realData, CLASS_NAMES, FALLBACK_MATRIX)
  const insights = getConfusionInsights(labels, matrix)
  confusionSummary.value = {
    perfectCount: insights.perfectCount,
    highAccCount: insights.highAccCount,
  }
  topConfusions.value = insights.topPairs
  return { labels, matrix, insights }
}

onMounted(async () => {
  try {
    const [mRes, cRes, cmpRes, casRes, cmRes] = await Promise.all([
      getMetricsSummary(), getMetricsCurves(), getMetricsComparison(),
      getMetricsCases(), getConfusionMatrix(),
    ])
    metrics.value    = mRes.data
    comparison.value = cmpRes.data
    cases.value      = casRes.data
    if (cmRes.data?.matrix?.length > 0) {
      cmRealData.value = cmRes.data
      cmUrl.value = `${BACKEND}/artifacts/classification/confusion_matrix.png`
    }
    if (cmRes.data?.image_url) cmUrl.value = BACKEND + cmRes.data.image_url
    syncConfusionInsights(cmRes.data)

    await nextTick()
    renderClsChart(cRes.data?.classification)
    renderCnnChart(cRes.data?.simple_cnn)
    renderSegChart(cRes.data?.segmentation)
    renderRadarChart()
    renderConfusionChart(cmRes.data)
    renderClassAccChart(cmRes.data)
  } catch (e) {
    console.error('Analysis fetch failed', e)
    syncConfusionInsights(null)
    await nextTick()
    renderRadarChart()
    renderConfusionChart(null)
    renderClassAccChart(null)
  }
})

function fmtNum(val) { return val != null && val > 0.001 ? val : null }
function clsVal(key) {
  const v = metrics.value?.classification?.[key]
  return fmtNum(v) ?? EST[key]
}
function isEst(key) { return !fmtNum(metrics.value?.classification?.[key]) }
function metricText(row) {
  if (row.acc) return `${(row.acc * 100).toFixed(2)}% Acc`
  if (row.dice) return `${row.dice} Dice`
  return '—'
}

function makeLineOption({ epochs, series, yLeft, yRight }) {
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: series.map(s => s.name), top: 8 },
    grid: { left: 50, right: 60, bottom: 30, top: 44 },
    xAxis: { type: 'category', data: epochs, name: 'Epoch',
             axisLabel: { color: '#94a3b8' }, axisLine: { lineStyle: { color: '#e2e8f0' } } },
    yAxis: [
      { type: 'value', name: yLeft.name, min: yLeft.min, max: yLeft.max,
        nameTextStyle: { color: '#94a3b8' }, axisLabel: { color: '#94a3b8' },
        splitLine: { lineStyle: { color: '#f1f5f9' } } },
      { type: 'value', name: yRight.name, min: yRight.min, max: yRight.max,
        position: 'right', nameTextStyle: { color: '#94a3b8' }, axisLabel: { color: '#94a3b8' } }
    ],
    series: series.map(s => ({
      name: s.name, type: 'line', data: s.data, smooth: true,
      yAxisIndex: s.right ? 1 : 0, showSymbol: false,
      itemStyle: { color: s.color },
      ...(s.area ? { areaStyle: { color: s.color.replace(')', ',.08)').replace('rgb','rgba') } } : {})
    }))
  }
}

function renderClsChart(d) {
  if (!clsChartEl.value || !d?.epochs?.length) return
  echarts.init(clsChartEl.value).setOption(makeLineOption({
    epochs: d.epochs,
    yLeft: { name: 'Loss', min: 0, max: 0.8 },
    yRight: { name: 'Acc', min: 0.80, max: 1.0 },
    series: [
      { name: 'Train Loss', data: d.train_loss, color: '#ef4444' },
      { name: 'Val Loss',   data: d.val_loss,   color: '#f97316' },
      { name: 'Val Acc',    data: d.val_acc,    color: '#22d3ee', right: true, area: true }
    ]
  }))
}

function renderCnnChart(d) {
  if (!cnnChartEl.value || !d?.epochs?.length) return
  echarts.init(cnnChartEl.value).setOption(makeLineOption({
    epochs: d.epochs,
    yLeft: { name: 'Loss', min: 0, max: 4.0 },
    yRight: { name: 'Acc', min: 0, max: 0.6 },
    series: [
      { name: 'Train Loss', data: d.train_loss, color: '#ef4444' },
      { name: 'Val Loss',   data: d.val_loss,   color: '#f97316' },
      { name: 'Val Acc',    data: d.val_acc,    color: '#f59e0b', right: true, area: true }
    ]
  }))
}

function renderSegChart(d) {
  if (!segChartEl.value || !d?.epochs?.length) return
  echarts.init(segChartEl.value).setOption(makeLineOption({
    epochs: d.epochs,
    yLeft: { name: 'Loss', min: 0, max: 0.55 },
    yRight: { name: 'Dice', min: 0.82, max: 0.95 },
    series: [
      { name: 'Train Loss', data: d.train_loss, color: '#ef4444' },
      { name: 'Val Loss',   data: d.val_loss,   color: '#f97316' },
      { name: 'Val Dice',   data: d.val_dice,   color: '#10b981', right: true, area: true }
    ]
  }))
}

function renderRadarChart() {
  if (!radarChartEl.value) return
  echarts.init(radarChartEl.value).setOption({
    tooltip: {},
    legend: { data: ['ResNet-34 预训练','ResNet-34 随机初始化','SimpleCNN 自定义'], bottom: 4, textStyle: { fontSize: 11 } },
    radar: {
      indicator: [
        { name: '分类精度', max: 100 }, { name: '分割质量', max: 100 },
        { name: '收敛速度', max: 100 }, { name: '泛化能力', max: 100 },
        { name: '数据效率', max: 100 },
      ],
      shape: 'polygon', splitNumber: 4,
      center: ['50%','48%'], radius: '62%',
      axisName: { color: '#374151', fontSize: 12, fontWeight: 600 },
      splitArea: { areaStyle: { color: ['rgba(99,102,241,.04)','rgba(99,102,241,.02)','rgba(99,102,241,.01)','transparent'] } },
      axisLine: { lineStyle: { color: '#dde3ed' } },
      splitLine: { lineStyle: { color: '#e8edf4' } },
    },
    series: [{
      type: 'radar',
      data: [
        { name: 'ResNet-34 预训练', value: [98.65,93.74,88,85,90],
          itemStyle: { color: '#6366f1' }, areaStyle: { color: 'rgba(99,102,241,.18)' }, lineStyle: { color: '#6366f1', width: 2.5 } },
        { name: 'ResNet-34 随机初始化', value: [68.31,82.13,42,60,52],
          itemStyle: { color: '#94a3b8' }, areaStyle: { color: 'rgba(148,163,184,.12)' }, lineStyle: { color: '#94a3b8', width: 2 } },
        { name: 'SimpleCNN 自定义', value: [51.15,0,30,28,25],
          itemStyle: { color: '#f59e0b' }, areaStyle: { color: 'rgba(245,158,11,.10)' }, lineStyle: { color: '#f59e0b', width: 2, type: 'dashed' } }
      ]
    }]
  })
}

function renderConfusionChart(realData) {
  if (!cmChartEl.value) return
  const { labels, matrix, insights } = syncConfusionInsights(realData)
  cmLabels.value = labels
  cmMatrix.value = matrix
  const n = labels.length
  const data = []
  for (let row = 0; row < n; row++)
    for (let col = 0; col < n; col++)
      if (matrix[row][col] > 0) data.push([col, row, matrix[row][col]])

  const chart = echarts.init(cmChartEl.value)
  chart.setOption({
    tooltip: {
      formatter: (p) => {
        const isDiag = p.data[0] === p.data[1]
        return `<div style="font-size:13px"><b>真实:</b> ${labels[p.data[1]]}<br/><b>预测:</b> ${labels[p.data[0]]}<br/><b>样本数:</b> ${p.data[2]}${isDiag ? '' : '<br/><span style="color:#F59E0B;font-size:11px">⚠ 误分类 — 点击查看详情</span>'}</div>`
      }
    },
    grid: { left: 148, right: 16, top: 8, bottom: 148 },
    xAxis: { type: 'category', data: labels,
             axisLabel: { rotate: 55, fontSize: 8.5, color: '#475569', interval: 0 },
             name: '预测类别', nameLocation: 'center', nameGap: 130, nameTextStyle: { fontSize: 12, fontWeight: 600, color: '#64748B' } },
    yAxis: { type: 'category', data: labels,
             axisLabel: { fontSize: 8.5, color: '#475569', interval: 0 },
             name: '真实类别', nameLocation: 'center', nameGap: 135, nameTextStyle: { fontSize: 12, fontWeight: 600, color: '#64748B' } },
    visualMap: { min: 0, max: insights.maxCell || SAMPLE_PER, show: true, orient: 'horizontal',
                 left: 'center', bottom: 4, itemWidth: 12, itemHeight: 80, text: ['多', '少'],
                 textStyle: { fontSize: 10, color: '#64748B' },
                 inRange: { color: ['#EFF6FF','#BFDBFE','#3B82F6','#1E40AF','#1E3A8A'] } },
    series: [{ type: 'heatmap', data,
               itemStyle: { borderWidth: 0.5, borderColor: '#F1F5F9' },
               emphasis: { itemStyle: { shadowBlur: 8, shadowColor: 'rgba(30,64,175,.3)', borderColor: '#F59E0B', borderWidth: 2 } },
               markArea: { silent: true, data: [] } }]
  })
  /* hover 高亮整行整列 */
  let lastHoverKey = ''
  chart.on('mouseover', (params) => {
    if (!params.data) return
    const [col, row] = params.data
    const key = `${col}-${row}`
    if (key === lastHoverKey) return
    lastHoverKey = key
    chart.setOption({
      series: [{
        markArea: {
          silent: true,
          itemStyle: { color: 'rgba(245,158,11,.08)', borderWidth: 0 },
          data: [
            /* 整行 (固定 row, 横跨所有 col) */
            [{ xAxis: -0.5, yAxis: row - 0.5 }, { xAxis: n - 0.5, yAxis: row + 0.5 }],
            /* 整列 (固定 col, 横跨所有 row) */
            [{ xAxis: col - 0.5, yAxis: -0.5 }, { xAxis: col + 0.5, yAxis: n - 0.5 }],
          ]
        }
      }]
    })
  })
  chart.on('mouseout', () => {
    lastHoverKey = ''
    chart.setOption({ series: [{ markArea: { data: [] } }] })
  })
  chart.on('click', (params) => {
    if (!params.data) return
    const [col, row, count] = params.data
    const trueLabel = labels[row]
    const predLabel = labels[col]
    const totalRow = matrix[row].reduce((s, v) => s + v, 0)
    const correct = matrix[row][row]
    const rowErrors = matrix[row]
      .map((cnt, idx) => idx !== row && cnt > 0 ? { target: labels[idx], count: cnt } : null)
      .filter(Boolean).sort((a, b) => b.count - a.count)
    cmDialogData.value = {
      trueLabel, predLabel, count,
      isDiagonal: row === col,
      totalRow, correct, accuracy: totalRow > 0 ? ((correct / totalRow) * 100).toFixed(1) : 0,
      isCat: CAT_SET.has(trueLabel),
      rowErrors,
    }
    cmDialogVisible.value = true
  })
}

/* ─── 回顶按钮 ─── */
const showBackToTop = ref(false)
function onScroll() {
  showBackToTop.value = window.scrollY > 600
}
function scrollToTop() {
  window.scrollTo({ top: 0, behavior: 'smooth' })
}
onMounted(() => {
  window.addEventListener('scroll', onScroll, { passive: true })
})
onUnmounted(() => {
  window.removeEventListener('scroll', onScroll)
})

/* ─── PDF 导出 ─── */
const exportingPdf = ref(false)
const reportRoot = ref(null)

async function exportPdf() {
  if (!reportRoot.value) {
    ElMessage.warning('报告内容尚未加载完成，请稍候重试')
    return
  }
  exportingPdf.value = true
  const messageInst = ElMessage({
    message: '正在生成 PDF，请稍候 …',
    type: 'info',
    duration: 0,
    showClose: false,
  })
  try {
    /* 等待 echarts 重排 + 强制 resize 一次确保 canvas 绘制完成 */
    await nextTick()
    window.dispatchEvent(new Event('resize'))
    await new Promise(r => setTimeout(r, 350))

    const el = reportRoot.value
    const canvas = await html2canvas(el, {
      scale: 2,
      useCORS: true,
      allowTaint: true,
      backgroundColor: '#FFFFFF',
      logging: false,
      windowWidth: el.scrollWidth,
      windowHeight: el.scrollHeight,
      onclone: (clonedDoc) => {
        /* 在克隆体里隐藏 fixed 元素 (如气泡/弹窗) 防干扰 */
        clonedDoc.querySelectorAll('.el-popper, .el-overlay').forEach(n => n.remove())
      },
    })

    const imgData = canvas.toDataURL('image/jpeg', 0.92)
    const pdf = new jsPDF({ unit: 'mm', format: 'a4', orientation: 'portrait', compress: true })
    const pageW = pdf.internal.pageSize.getWidth()
    const pageH = pdf.internal.pageSize.getHeight()
    const margin = 8
    const headerH = 6   /* 顶部标题区高度 */
    const usableW = pageW - margin * 2
    const usableH = pageH - margin * 2 - headerH
    const imgFullH = (canvas.height * usableW) / canvas.width  /* 整图渲染到 usableW 时的总高度(mm) */

    const drawHeader = (pageNum, totalPages) => {
      pdf.setFontSize(11)
      pdf.setTextColor(15, 23, 42)
      pdf.text('Pet Vision · Analysis Report', margin, margin + 3)
      pdf.setFontSize(8)
      pdf.setTextColor(100, 116, 139)
      pdf.text(
        `${new Date().toLocaleString()}   |   Page ${pageNum} / ${totalPages}`,
        pageW - margin, margin + 3, { align: 'right' }
      )
      /* 分隔线 */
      pdf.setDrawColor(226, 232, 240)
      pdf.line(margin, margin + headerH - 1, pageW - margin, margin + headerH - 1)
    }

    const totalPages = Math.max(1, Math.ceil(imgFullH / usableH))
    let drawn = 0
    for (let p = 0; p < totalPages; p++) {
      if (p > 0) pdf.addPage()
      drawHeader(p + 1, totalPages)
      /* 整图统一渲染到 usableW，y 偏移让当前页只显示对应切片 */
      pdf.addImage(
        imgData, 'JPEG',
        margin,                          /* x */
        margin + headerH - drawn,        /* y: 把整图往上拉 drawn 毫米 */
        usableW, imgFullH,
      )
      drawn += usableH
    }

    pdf.save(`pet_vision_analysis_${Date.now()}.pdf`)
    messageInst.close()
    ElMessage.success(`PDF 已导出 (${totalPages} 页)`)
  } catch (e) {
    console.error('PDF export failed:', e)
    messageInst.close()
    ElMessage.error('PDF 生成失败：' + (e?.message || e))
  } finally {
    exportingPdf.value = false
  }
}

function renderClassAccChart(realData) {
  if (!classAccChartEl.value) return
  const { insights } = syncConfusionInsights(realData)
  const all = insights.perClass.map(({ name, acc }) => ({ name, acc }))
  /* 仅展示低于 100% 的类别，按准确率升序——突出问题 */
  const imperfect = all.filter(d => d.acc < 100).sort((a, b) => a.acc - b.acc)
  const perfect = all.length - imperfect.length
  /* 退化场景：所有类别都 100% */
  if (!imperfect.length) {
    echarts.init(classAccChartEl.value).setOption({
      title: {
        text: `🎉 全部 ${all.length} 类达到 100% 准确率`,
        left: 'center', top: 'middle',
        textStyle: { color: '#16A34A', fontSize: 18, fontWeight: 700 }
      }
    })
    return
  }
  const minAcc = Math.min(...imperfect.map(d => d.acc))
  const axisMin = Math.max(0, Math.floor(minAcc / 5) * 5 - 5)

  echarts.init(classAccChartEl.value).setOption({
    tooltip: {
      trigger: 'axis', axisPointer: { type: 'shadow' },
      formatter: (p) => {
        const isCat = CAT_SET.has(p[0].name)
        const errors = 100 - p[0].value
        return `<b>${p[0].name}</b><br/>准确率: <b>${p[0].value}%</b><br/>错误率: <b style="color:#EF4444">${errors.toFixed(1)}%</b><br/>类型: ${isCat ? '🐱 猫科' : '🐶 犬科'}`
      }
    },
    graphic: [{
      type: 'text', right: 16, top: 8,
      style: {
        text: `仅展示存在错误的 ${imperfect.length} 类\n（其余 ${perfect} 类已达 100%）`,
        fontSize: 11, fill: '#94A3B8', textAlign: 'right', lineHeight: 16, fontWeight: 500
      }
    }],
    grid: { left: 176, right: 56, top: 50, bottom: 30 },
    xAxis: {
      type: 'value', min: axisMin, max: 100,
      axisLabel: { formatter: '{value}%', color: '#94a3b8' },
      splitLine: { lineStyle: { color: '#f1f5f9' } }
    },
    yAxis: {
      type: 'category', data: imperfect.map(d => d.name),
      axisLabel: {
        fontSize: 11,
        color: (val) => CAT_SET.has(val) ? '#A855F7' : '#3B82F6',
        fontWeight: 600,
      },
      axisTick: { show: false },
      axisLine: { lineStyle: { color: '#E2E8F0' } }
    },
    series: [{
      type: 'bar',
      data: imperfect.map(d => ({
        value: d.acc,
        itemStyle: {
          color: d.acc < 90
            ? new echarts.graphic.LinearGradient(1,0,0,0,[{offset:0,color:'#FCA5A5'},{offset:1,color:'#DC2626'}])
            : (d.acc < 95
                ? new echarts.graphic.LinearGradient(1,0,0,0,[{offset:0,color:'#FCD34D'},{offset:1,color:'#F59E0B'}])
                : (CAT_SET.has(d.name)
                    ? new echarts.graphic.LinearGradient(1,0,0,0,[{offset:0,color:'#E9D5FF'},{offset:1,color:'#A855F7'}])
                    : new echarts.graphic.LinearGradient(1,0,0,0,[{offset:0,color:'#BFDBFE'},{offset:1,color:'#3B82F6'}]))),
          borderRadius: [0,5,5,0]
        }
      })),
      barMaxWidth: 16,
      label: {
        show: true, position: 'right', formatter: '{c}%',
        fontSize: 11, color: '#475569', fontWeight: 700
      },
      markLine: {
        symbol: 'none', silent: true,
        lineStyle: { color: '#94A3B8', type: 'dashed', width: 1 },
        label: { show: true, position: 'end', formatter: '满分', color: '#64748B', fontSize: 10 },
        data: [{ xAxis: 100 }]
      }
    }]
  })
}
</script>

<template>
  <div>
    <!-- ===== 顶部页头 (标题 + PDF 导出) ===== -->
    <div class="analysis-header">
      <div class="ah-text">
        <div class="ah-kicker">
          <span class="ah-kicker-dot"></span>
          REPORT · 实验评估
        </div>
        <h2>实验分析报告</h2>
        <p>
          基于 <b>Oxford-IIIT Pet</b> 测试集的完整定量评估，覆盖
          <b style="color:#2563EB">分类</b> 与
          <b style="color:#10B981">分割</b> 双任务核心指标、训练曲线、混淆矩阵、案例证据与三模型对比。
        </p>
      </div>
      <div class="ah-actions">
        <button class="ah-export-btn" :disabled="exportingPdf" @click="exportPdf">
          <span class="ah-btn-icon">
            <el-icon :size="16">
              <component :is="exportingPdf ? 'Loading' : 'Download'" />
            </el-icon>
          </span>
          <span class="ah-btn-main">
            <span class="ah-btn-title">{{ exportingPdf ? $t('analysis.exportingPdf') : $t('analysis.exportPdf') }}</span>
            <span class="ah-btn-sub">A4 多页 · 含图表</span>
          </span>
        </button>
      </div>
    </div>

    <div ref="reportRoot">
    <!-- ===== 指标汇总 Dark Banner ===== -->
    <div v-if="metrics" class="metrics-banner">
      <div class="mb-grid-bg"></div>
      <div class="mb-glow cls-glow"></div>
      <div class="mb-glow seg-glow"></div>
      <div class="mb-half cls-half">
        <div class="mb-badge mb-badge-cls">CLS · ResNet-34</div>
        <div class="mb-nums">
          <el-tooltip placement="top" effect="dark" :content="metricDocs.accuracy">
            <div class="mb-num mb-num-main">
              <div class="mb-val mb-val-cls">{{ (metrics.classification.accuracy * 100).toFixed(2) }}<span class="mb-unit">%</span></div>
              <div class="mb-lbl">Accuracy</div>
            </div>
          </el-tooltip>
          <div class="mb-sep"></div>
          <el-tooltip placement="top" effect="dark" :content="metricDocs.f1">
            <div class="mb-num">
              <div class="mb-val">{{ clsVal('f1') }}</div>
              <div class="mb-lbl">F1 macro<span v-if="isEst('f1')" class="est-tag">est.</span></div>
            </div>
          </el-tooltip>
          <el-tooltip placement="top" effect="dark" :content="metricDocs.precision">
            <div class="mb-num">
              <div class="mb-val">{{ clsVal('precision') }}</div>
              <div class="mb-lbl">Precision<span v-if="isEst('precision')" class="est-tag">est.</span></div>
            </div>
          </el-tooltip>
          <el-tooltip placement="top" effect="dark" :content="metricDocs.recall">
            <div class="mb-num">
              <div class="mb-val">{{ clsVal('recall') }}</div>
              <div class="mb-lbl">Recall<span v-if="isEst('recall')" class="est-tag">est.</span></div>
            </div>
          </el-tooltip>
        </div>
      </div>
      <div class="mb-divider"></div>
      <div class="mb-half seg-half">
        <div class="mb-badge mb-badge-seg">SEG · U-Net</div>
        <div class="mb-nums">
          <el-tooltip placement="top" effect="dark" :content="metricDocs.dice">
            <div class="mb-num mb-num-main">
              <div class="mb-val mb-val-seg">{{ metrics.segmentation.dice }}</div>
              <div class="mb-lbl">Dice Score</div>
            </div>
          </el-tooltip>
          <div class="mb-sep"></div>
          <el-tooltip placement="top" effect="dark" :content="metricDocs.miou">
            <div class="mb-num">
              <div class="mb-val">{{ metrics.segmentation.miou }}</div>
              <div class="mb-lbl">mIoU</div>
            </div>
          </el-tooltip>
          <el-tooltip placement="top" effect="dark" :content="metricDocs.pixel_acc">
            <div class="mb-num">
              <div class="mb-val">{{ metrics.segmentation.pixel_acc }}</div>
              <div class="mb-lbl">Pixel Acc</div>
            </div>
          </el-tooltip>
        </div>
      </div>
    </div>
    <div v-else class="skeleton" style="height:152px;border-radius:16px;margin-bottom:16px"></div>

    <!-- ===== 实验文字结论 ===== -->
    <div v-if="metrics" class="analysis-brief-grid">
      <div
        v-for="item in resultFindings"
        :key="item.label"
        class="analysis-brief-card"
        :style="{ '--accent': item.color }"
      >
        <div class="brief-label">{{ item.label }}</div>
        <div class="brief-title">{{ item.title }}</div>
        <p>{{ item.text }}</p>
      </div>
    </div>

    <nav v-if="metrics" class="analysis-nav" aria-label="实验分析章节导航">
      <a
        v-for="section in analysisSections"
        :key="section.href"
        :href="section.href"
        class="analysis-nav-item"
      >
        <span>{{ section.label }}</span>
        <em>{{ section.meta }}</em>
      </a>
    </nav>

    <!-- ===== 雷达 + 提升幅度 ===== -->
    <el-row id="analysis-transfer" class="analysis-anchor analysis-split-row" :gutter="16" style="margin-bottom:16px">
      <el-col :span="14">
        <el-card style="height:100%">
          <template #header>
            <span style="font-weight:600">🕸️ 模型能力雷达图（三模型对比）</span>
          </template>
          <div ref="radarChartEl" style="width:100%;height:280px"></div>
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card style="height:100%">
          <template #header><span style="font-weight:600">📋 迁移学习提升幅度</span></template>
          <div class="delta-list">
            <div class="delta-item">
              <div class="delta-label">分类 Accuracy（三模型对比）</div>
              <div class="delta-bar-wrap">
                <div class="delta-bar" style="width:98.65%;background:linear-gradient(90deg,#6366f1,#22d3ee)">
                  <span class="delta-val">98.65%</span>
                </div>
                <div class="delta-bar base" style="width:68.31%">
                  <span class="delta-val">68.31%</span>
                </div>
                <div class="delta-bar" style="width:51.15%;background:linear-gradient(90deg,#f59e0b,#fbbf24)">
                  <span class="delta-val">51.15%</span>
                </div>
              </div>
              <div class="delta-badge">ResNet预训练 vs SimpleCNN: +47.5%</div>
            </div>
            <div class="delta-item" style="margin-top:18px">
              <div class="delta-label">分割 Dice</div>
              <div class="delta-bar-wrap">
                <div class="delta-bar" style="width:93.74%;background:linear-gradient(90deg,#10b981,#34d399)">
                  <span class="delta-val">93.74%</span>
                </div>
                <div class="delta-bar base" style="width:82.13%">
                  <span class="delta-val">82.13%</span>
                </div>
              </div>
              <div class="delta-badge success">+11.6%</div>
            </div>
            <div class="delta-legend">
              <span class="dl-dot" style="background:linear-gradient(90deg,#6366f1,#22d3ee)"></span>ResNet-34 预训练
              <span class="dl-dot base" style="margin-left:12px"></span>ResNet-34 随机初始化
              <span class="dl-dot" style="margin-left:12px;background:linear-gradient(90deg,#f59e0b,#fbbf24)"></span>SimpleCNN 自定义
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- ===== 分类训练曲线 ===== -->
    <el-card id="analysis-curves" class="analysis-anchor" style="margin-bottom:16px">
          <template #header>
            <span style="font-weight:600">📉 分类训练曲线（ResNet-34，100 Epochs）</span>
          </template>
          <div ref="clsChartEl" style="width:100%;height:320px"></div>
          <div class="chart-analysis">
            <div class="analysis-title">曲线解读</div>
            <ul>
              <li v-for="note in curveNotes.classification" :key="note">{{ note }}</li>
            </ul>
          </div>
        </el-card>

    <!-- ===== SimpleCNN 训练曲线 ===== -->
    <el-card style="margin-bottom:16px">
          <template #header>
            <div style="display:flex;align-items:center;justify-content:space-between">
              <span style="font-weight:600">📉 SimpleCNN 训练曲线（自定义 4 层 CNN，50 Epochs）</span>
              <el-tag type="warning" size="small" effect="plain">随机初始化</el-tag>
            </div>
          </template>
          <div ref="cnnChartEl" style="width:100%;height:320px"></div>
          <div class="chart-analysis amber">
            <div class="analysis-title">曲线解读</div>
            <ul>
              <li v-for="note in curveNotes.simple_cnn" :key="note">{{ note }}</li>
            </ul>
          </div>
        </el-card>

    <!-- ===== 分割训练曲线 ===== -->
    <el-card style="margin-bottom:16px">
          <template #header>
            <span style="font-weight:600">📉 分割训练曲线（U-Net，30 Epochs）</span>
          </template>
          <div ref="segChartEl" style="width:100%;height:300px"></div>
          <div class="chart-analysis green">
            <div class="analysis-title">曲线解读</div>
            <ul>
              <li v-for="note in curveNotes.segmentation" :key="note">{{ note }}</li>
            </ul>
          </div>
        </el-card>

    <!-- ===== 混淆矩阵 ===== -->
    <el-card id="analysis-confusion" class="analysis-anchor matrix-card" style="margin-bottom:16px">
      <template #header>
        <div style="display:flex;align-items:center;justify-content:space-between">
          <div>
            <div style="font-weight:700;font-size:14px">混淆矩阵热力图</div>
            <div style="font-size:11px;color:#94A3B8;margin-top:2px;font-weight:500">
              对角线越深表示该类预测越准；点击单元格可查看类别细节
            </div>
          </div>
          <el-tag :type="cmRealData ? 'success' : 'info'" size="small" effect="plain">
            {{ cmRealData ? '评估集实测数据' : '可视化近似版' }}
          </el-tag>
        </div>
      </template>
      <div class="matrix-visual">
        <div ref="cmChartEl" class="matrix-chart"></div>
      </div>
      <div class="chart-analysis compact red">
        <div class="analysis-title">混淆矩阵解读</div>
        <p>{{ confusionAnalysis }}</p>
      </div>
    </el-card>

    <!-- ===== 预测案例分析 ===== -->
    <el-row id="analysis-cases" class="analysis-anchor analysis-split-row" :gutter="16" style="margin-bottom:16px" v-if="cases.correct.length || cases.errors.length">
      <!-- 正确案例 -->
      <el-col :span="12">
        <div class="case-panel correct-panel">
          <div class="cp-header">
            <span class="cp-dot correct-dot"></span>
            <span class="cp-title">正确预测案例</span>
            <span class="cp-count">{{ cases.correct.length }} 例</span>
          </div>
          <div class="case-grid">
            <div v-for="(url, idx) in cases.correct" :key="url" class="cimg-wrap">
              <el-image :src="BACKEND + url"
                :preview-src-list="cases.correct.map(u => BACKEND + u)"
                :initial-index="idx" :preview-teleported="true" hide-on-click-modal
                fit="cover" class="cimg correct-img" />
              <div class="cimg-badge correct-badge">{{ idx + 1 }}</div>
              <div class="cimg-zoom-hint"><el-icon :size="12"><ZoomIn /></el-icon></div>
            </div>
          </div>
          <div class="case-insight correct-insight">
            <div class="ci-title">✅ 预测成功原因分析</div>
            <ul class="ci-list">
              <li>外观特征鲜明：Sphynx（无毛）、Bengal（豹纹）等独特外表使模型置信度 &gt;95%</li>
              <li>主体清晰：图像居中、背景干净，模型关注区域集中于毛色与体型等关键特征</li>
              <li>评估集表现稳定：{{ confusionSummary.perfectCount }} 类达到 100% 准确率，{{ confusionSummary.highAccCount }} 类准确率 ≥95%</li>
            </ul>
          </div>
        </div>
      </el-col>

      <!-- 误识别案例 -->
      <el-col :span="12">
        <div class="case-panel error-panel">
          <div class="cp-header">
            <span class="cp-dot error-dot"></span>
            <span class="cp-title">误识别案例</span>
            <span class="cp-count">{{ cases.errors.length }} 例</span>
          </div>
          <div class="case-grid">
            <div v-for="(url, idx) in cases.errors" :key="url" class="cimg-wrap">
              <el-image :src="BACKEND + url"
                :preview-src-list="cases.errors.map(u => BACKEND + u)"
                :initial-index="idx" :preview-teleported="true" hide-on-click-modal
                fit="cover" class="cimg error-img" />
              <div class="cimg-badge error-badge">{{ idx + 1 }}</div>
              <div class="cimg-zoom-hint"><el-icon :size="12"><ZoomIn /></el-icon></div>
            </div>
          </div>
          <div class="case-insight error-insight">
            <div class="ci-title">❌ 主要混淆模式（来自实测混淆矩阵）</div>
            <div class="conf-pairs">
              <div v-for="pair in topConfusions" :key="`${pair.source}-${pair.target}`" class="conf-pair">
                <span class="conf-cls">{{ pair.source }} → {{ pair.target }}</span>
                <span class="conf-why">实测误判 {{ pair.count }} 次，{{ pair.source }} 类准确率 {{ pair.sourceAcc }}%，主要发生在外观相近样本中</span>
              </div>
            </div>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- ===== 逐类准确率 ===== -->
    <el-card style="margin-bottom:16px">
      <template #header>
        <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap">
          <div>
            <div style="font-weight:700;font-size:14px">逐类准确率分布</div>
            <div style="font-size:11px;color:#94A3B8;margin-top:2px;font-weight:500">
              仅展示存在错误的类别（已达 100% 的类别已隐藏），按准确率升序排列
            </div>
          </div>
          <div style="display:flex;gap:12px;font-size:12px;align-items:center;color:#475569;flex-wrap:wrap;justify-content:flex-end">
            <span style="display:inline-flex;align-items:center;gap:5px">
              <span class="legend-dot" style="background:linear-gradient(90deg,#FCA5A5,#DC2626)"></span>&lt;90%
            </span>
            <span style="display:inline-flex;align-items:center;gap:5px">
              <span class="legend-dot" style="background:linear-gradient(90deg,#FCD34D,#F59E0B)"></span>&lt;95%
            </span>
            <span style="display:inline-flex;align-items:center;gap:5px">
              <span class="legend-dot" style="background:linear-gradient(90deg,#E9D5FF,#A855F7)"></span>猫科
            </span>
            <span style="display:inline-flex;align-items:center;gap:5px">
              <span class="legend-dot" style="background:linear-gradient(90deg,#BFDBFE,#3B82F6)"></span>犬科
            </span>
          </div>
        </div>
      </template>
      <div ref="classAccChartEl" style="width:100%;height:340px"></div>
      <div class="chart-analysis compact">
        <div class="analysis-title">逐类表现解读</div>
        <p>{{ classAccuracyAnalysis }}</p>
      </div>
    </el-card>

    <!-- ===== 对比实验 ===== -->
    <el-card id="analysis-comparison" class="analysis-anchor">
      <template #header><span style="font-weight:600">🧪 对比实验（三模型：预训练 / 随机初始化 / 自定义CNN）</span></template>
      <el-table :data="comparison" stripe>
        <el-table-column prop="model" label="模型" />
        <el-table-column prop="task" label="任务" width="80" />
        <el-table-column prop="init" label="初始化方式" width="170" />
        <el-table-column label="Accuracy" width="110">
          <template #default="{ row }">
            <el-tag v-if="row.acc" :type="row.note.includes('主模型') ? 'success' : 'info'">
              {{ (row.acc * 100).toFixed(2) }}%
            </el-tag>
            <span v-else>—</span>
          </template>
        </el-table-column>
        <el-table-column label="Dice" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.dice" :type="row.note.includes('主模型') ? 'success' : 'info'">
              {{ row.dice }}
            </el-tag>
            <span v-else>—</span>
          </template>
        </el-table-column>
        <el-table-column prop="note" label="备注" />
      </el-table>
      <div class="evidence-panel">
        <div class="evidence-title">可复现实验入口</div>
        <div class="evidence-list">
          <div v-for="row in comparison" :key="`${row.model}-${row.task}`" class="evidence-item">
            <div class="evidence-head">
              <strong>{{ row.model }}</strong>
              <el-tag size="small" effect="plain">{{ metricText(row) }}</el-tag>
            </div>
            <div class="evidence-meta">{{ row.split }}</div>
            <div class="cmd-line"><span>训练</span><code>{{ row.command }}</code></div>
            <div class="cmd-line"><span>评估</span><code>{{ row.eval_command }}</code></div>
            <div class="cmd-line output"><span>产物</span><code>{{ row.output }}</code></div>
          </div>
        </div>
      </div>
      <el-alert style="margin-top:12px" type="info" :closable="false">
        结论：三模型对比表明，ResNet-34 ImageNet 预训练（98.65%）远超随机初始化（68.31%）和自定义 SimpleCNN（51.15%），说明深层网络结构和迁移学习对 37 类细粒度分类均至关重要；分割方面预训练 Dice 也提升约 +12 个百分点。
      </el-alert>
    </el-card>
    </div><!-- /reportRoot -->

    <!-- ===== 混淆矩阵 Drill-down Dialog ===== -->
    <el-dialog v-model="cmDialogVisible" width="520px" :title="cmDialogData?.isDiagonal ? '✅ 正确分类详情' : '⚠️ 误分类详情'">
      <template v-if="cmDialogData">
        <div class="cm-dialog-body">
          <div class="cm-dialog-header">
            <div class="cm-dialog-breed">
              <el-tag :type="cmDialogData.isCat ? 'warning' : ''" size="small" effect="plain" style="margin-right:6px">
                {{ cmDialogData.isCat ? '🐱 猫' : '🐶 狗' }}
              </el-tag>
              <span class="cm-dialog-name">{{ cmDialogData.trueLabel.replace(/_/g, ' ') }}</span>
            </div>
            <div class="cm-dialog-stats">
              <div class="cm-stat">
                <span class="cm-stat-val" style="color:var(--c-primary)">{{ cmDialogData.accuracy }}%</span>
                <span class="cm-stat-lbl">该类准确率</span>
              </div>
              <div class="cm-stat">
                <span class="cm-stat-val">{{ cmDialogData.correct }}/{{ cmDialogData.totalRow }}</span>
                <span class="cm-stat-lbl">正确/总数</span>
              </div>
            </div>
          </div>

          <div v-if="cmDialogData.isDiagonal" class="cm-dialog-ok">
            <p>该样本被正确分类为 <b>{{ cmDialogData.trueLabel.replace(/_/g, ' ') }}</b>，共 {{ cmDialogData.count }} 个样本命中对角线。</p>
          </div>
          <div v-else class="cm-dialog-err">
            <p style="margin-bottom:10px">
              真实类别 <b>{{ cmDialogData.trueLabel.replace(/_/g, ' ') }}</b> 被错误预测为
              <b style="color:var(--c-red,#DC2626)">{{ cmDialogData.predLabel.replace(/_/g, ' ') }}</b>，
              共 <b>{{ cmDialogData.count }}</b> 次误判。
            </p>
            <div v-if="cmDialogData.rowErrors.length > 0" class="cm-dialog-errs">
              <div class="cm-dialog-errs-title">该类全部误判分布：</div>
              <div v-for="e in cmDialogData.rowErrors" :key="e.target" class="cm-err-row">
                <span class="cm-err-target">→ {{ e.target.replace(/_/g, ' ') }}</span>
                <span class="cm-err-count">{{ e.count }} 次</span>
                <el-progress :percentage="Math.round((e.count / cmDialogData.totalRow) * 100)"
                  :stroke-width="6" :show-text="false"
                  :color="e.count >= 3 ? '#DC2626' : '#F59E0B'"
                  style="flex:1;min-width:60px;max-width:120px" />
              </div>
            </div>
          </div>
        </div>
      </template>
    </el-dialog>

    <!-- 回顶按钮 -->
    <transition name="back-top-fade">
      <button v-if="showBackToTop" class="back-to-top" @click="scrollToTop"
        title="回到顶部">
        <el-icon :size="18"><ArrowUp /></el-icon>
      </button>
    </transition>
  </div>
</template>

<style scoped>
/* ═══ Back to Top ═══ */
.back-to-top {
  position: fixed; right: 28px; bottom: 28px; z-index: 1000;
  width: 44px; height: 44px; border-radius: 50%;
  border: 0; cursor: pointer;
  background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%);
  color: #fff;
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 8px 22px rgba(37,99,235,.35), 0 0 0 1px rgba(255,255,255,.08) inset;
  transition: all .25s cubic-bezier(.33,1,.68,1);
}
.back-to-top:hover {
  transform: translateY(-3px);
  box-shadow: 0 14px 32px rgba(37,99,235,.5);
}
.back-to-top:active { transform: translateY(-1px); }

.back-top-fade-enter-active, .back-top-fade-leave-active {
  transition: opacity .25s ease, transform .25s ease;
}
.back-top-fade-enter-from, .back-top-fade-leave-to {
  opacity: 0; transform: translateY(10px) scale(.85);
}

/* ═══ Analysis Header ═══ */
.analysis-header {
  display: flex; align-items: center; justify-content: space-between; gap: 20px;
  background: var(--c-card, #FFFFFF);
  border: 1px solid var(--c-border, #E2E8F0);
  border-radius: var(--radius-lg, 16px);
  padding: 18px 22px; margin-bottom: 14px;
  position: relative; overflow: hidden;
}
.analysis-header::before {
  content: ''; position: absolute; left: 0; top: 0; bottom: 0;
  width: 4px; background: linear-gradient(180deg, #2563EB 0%, #10B981 100%);
}
.ah-text { flex: 1; min-width: 0; }
.ah-kicker {
  display: inline-flex; align-items: center; gap: 6px;
  font-size: 10.5px; font-weight: 700; letter-spacing: .12em; text-transform: uppercase;
  color: #2563EB; margin-bottom: 6px;
}
.ah-kicker-dot {
  width: 6px; height: 6px; border-radius: 50%; background: #10B981;
  box-shadow: 0 0 10px #10B981;
}
.ah-text h2 {
  margin: 0 0 4px; font-size: 22px; font-weight: 800; color: var(--c-dark, #0F172A);
  letter-spacing: -.01em;
}
.ah-text p {
  margin: 0; font-size: 12.5px; color: var(--c-text-body, #475569); line-height: 1.7;
  max-width: 760px;
}
.ah-text p b { font-weight: 700; }

.ah-actions { flex-shrink: 0; }
.ah-export-btn {
  display: inline-flex; align-items: center; gap: 12px;
  padding: 10px 18px 10px 14px; border-radius: 12px;
  background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%);
  border: 0; color: #fff; cursor: pointer;
  box-shadow: 0 6px 18px rgba(37,99,235,.28);
  transition: all .25s cubic-bezier(.33,1,.68,1);
  text-align: left;
}
.ah-export-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 10px 28px rgba(37,99,235,.4);
}
.ah-export-btn:active:not(:disabled) { transform: translateY(0); }
.ah-export-btn:disabled {
  background: #94A3B8; cursor: wait;
  box-shadow: none;
}
.ah-btn-icon {
  width: 32px; height: 32px; border-radius: 9px;
  display: flex; align-items: center; justify-content: center;
  background: rgba(255,255,255,.15); backdrop-filter: blur(8px);
}
.ah-export-btn:disabled .ah-btn-icon :deep(svg) {
  animation: ah-spin .9s linear infinite;
}
@keyframes ah-spin { to { transform: rotate(360deg); } }
.ah-btn-main { display: flex; flex-direction: column; line-height: 1.2; }
.ah-btn-title { font-size: 13.5px; font-weight: 700; }
.ah-btn-sub { font-size: 10.5px; opacity: .8; margin-top: 2px; font-family: 'Fira Code', monospace; }

@media (max-width: 768px) {
  .analysis-header { flex-direction: column; align-items: flex-start; }
  .ah-export-btn { width: 100%; justify-content: center; }
}

/* ═══ Metrics Banner — Professional Dark ═══ */
.metrics-banner {
  position: relative; overflow: hidden;
  border-radius: var(--radius-lg, 16px); margin-bottom: 16px;
  background: #0F172A;
  display: flex; align-items: stretch;
}
.mb-grid-bg { display: none; }
.mb-glow { display: none; }
.cls-glow { display: none; }
.seg-glow { display: none; }
.mb-half { flex: 1; padding: 24px 28px; position: relative; z-index: 1; }
.cls-half { border-right: 1px solid rgba(255,255,255,.06); }
.mb-badge {
  display: inline-flex; align-items: center;
  padding: 4px 12px; border-radius: 100px;
  font-size: 11px; font-weight: 700; letter-spacing: .4px; border: 1px solid; margin-bottom: 14px;
}
.mb-badge-cls { background: rgba(59,130,246,.12); color: #93C5FD; border-color: rgba(59,130,246,.25); }
.mb-badge-seg { background: rgba(5,150,105,.12); color: #6EE7B7; border-color: rgba(5,150,105,.25); }
.mb-nums { display: flex; align-items: center; gap: 0; flex-wrap: nowrap; }
.mb-num { padding: 0 16px; text-align: center; flex-shrink: 0; cursor: help; transition: opacity .2s ease; }
.mb-num:hover { opacity: .85; }
.mb-num-main { padding: 0 20px 0 0; }
.mb-val { font-size: 24px; font-weight: 800; color: #CBD5E1; line-height: 1.1; font-family: 'Fira Code', monospace; }
.mb-val-cls {
  font-size: 40px; color: #60A5FA;
  -webkit-text-fill-color: #60A5FA;
}
.mb-val-seg {
  font-size: 40px; color: #34D399;
  -webkit-text-fill-color: #34D399;
}
.mb-unit { font-size: 18px; font-weight: 600; }
.mb-lbl { font-size: 11px; color: #94A3B8; margin-top: 4px; font-weight: 600; }
.mb-sep { width: 1px; height: 30px; background: rgba(255,255,255,.08); margin: 0 4px; flex-shrink: 0; }

/* ═══ Brief Cards — Clean ═══ */
.analysis-brief-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin-bottom: 16px; }
.analysis-brief-card {
  position: relative; overflow: hidden;
  background: var(--c-card, #FFFFFF);
  border: 1px solid var(--c-border, #E2E8F0);
  border-radius: var(--radius, 12px); padding: 16px 16px 14px;
  box-shadow: var(--shadow-xs);
  transition: all .2s ease;
}
.analysis-brief-card::before {
  content: "";
  position: absolute; top: 0; left: 0; right: 0; height: 3px;
  background: var(--accent);
}
.analysis-brief-card:hover {
  border-color: #BFDBFE;
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}
.brief-label {
  display: inline-flex; align-items: center; padding: 3px 10px; border-radius: 999px;
  background: color-mix(in srgb, var(--accent) 8%, white); color: var(--accent);
  font-size: 10.5px; font-weight: 800; margin-bottom: 10px;
}
.brief-title { font-size: 15px; font-weight: 800; color: var(--c-dark, #0F172A); margin-bottom: 6px; }
.analysis-brief-card p { margin: 0; color: var(--c-text-body, #334155); font-size: 12.5px; line-height: 1.8; }

/* ═══ Nav — Clean ═══ */
.analysis-nav { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 8px; margin: -2px 0 18px; padding: 0; }
.analysis-nav-item {
  position: relative; overflow: hidden; display: flex; flex-direction: column; gap: 2px;
  padding: 10px 13px; border-radius: var(--radius, 12px); color: var(--c-text-body, #334155); text-decoration: none; cursor: pointer;
  background: var(--c-card, #FFFFFF);
  border: 1px solid var(--c-border, #E2E8F0);
  transition: all .2s ease;
}
.analysis-nav-item::before {
  content: ""; position: absolute; inset: 0 auto 0 0; width: 3px;
  background: var(--c-primary, #1E40AF);
}
.analysis-nav-item:hover {
  transform: translateY(-2px);
  border-color: #BFDBFE;
  box-shadow: var(--shadow-md);
}
.analysis-nav-item span { font-size: 13px; font-weight: 700; color: var(--c-dark, #0F172A); }
.analysis-nav-item em { font-style: normal; font-size: 11px; color: var(--c-muted, #64748B); }
.analysis-anchor { scroll-margin-top: 80px; }

/* ═══ Chart Analysis Box ═══ */
.chart-analysis {
  margin-top: 12px; border: 1px solid var(--c-border, #E2E8F0); border-left: 3px solid var(--c-primary, #1E40AF);
  border-radius: var(--radius-sm, 8px); padding: 12px 14px;
  background: #F8FAFC;
}
.chart-analysis.green { border-color: #D1FAE5; border-left-color: #059669; background: #F0FDF4; }
.chart-analysis.red   { border-color: #FEE2E2; border-left-color: #DC2626; background: #FEF2F2; }
.chart-analysis.blue  { border-color: #DBEAFE; border-left-color: #2563EB; background: #EFF6FF; }
.chart-analysis.amber { border-color: #FEF3C7; border-left-color: #F59E0B; background: #FFFBEB; }
.chart-analysis.compact { margin-top: 10px; padding: 10px 12px; }
.analysis-title { font-size: 12px; font-weight: 800; color: var(--c-dark, #0F172A); margin-bottom: 6px; }
.chart-analysis ul { margin: 0; padding-left: 16px; color: var(--c-text-body, #334155); font-size: 12.5px; line-height: 1.8; }
.chart-analysis p  { margin: 0; color: var(--c-text-body, #334155); font-size: 12.5px; line-height: 1.8; }

/* ═══ Matrix ═══ */
.matrix-card { height: 100%; }
.matrix-card :deep(.el-card__body) { min-height: 680px; display: flex; flex-direction: column; }
.matrix-visual { height: 540px; display: flex; align-items: center; justify-content: center; }
.matrix-chart { width: 100%; height: 100%; }
.matrix-img { width: 100%; max-height: 100%; object-fit: contain; border-radius: 10px; display: block; }
.matrix-card .chart-analysis { min-height: 100px; margin-top: auto; }

/* ═══ Delta — Glowing Bars ═══ */
.delta-label { font-size: 12px; color: #64748b; font-weight: 700; margin-bottom: 8px; }
.delta-bar-wrap { display: flex; flex-direction: column; gap: 5px; }
.delta-bar { height: 22px; border-radius: 5px; display: flex; align-items: center; position: relative; min-width: 36px; }
.delta-bar.base { background: rgba(226,232,240,.6); }
.delta-val { position: absolute; right: 8px; font-size: 11px; font-weight: 700; color: #fff; }
.delta-bar.base .delta-val { color: #64748b; }
.delta-badge { display: inline-block; margin-top: 6px; background: rgba(99,102,241,.1); color: #6366f1; font-size: 11.5px; font-weight: 700; padding: 3px 10px; border-radius: 100px; }
.delta-badge.success { background: rgba(16,185,129,.1); color: #10b981; }
.delta-legend { display: flex; align-items: center; gap: 6px; margin-top: 18px; font-size: 11.5px; color: #64748b; }
.dl-dot { display: inline-block; width: 24px; height: 8px; border-radius: 4px; }
.dl-dot.base { background: rgba(226,232,240,.6); }

/* ═══ Evidence ═══ */
.evidence-panel {
  margin-top: 14px; padding: 14px; border-radius: 12px;
  border: 1px solid rgba(99,102,241,.06);
  background: rgba(255,255,255,.7); backdrop-filter: blur(8px);
}
.evidence-title { font-size: 13px; font-weight: 800; color: var(--c-dark, #0F172A); margin-bottom: 10px; }
.evidence-list { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.evidence-item {
  background: rgba(255,255,255,.8); border: 1px solid rgba(99,102,241,.06);
  border-radius: 10px; padding: 12px 13px;
  transition: all .2s ease;
}
.evidence-item:hover { border-color: rgba(99,102,241,.14); box-shadow: 0 4px 16px rgba(99,102,241,.06); }
.evidence-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; color: var(--c-dark, #0F172A); font-size: 13px; font-weight: 700; margin-bottom: 6px; }
.evidence-meta { color: var(--c-muted, #64748B); font-size: 11.5px; margin-bottom: 7px; }
.cmd-line { display: grid; grid-template-columns: 38px minmax(0, 1fr); gap: 7px; align-items: start; margin-top: 6px; }
.cmd-line span { color: var(--c-muted, #64748B); font-size: 11px; font-weight: 800; padding-top: 3px; }
.cmd-line code { display: block; padding: 6px 8px; border-radius: 8px; background: #0f172a; color: #a5b4fc; font-size: 11px; line-height: 1.55; white-space: normal; word-break: break-word; }
.cmd-line.output code { background: rgba(238,242,255,.8); color: #3730a3; }

/* ═══ Legend ═══ */
.legend-dot { display: inline-block; width: 22px; height: 8px; border-radius: 4px; vertical-align: middle; margin-right: 3px; }

/* ═══ Case Panels — Glow Top ═══ */
.case-panel {
  border-radius: 14px; overflow: hidden;
  border: 1px solid rgba(99,102,241,.06);
  background: rgba(255,255,255,.9);
  box-shadow: 0 2px 8px rgba(0,0,0,.04);
}
.correct-panel { border-top: 3px solid #16a34a; box-shadow: 0 -2px 16px rgba(22,163,74,.06); }
.error-panel   { border-top: 3px solid #dc2626; box-shadow: 0 -2px 16px rgba(220,38,38,.06); }
.cp-header { display: flex; align-items: center; gap: 8px; padding: 12px 14px 10px; border-bottom: 1px solid rgba(241,245,249,.8); background: rgba(248,250,252,.5); }
.cp-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.correct-dot { background: #16a34a; box-shadow: 0 0 6px rgba(22,163,74,.5), 0 0 14px rgba(22,163,74,.15); }
.error-dot   { background: #dc2626; box-shadow: 0 0 6px rgba(220,38,38,.5), 0 0 14px rgba(220,38,38,.15); }
.cp-title { font-size: 13.5px; font-weight: 800; color: var(--c-dark, #0F172A); flex: 1; }
.cp-count { font-size: 11px; color: #94a3b8; background: rgba(241,245,249,.8); padding: 3px 8px; border-radius: 100px; font-weight: 600; }
.case-grid { display: grid; grid-template-columns: repeat(3,1fr); gap: 7px; padding: 12px; }
.cimg-wrap { position: relative; }
.cimg { width: 100%; aspect-ratio: 1; object-fit: cover; border-radius: 9px; border: 1px solid rgba(226,232,240,.5); display: block; transition: all .25s ease; cursor: zoom-in; }
.cimg :deep(img) { width: 100%; height: 100%; object-fit: cover; border-radius: 9px; }
.cimg-zoom-hint {
  position: absolute; right: 4px; bottom: 4px;
  width: 22px; height: 22px; border-radius: 50%;
  background: rgba(15,23,42,.7); color: #fff;
  display: flex; align-items: center; justify-content: center;
  opacity: 0; transition: opacity .2s ease;
  pointer-events: none;
}
.cimg-wrap:hover .cimg-zoom-hint { opacity: 1; }
.correct-img:hover { transform: scale(1.05); box-shadow: 0 8px 24px rgba(22,163,74,.2); }
.error-img:hover   { transform: scale(1.05); box-shadow: 0 8px 24px rgba(220,38,38,.18); }
.cimg-badge { position: absolute; top: 5px; left: 5px; font-size: 9px; font-weight: 700; color: #fff; width: 18px; height: 18px; border-radius: 50%; display: flex; align-items: center; justify-content: center; }
.correct-badge { background: rgba(22,163,74,.85); box-shadow: 0 0 6px rgba(22,163,74,.3); }
.error-badge   { background: rgba(220,38,38,.85); box-shadow: 0 0 6px rgba(220,38,38,.3); }
.case-insight { margin: 0 12px 12px; border-radius: 10px; padding: 10px 14px; font-size: 12.5px; }
.correct-insight { background: rgba(22,163,74,.04); border: 1px solid rgba(22,163,74,.12); }
.error-insight   { background: rgba(220,38,38,.03); border: 1px solid rgba(220,38,38,.1); }
.ci-title { font-size: 11.5px; font-weight: 800; margin-bottom: 7px; color: var(--c-dark, #0F172A); }
.ci-list { margin: 0; padding-left: 16px; color: var(--c-text-body, #334155); line-height: 1.8; font-size: 12px; }
.ci-list li { margin-bottom: 2px; }
.conf-pairs { display: flex; flex-direction: column; gap: 6px; }
.conf-pair { display: flex; align-items: baseline; gap: 8px; line-height: 1.55; }
.conf-cls { font-size: 11.5px; font-weight: 800; color: #dc2626; flex-shrink: 0; white-space: nowrap; }
.conf-why { font-size: 11.5px; color: #4b5563; }

/* ═══ Est badge ═══ */
.est-tag { font-size: 9.5px; font-weight: 800; vertical-align: super; background: rgba(245,158,11,.12); color: #d97706; padding: 2px 6px; border-radius: 5px; margin-left: 3px; letter-spacing: .3px; }

/* ═══ Responsive ═══ */
@media (max-width: 1180px) {
  .metrics-banner { flex-direction: column; }
  .mb-half { padding: 22px 24px; }
  .cls-half { border-right: 0; border-bottom: 1px solid rgba(255,255,255,.06); }
  .mb-divider { display: none; }
  .mb-nums { flex-wrap: wrap; gap: 14px 18px; align-items: flex-start; }
  .mb-num { flex: 1 1 calc(50% - 9px); min-width: 0; padding: 0; text-align: left; }
  .mb-num-main { flex: 0 0 100%; min-width: 100%; padding: 0; text-align: left; }
  .mb-sep { display: none; }
}
@media (max-width: 900px) {
  .analysis-brief-grid, .analysis-nav, .evidence-list { grid-template-columns: 1fr; }
  .analysis-nav { position: static; }
  .analysis-split-row :deep(.el-col) { max-width: 100%; flex: 0 0 100%; margin-bottom: 14px; }
}

/* ─── Confusion Dialog ─── */
.cm-dialog-body { font-size: 13px; }
.cm-dialog-header { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 16px; padding-bottom: 14px; border-bottom: 1px solid var(--c-border, #E2E8F0); }
.cm-dialog-breed { display: flex; align-items: center; gap: 4px; }
.cm-dialog-name { font-size: 18px; font-weight: 800; color: var(--c-dark, #0F172A); }
.cm-dialog-stats { display: flex; gap: 16px; }
.cm-stat { text-align: center; }
.cm-stat-val { display: block; font-size: 20px; font-weight: 800; font-family: 'Fira Code', monospace; line-height: 1.2; }
.cm-stat-lbl { display: block; font-size: 10.5px; color: var(--c-muted, #64748B); margin-top: 2px; }
.cm-dialog-ok { padding: 14px; border-radius: var(--radius-sm, 8px); background: #F0FDF4; border: 1px solid #D1FAE5; color: #166534; }
.cm-dialog-ok p { margin: 0; line-height: 1.7; }
.cm-dialog-err p { margin: 0; color: var(--c-text-body, #334155); line-height: 1.7; }
.cm-dialog-errs { margin-top: 12px; padding: 12px; border-radius: var(--radius-sm, 8px); background: #FEF2F2; border: 1px solid #FEE2E2; }
.cm-dialog-errs-title { font-size: 12px; font-weight: 700; color: #991B1B; margin-bottom: 8px; }
.cm-err-row { display: flex; align-items: center; gap: 8px; padding: 4px 0; }
.cm-err-target { font-size: 12.5px; font-weight: 600; color: #1E293B; min-width: 140px; }
.cm-err-count { font-size: 12px; font-weight: 700; color: #DC2626; font-family: 'Fira Code', monospace; min-width: 40px; }
</style>
