<script setup>
import { ref, computed, onMounted, onUnmounted, reactive } from 'vue'
import { inferMultitask, inferCompare, inferGradcam, submitFeedback } from '../api'

const BACKEND = 'http://127.0.0.1:8000'

const CAT_BREEDS = new Set([
  'Abyssinian','Bengal','Birman','Bombay','British_Shorthair',
  'Egyptian_Mau','Maine_Coon','Persian','Ragdoll','Russian_Blue',
  'Siamese','Sphynx'
])

const file    = ref(null)
const preview = ref('')
const result  = ref(null)
const loading = ref(false)
const error   = ref('')
const showAllTop5 = ref(false)  /* Top-1 极高时折叠 2-5 名 */

/* ─── 内置示例图片库 (打包到前端 public/samples) ─── */
const SAMPLE_IMAGES = [
  { breed: 'Bengal',     species: 'cat', url: '/samples/Bengal.jpg' },
  { breed: 'Sphynx',     species: 'cat', url: '/samples/Sphynx.jpg' },
  { breed: 'Abyssinian', species: 'cat', url: '/samples/Abyssinian.jpg' },
  { breed: 'samoyed',    species: 'dog', url: '/samples/samoyed.jpg' },
  { breed: 'pug',        species: 'dog', url: '/samples/pug.jpg' },
  { breed: 'beagle',     species: 'dog', url: '/samples/beagle.jpg' },
]
async function useSample(sample) {
  loading.value = true
  error.value = ''
  result.value = null
  try {
    const resp = await fetch(sample.url)
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    const blob = await resp.blob()
    const f = new File([blob], `sample_${sample.breed}.jpg`, { type: blob.type || 'image/jpeg' })
    file.value = f
    preview.value = URL.createObjectURL(f)
  } catch (e) {
    console.error('Sample load failed:', e)
    error.value = `加载示例图片失败：${e.message || e}`
  } finally {
    loading.value = false
  }
}

/* ─── 模式: single | batch | compare ─── */
const mode = ref('single')
const batchMode = computed(() => mode.value === 'batch')
const compareMode = computed(() => mode.value === 'compare')

/* ─── Batch Mode (state machine) ─── */
const batchTasks   = ref([])  /* { id, raw, name, preview, status, result, error, elapsed } */
const batchRunning = ref(false)
const batchFilter  = ref('all')   /* all|cat|dog|low|err */
const batchSort    = ref('order') /* order|conf-desc|conf-asc */
const batchDetail  = reactive({ visible: false, task: null })
const BATCH_CONCURRENCY = 3
let batchSeq = 0

/* ─── 三模型对比 ─── */
const compareFile    = ref(null)
const comparePreview = ref('')
const compareResult  = ref(null)
const compareLoading = ref(false)
const compareError   = ref('')
function onCompareFile(uploadFile) {
  compareFile.value    = uploadFile.raw
  comparePreview.value = URL.createObjectURL(uploadFile.raw)
  compareResult.value  = null
  compareError.value   = ''
}
async function runCompare() {
  if (!compareFile.value) return
  compareLoading.value = true
  compareError.value = ''
  try {
    const { data } = await inferCompare(compareFile.value)
    compareResult.value = data
  } catch (e) {
    compareError.value = '对比推理失败：' + (e.message || e)
  } finally {
    compareLoading.value = false
  }
}

/* ─── WebSocket 实时日志 ─── */
const wsEnabled  = ref(false)
const wsLog      = ref([])  /* {t, level, msg} */
const wsProgress = ref(0)
const wsState    = ref('idle')  /* idle|connecting|running|done|error */
let wsSocket = null

function clearWsLog() {
  wsLog.value = []
  wsProgress.value = 0
  wsState.value = 'idle'
}
async function runInferWS() {
  if (!file.value) return
  clearWsLog()
  wsState.value = 'connecting'
  showAllTop5.value = false
  result.value = null
  error.value = ''

  const url = `ws://${new URL(BACKEND).host}/ws/infer`
  wsSocket = new WebSocket(url)
  wsSocket.binaryType = 'arraybuffer'

  wsSocket.onopen = async () => {
    wsState.value = 'running'
    wsLog.value.push({ t: timeNow(), level: 'info', msg: 'WebSocket 已连接，发送图片字节…' })
    const buf = await file.value.arrayBuffer()
    wsSocket.send(buf)
  }
  wsSocket.onmessage = (ev) => {
    try {
      const m = JSON.parse(ev.data)
      wsLog.value.push({ t: m.t, level: m.level, msg: m.msg })
      if (typeof m.progress === 'number') wsProgress.value = m.progress
      if (m.level === 'done' && m.result) {
        result.value = m.result
        wsState.value = 'done'
        saveHistory({
          time: new Date().toLocaleString('zh-CN'),
          breed: m.result.class_top1,
          confidence: m.result.class_confidence,
          area: m.result.pet_area_ratio,
          fileName: file.value?.name,
        })
      }
      if (m.level === 'error') wsState.value = 'error'
    } catch {}
  }
  wsSocket.onerror = () => {
    wsState.value = 'error'
    wsLog.value.push({ t: timeNow(), level: 'error', msg: 'WebSocket 错误' })
  }
  wsSocket.onclose = () => {
    if (wsState.value === 'running') wsState.value = 'done'
  }
}
function timeNow() {
  return new Date().toTimeString().slice(0, 8)
}

/* ─── 错误反馈表单 ─── */
const feedbackVisible = ref(false)
const feedbackForm = reactive({ correctBreed: '', note: '' })
const feedbackSubmitting = ref(false)
const feedbackDone = ref(false)
async function openFeedback() {
  feedbackForm.correctBreed = ''
  feedbackForm.note = ''
  feedbackDone.value = false
  feedbackVisible.value = true
}
async function sendFeedback() {
  if (!result.value || !feedbackForm.correctBreed) return
  feedbackSubmitting.value = true
  try {
    await submitFeedback({
      file_name: file.value?.name || '',
      predicted_breed: result.value.class_top1,
      predicted_confidence: result.value.class_confidence,
      correct_breed: feedbackForm.correctBreed,
      note: feedbackForm.note || null,
    })
    feedbackDone.value = true
    setTimeout(() => { feedbackVisible.value = false }, 1200)
  } catch (e) {
    /* keep dialog open */
  } finally {
    feedbackSubmitting.value = false
  }
}

/* 全部品种列表 (37 类) — 用于 feedback 下拉框 */
const ALL_BREEDS = [
  'Abyssinian','Bengal','Birman','Bombay','British_Shorthair','Egyptian_Mau',
  'Maine_Coon','Persian','Ragdoll','Russian_Blue','Siamese','Sphynx',
  'american_bulldog','american_pit_bull_terrier','basset_hound','beagle','boxer',
  'chihuahua','english_cocker_spaniel','english_setter','german_shorthaired',
  'great_pyrenees','havanese','japanese_chin','keeshond','leonberger',
  'miniature_pinscher','newfoundland','pomeranian','pug','saint_bernard',
  'samoyed','scottish_terrier','shiba_inu','staffordshire_bull_terrier',
  'wheaten_terrier','yorkshire_terrier'
]

/* ─── History ─── */
const HISTORY_KEY = 'pet-vision-history'
const history = ref([])
const showHistory = ref(false)

function loadHistory() {
  try {
    history.value = JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]')
  } catch { history.value = [] }
}
function saveHistory(item) {
  history.value.unshift(item)
  if (history.value.length > 50) history.value = history.value.slice(0, 50)
  localStorage.setItem(HISTORY_KEY, JSON.stringify(history.value))
}
function clearHistory() {
  history.value = []
  localStorage.removeItem(HISTORY_KEY)
}

onMounted(() => {
  loadHistory()
  window.addEventListener('paste', onClipboardPaste)
})
onUnmounted(() => {
  window.removeEventListener('paste', onClipboardPaste)
  /* 释放摄像头流 */
  if (cameraStream.value) {
    cameraStream.value.getTracks().forEach(t => t.stop())
    cameraStream.value = null
  }
})

const hasResult = computed(() => result.value !== null)

function onFileChange(uploadFile) {
  file.value    = uploadFile.raw
  preview.value = URL.createObjectURL(uploadFile.raw)
  result.value  = null
  error.value   = ''
}

async function runInfer() {
  if (!file.value) return
  loading.value = true
  error.value   = ''
  showAllTop5.value = false
  try {
    const { data } = await inferMultitask(file.value)
    result.value = data
    saveHistory({
      time: new Date().toLocaleString('zh-CN'),
      breed: data.class_top1,
      confidence: data.class_confidence,
      area: data.pet_area_ratio,
      fileName: file.value.name,
    })
    /* 推理完成后异步生成 Grad-CAM 热力图 (不阻塞主结果) */
    fetchGradcam(file.value).catch(() => {})
  } catch {
    error.value = '推理失败，请确认后端已启动（http://127.0.0.1:8000）'
  } finally {
    loading.value = false
  }
}

const gradcamLoading = ref(false)
async function fetchGradcam(f) {
  if (!f) return
  gradcamLoading.value = true
  try {
    const { data } = await inferGradcam(f)
    if (data?.heatmap_url && result.value) {
      result.value = { ...result.value, gradcam_url: data.heatmap_url }
    }
  } finally {
    gradcamLoading.value = false
  }
}

/* ─── 实时摄像头 ─── */
const cameraVisible = ref(false)
const cameraVideoEl = ref(null)
const cameraStream  = ref(null)
const cameraError   = ref('')
const cameraReady   = ref(false)

async function openCamera() {
  cameraError.value = ''
  cameraReady.value = false
  cameraVisible.value = true
  try {
    if (!navigator.mediaDevices?.getUserMedia) {
      throw new Error('当前浏览器不支持 getUserMedia API')
    }
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'user' },
      audio: false,
    })
    cameraStream.value = stream
    /* 等待 dialog 渲染完成 */
    await new Promise(r => setTimeout(r, 50))
    if (cameraVideoEl.value) {
      cameraVideoEl.value.srcObject = stream
      cameraVideoEl.value.onloadedmetadata = () => {
        cameraVideoEl.value.play()
        cameraReady.value = true
      }
    }
  } catch (e) {
    cameraError.value = e?.message || '摄像头访问失败，请检查权限设置'
  }
}

function closeCamera() {
  if (cameraStream.value) {
    cameraStream.value.getTracks().forEach(t => t.stop())
    cameraStream.value = null
  }
  cameraReady.value = false
  cameraVisible.value = false
}

async function captureCamera() {
  if (!cameraVideoEl.value || !cameraReady.value) return
  const video = cameraVideoEl.value
  const canvas = document.createElement('canvas')
  canvas.width = video.videoWidth
  canvas.height = video.videoHeight
  const ctx = canvas.getContext('2d')
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
  const blob = await new Promise(r => canvas.toBlob(r, 'image/jpeg', 0.92))
  if (!blob) return
  const captured = new File([blob], `camera_${Date.now()}.jpg`, { type: 'image/jpeg' })
  /* 走单张推理流程 */
  file.value = captured
  preview.value = URL.createObjectURL(captured)
  result.value = null
  error.value = ''
  closeCamera()
  /* 自动触发推理 */
  runInfer()
}

/* ─── Batch (state machine + concurrent) ─── */
function addBatchFile(rawFile, displayName) {
  if (!rawFile.type?.startsWith('image/')) return
  batchTasks.value.push({
    id: ++batchSeq,
    raw: rawFile,
    name: displayName || rawFile.name || `image_${batchSeq}.jpg`,
    preview: URL.createObjectURL(rawFile),
    status: 'pending',
    result: null,
    error: null,
    elapsed: 0,
  })
}
function onBatchChange(uploadFile) {
  addBatchFile(uploadFile.raw, uploadFile.name)
}

/* 剪贴板粘贴图片 */
function onClipboardPaste(e) {
  if (!batchMode.value) return
  const items = e.clipboardData?.items
  if (!items) return
  let added = 0
  for (const item of items) {
    if (item.type.startsWith('image/')) {
      const blob = item.getAsFile()
      if (blob) {
        const ext = (blob.type.split('/')[1] || 'png').replace('jpeg', 'jpg')
        const f = new File([blob], `clipboard_${Date.now()}_${++added}.${ext}`, { type: blob.type })
        addBatchFile(f)
      }
    }
  }
}

/* 拖拽：包括文件夹（递归） */
async function readEntries(entry, files) {
  if (entry.isFile) {
    await new Promise(resolve => entry.file(f => { files.push(f); resolve() }))
  } else if (entry.isDirectory) {
    const reader = entry.createReader()
    await new Promise(resolve => {
      const readBatch = () => {
        reader.readEntries(async (entries) => {
          if (!entries.length) return resolve()
          for (const e of entries) await readEntries(e, files)
          readBatch()
        })
      }
      readBatch()
    })
  }
}
async function onBatchDrop(e) {
  if (!batchMode.value) return
  e.preventDefault()
  const items = e.dataTransfer?.items
  if (!items) return
  const files = []
  const tasks = []
  for (const it of items) {
    const entry = it.webkitGetAsEntry?.()
    if (entry) tasks.push(readEntries(entry, files))
    else if (it.kind === 'file') {
      const f = it.getAsFile()
      if (f) files.push(f)
    }
  }
  await Promise.all(tasks)
  for (const f of files) addBatchFile(f)
}
function removeBatchTask(id) {
  const t = batchTasks.value.find(x => x.id === id)
  if (t?.preview?.startsWith('blob:')) URL.revokeObjectURL(t.preview)
  batchTasks.value = batchTasks.value.filter(x => x.id !== id)
}
function clearBatch() {
  batchTasks.value.forEach(t => t.preview?.startsWith('blob:') && URL.revokeObjectURL(t.preview))
  batchTasks.value = []
}

async function inferOne(task) {
  task.status = 'running'
  task.error = null
  const t0 = performance.now()
  try {
    const { data } = await inferMultitask(task.raw)
    task.result = data
    task.elapsed = Math.round(performance.now() - t0)
    task.status = 'done'
    saveHistory({
      time: new Date().toLocaleString('zh-CN'),
      breed: data.class_top1,
      confidence: data.class_confidence,
      area: data.pet_area_ratio,
      fileName: task.name,
    })
  } catch (e) {
    task.error = e?.message || '推理失败'
    task.status = 'error'
  }
}

async function runBatchInfer() {
  const queue = batchTasks.value.filter(t => t.status === 'pending' || t.status === 'error')
  if (!queue.length || batchRunning.value) return
  batchRunning.value = true
  /* worker pool */
  const workers = Array.from({ length: BATCH_CONCURRENCY }, async () => {
    while (queue.length) {
      const next = queue.shift()
      if (!next) break
      await inferOne(next)
    }
  })
  await Promise.all(workers)
  batchRunning.value = false
}

async function retryTask(task) {
  task.status = 'pending'
  await inferOne(task)
}
async function retryAllFailed() {
  const failed = batchTasks.value.filter(t => t.status === 'error')
  failed.forEach(t => { t.status = 'pending' })
  await runBatchInfer()
}

function openDetail(task) {
  if (task.status !== 'done') return
  batchDetail.task = task
  batchDetail.visible = true
}

function exportBatchCSV() {
  const done = batchTasks.value.filter(t => t.status === 'done')
  if (!done.length) return
  const header = ['file', 'breed', 'confidence', 'area_ratio', 'top2_breed', 'top2_conf', 'latency_ms']
  const rows = done.map(t => [
    t.name,
    t.result.class_top1,
    t.result.class_confidence.toFixed(4),
    t.result.pet_area_ratio.toFixed(4),
    t.result.top5?.[1]?.label || '',
    t.result.top5?.[1]?.confidence?.toFixed(4) || '',
    t.result.latency_ms,
  ])
  const csv = [header, ...rows].map(r => r.map(v => `"${String(v).replace(/"/g, '""')}"`).join(',')).join('\n')
  const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `batch_results_${Date.now()}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

/* ─── Batch derived stats ─── */
const batchStats = computed(() => {
  const tasks = batchTasks.value
  const done = tasks.filter(t => t.status === 'done')
  const errs = tasks.filter(t => t.status === 'error')
  const running = tasks.filter(t => t.status === 'running').length
  const cats = done.filter(t => CAT_BREEDS.has(t.result.class_top1)).length
  const dogs = done.length - cats
  const avgConf = done.length ? done.reduce((s, t) => s + t.result.class_confidence, 0) / done.length : 0
  const totalTime = done.reduce((s, t) => s + (t.elapsed || 0), 0)
  const lowConf = done.filter(t => t.result.class_confidence < 0.5).length
  return {
    total: tasks.length,
    done: done.length,
    failed: errs.length,
    running,
    pending: tasks.length - done.length - errs.length - running,
    cats, dogs, avgConf, totalTime, lowConf,
    progress: tasks.length ? Math.round(((done.length + errs.length) / tasks.length) * 100) : 0,
  }
})

const filteredTasks = computed(() => {
  let arr = [...batchTasks.value]
  if (batchFilter.value === 'cat')  arr = arr.filter(t => t.status === 'done' && CAT_BREEDS.has(t.result.class_top1))
  if (batchFilter.value === 'dog')  arr = arr.filter(t => t.status === 'done' && !CAT_BREEDS.has(t.result.class_top1))
  if (batchFilter.value === 'low')  arr = arr.filter(t => t.status === 'done' && t.result.class_confidence < 0.5)
  if (batchFilter.value === 'err')  arr = arr.filter(t => t.status === 'error')
  if (batchSort.value === 'conf-desc') arr.sort((a, b) => (b.result?.class_confidence || 0) - (a.result?.class_confidence || 0))
  if (batchSort.value === 'conf-asc')  arr.sort((a, b) => (a.result?.class_confidence || 1) - (b.result?.class_confidence || 1))
  return arr
})

function confColorOf(c) {
  if (c >= 0.8) return '#22c55e'
  if (c >= 0.5) return '#f59e0b'
  return '#ef4444'
}
function isCat(breed) { return CAT_BREEDS.has(breed) }

const confPct = computed(() =>
  result.value ? parseFloat((result.value.class_confidence * 100).toFixed(1)) : 0
)
const confColor = computed(() => {
  const c = result.value ? result.value.class_confidence : 0
  if (c >= 0.8) return '#22c55e'
  if (c >= 0.5) return '#f59e0b'
  return '#ef4444'
})
const confLabel = computed(() => {
  const c = result.value ? result.value.class_confidence : 0
  if (c >= 0.8) return '高置信度'
  if (c >= 0.5) return '中置信度'
  return '低置信度'
})
const areaPct = computed(() =>
  result.value ? Math.round(result.value.pet_area_ratio * 100) : 0
)

/* ─── 复制 / 导出单张结果 ─── */
const copySuccess = ref(false)
async function copyResult() {
  if (!result.value) return
  const txt = JSON.stringify({
    file: file.value?.name,
    breed: result.value.class_top1,
    confidence: result.value.class_confidence,
    top5: result.value.top5,
    pet_area_ratio: result.value.pet_area_ratio,
    latency_ms: result.value.latency_ms,
  }, null, 2)
  try {
    await navigator.clipboard.writeText(txt)
    copySuccess.value = true
    setTimeout(() => { copySuccess.value = false }, 1500)
  } catch {
    /* fallback */
    const ta = document.createElement('textarea')
    ta.value = txt
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
    copySuccess.value = true
    setTimeout(() => { copySuccess.value = false }, 1500)
  }
}
function downloadResult() {
  if (!result.value) return
  const data = {
    timestamp: new Date().toISOString(),
    file: file.value?.name,
    classification: {
      breed: result.value.class_top1,
      confidence: result.value.class_confidence,
      top5: result.value.top5,
    },
    segmentation: {
      pet_area_ratio: result.value.pet_area_ratio,
      mask_url: BACKEND + result.value.mask_url,
      overlay_url: BACKEND + result.value.overlay_url,
    },
    latency_ms: result.value.latency_ms,
  }
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `result_${result.value.class_top1}_${Date.now()}.json`
  a.click()
  URL.revokeObjectURL(a.href)
}

const top5Visible = computed(() => {
  if (!result.value?.top5) return []
  /* Top-1 极高时仅展示 Top-1，其余收起 */
  if (!showAllTop5.value && result.value.class_confidence >= 0.99) {
    return result.value.top5.slice(0, 1)
  }
  return result.value.top5
})
const top5Collapsed = computed(() =>
  result.value?.class_confidence >= 0.99 && !showAllTop5.value
)

const tips = [
  { text: '上传清晰的宠物正面照效果最佳', color: '#22c55e' },
  { text: '支持猫、狗共 37 个品种识别',  color: '#6366f1' },
  { text: '分割结果以宠物轮廓为前景',    color: '#22d3ee' },
  { text: '置信度越高，预测越可靠',      color: '#f59e0b' },
]

const modelInfo = [
  { badge: 'CLS', color: '#6366f1', bg: 'rgba(99,102,241,.1)', label: 'ResNet-34', sub: '37类识别' },
  { badge: 'SEG', color: '#10b981', bg: 'rgba(16,185,129,.1)', label: 'U-Net',     sub: '像素级分割' },
]

const outputPreview = [
  { tag: 'CLS', title: '品种识别', desc: '输出 Top-1 品种、置信度和 Top-5 候选', color: '#6366f1' },
  { tag: 'SEG', title: '前景分割', desc: '生成宠物前景 Mask 与半透明叠加图', color: '#10b981' },
  { tag: 'AREA', title: '区域占比', desc: '估算宠物前景像素占整图比例', color: '#22d3ee' },
]

const qualityChecks = [
  '主体完整，头部和身体尽量不被遮挡',
  '避免多只宠物同时出现在画面中央',
  '背景越简单，分割边界越稳定',
  '低置信度结果建议换一张更清晰图片复测',
]
</script>

<template>
  <div class="predict-page">

    <!-- ===== 顶部 Tab 条 ===== -->
    <div class="predict-modebar">
      <div class="mb-tabs">
        <button
          v-for="tab in [
            { v: 'single',  icon: 'Camera',   label: $t('predict.tabSingle'),  desc: '单图分类 + 分割', color: '#6366F1' },
            { v: 'batch',   icon: 'Files',    label: $t('predict.tabBatch'),   desc: '多图并发推理',     color: '#10B981' },
            { v: 'compare', icon: 'DataLine', label: $t('predict.tabCompare'), desc: '三模型同图对比',   color: '#7C3AED' },
          ]"
          :key="tab.v"
          class="mb-tab"
          :class="{ active: mode === tab.v }"
          :style="{ '--tc': tab.color }"
          @click="mode = tab.v"
        >
          <div class="mb-tab-icon"><el-icon :size="16"><component :is="tab.icon" /></el-icon></div>
          <div class="mb-tab-text">
            <div class="mb-tab-label">{{ tab.label }}</div>
            <div class="mb-tab-desc">{{ tab.desc }}</div>
          </div>
        </button>
      </div>
      <button v-if="mode === 'single'" class="mb-history" @click="showHistory = !showHistory" :class="{ active: showHistory }">
        <el-icon :size="14"><Clock /></el-icon>
        <span>{{ $t('predict.history') }}</span>
        <span v-if="history.length" class="mb-history-count">{{ history.length }}</span>
      </button>
    </div>

  <div class="predict-layout" :class="`layout-${mode}`">

    <!-- ===== 左栏 (仅 single 模式显示) ===== -->
    <div v-if="mode === 'single'" class="left-col">

      <!-- Single mode upload -->
      <el-card v-if="mode === 'single'">
        <template #header>
          <div class="ph" style="justify-content:space-between;width:100%">
            <span style="display:inline-flex;align-items:center;gap:8px">
              <el-icon color="#6366f1" :size="17"><Camera /></el-icon>
              上传图片
            </span>
            <el-button size="small" type="primary" plain @click="openCamera"
              class="camera-btn-trigger">
              <el-icon style="margin-right:4px"><VideoCamera /></el-icon>
              摄像头
            </el-button>
          </div>
        </template>

        <el-upload
          drag :auto-upload="false"
          :on-change="onFileChange"
          :show-file-list="false"
          accept="image/*"
          class="uploader"
        >
          <div v-if="!preview" class="upload-idle">
            <div class="upload-icon-ring">
              <el-icon :size="28" color="#6366f1"><UploadFilled /></el-icon>
            </div>
            <p class="upload-hint">拖拽图片到此处，或<em>点击上传</em></p>
            <p class="upload-sub">JPG · PNG · WEBP · 建议使用正面宠物照</p>
          </div>
          <div v-else class="preview-box">
            <img :src="preview" class="preview-img" />
            <div class="preview-overlay">
              <el-icon color="#fff" :size="22"><RefreshRight /></el-icon>
              <span>重新选择</span>
            </div>
          </div>
        </el-upload>

        <el-button
          type="primary" size="large"
          :loading="loading || wsState === 'running'" :disabled="!file"
          @click="wsEnabled ? runInferWS() : runInfer()"
          style="width:100%;margin-top:14px;height:44px;font-size:15px;font-weight:600"
        >
          <el-icon v-if="!loading && wsState !== 'running'" style="margin-right:6px"><DataAnalysis /></el-icon>
          {{ (loading || wsState === 'running') ? $t('predict.inferring') : $t('predict.runInfer') }}
        </el-button>

        <!-- WebSocket 开关 -->
        <div class="ws-toggle">
          <el-switch v-model="wsEnabled" size="small" />
          <span>{{ $t('predict.enableRealtime') }}</span>
          <el-tooltip placement="top" :content="$t('predict.realtimeLog')">
            <el-icon :size="13" style="color:#94A3B8"><InfoFilled /></el-icon>
          </el-tooltip>
        </div>

        <!-- 示例图片库 -->
        <div class="sample-section" v-if="!preview">
          <div class="sample-title">
            <el-icon :size="13"><Picture /></el-icon>
            <span>没有图片？试试这些样例</span>
          </div>
          <div class="sample-grid">
            <button v-for="s in SAMPLE_IMAGES" :key="s.breed"
              class="sample-thumb" :class="s.species"
              @click="useSample(s)" :title="s.breed">
              <img :src="s.url" :alt="s.breed" />
              <span class="sample-badge">{{ s.species === 'cat' ? '🐱' : '🐶' }}</span>
            </button>
          </div>
        </div>

        <el-alert v-if="error" :title="error" type="error"
          show-icon :closable="false" style="margin-top:12px" />
      </el-card>

      <!-- 模型说明 (单张模式才显示) -->
      <el-card v-if="mode === 'single'" style="margin-top:12px">
        <template #header>
          <div class="ph">
            <el-icon color="#10b981" :size="17"><DataAnalysis /></el-icon>
            <span>推理模型</span>
          </div>
        </template>
        <div class="model-info-list">
          <div v-for="m in modelInfo" :key="m.badge" class="model-info-row">
            <span class="mi-badge" :style="{ background: m.bg, color: m.color }">{{ m.badge }}</span>
            <div class="mi-text">
              <div class="mi-name">{{ m.label }}</div>
              <div class="mi-sub">{{ m.sub }}</div>
            </div>
          </div>
        </div>
      </el-card>

      <el-card v-if="mode === 'single'" style="margin-top:12px">
        <template #header>
          <div class="ph">
            <el-icon color="#f59e0b" :size="17"><Warning /></el-icon>
            <span>使用说明</span>
          </div>
        </template>
        <div class="tips">
          <div v-for="t in tips" :key="t.text" class="tip-row">
            <span class="tip-dot" :style="{ background: t.color }"></span>
            <span>{{ t.text }}</span>
          </div>
        </div>
      </el-card>

      <!-- History panel -->
      <el-card v-if="showHistory" style="margin-top:12px">
        <template #header>
          <div class="ph" style="justify-content:space-between;width:100%">
            <span>📋 推理历史记录（{{ history.length }}）</span>
            <el-button v-if="history.length" size="small" type="danger" text @click="clearHistory">清空</el-button>
          </div>
        </template>
        <div v-if="history.length" class="history-list">
          <div v-for="(h, idx) in history" :key="idx" class="history-row">
            <div class="hist-breed">{{ h.breed }}</div>
            <div class="hist-conf" :style="{ color: h.confidence >= 0.8 ? '#22c55e' : h.confidence >= 0.5 ? '#f59e0b' : '#ef4444' }">
              {{ (h.confidence * 100).toFixed(1) }}%
            </div>
            <div class="hist-file">{{ h.fileName }}</div>
            <div class="hist-time">{{ h.time }}</div>
          </div>
        </div>
        <el-empty v-else description="暂无历史记录" :image-size="40" />
      </el-card>
    </div>

    <!-- ===== 右栏 ===== -->
    <div class="right-col">

      <!-- 空状态 (只在单张模式下显示) -->
      <div v-if="mode === 'single' && !hasResult" class="empty-state standby-board">
        <div class="standby-hero">
          <div class="standby-copy">
            <div class="standby-kicker">
              <span class="pulse-dot"></span>
              {{ preview ? '图片已载入，等待开始推理' : '等待上传宠物图片' }}
            </div>
            <h2>{{ preview ? '准备进行双模型推理' : '上传后将自动生成分类与分割报告' }}</h2>
            <p>
              系统会同时调用 ResNet-34 分类器和 U-Net 分割网络，输出品种置信度、Top-5 候选、前景 Mask、叠加可视化和宠物区域占比。
            </p>
            <div class="standby-actions">
              <span class="action-chip">37 类猫狗品种</span>
              <span class="action-chip">像素级前景分割</span>
              <span class="action-chip">本地 FastAPI 推理</span>
            </div>
          </div>
          <div class="standby-preview">
            <img v-if="preview" :src="preview" class="standby-img" />
            <div v-else class="standby-placeholder">
              <div class="empty-emoji">🐾</div>
              <span>等待图片</span>
            </div>
          </div>
        </div>

        <div class="standby-output-grid">
          <div v-for="item in outputPreview" :key="item.title" class="output-card" :style="{ '--accent': item.color }">
            <div class="output-tag">{{ item.tag }}</div>
            <div>
              <div class="output-title">{{ item.title }}</div>
              <div class="output-desc">{{ item.desc }}</div>
            </div>
          </div>
        </div>

        <div class="standby-detail-grid">
          <div class="standby-panel">
            <div class="panel-title">推理流程</div>
            <div class="empty-flow">
              <div class="ef-step">
                <div class="ef-icon" style="background:rgba(99,102,241,.1);color:#6366f1">📸</div>
                <div class="ef-label">上传图片</div>
              </div>
              <div class="ef-arrow">→</div>
              <div class="ef-step">
                <div class="ef-icon" style="background:rgba(16,185,129,.1);color:#10b981">🧠</div>
                <div class="ef-label">双模型推理</div>
              </div>
              <div class="ef-arrow">→</div>
              <div class="ef-step">
                <div class="ef-icon" style="background:rgba(245,158,11,.1);color:#f59e0b">📊</div>
                <div class="ef-label">可视化结果</div>
              </div>
            </div>
            <div class="empty-tags">
              <el-tag type="info" effect="plain">ResNet-34 分类</el-tag>
              <el-tag type="info" effect="plain">U-Net 分割</el-tag>
              <el-tag type="info" effect="plain">Top-5 置信度</el-tag>
            </div>
          </div>

          <div class="standby-panel">
            <div class="panel-title">图片质量检查</div>
            <div class="quality-list">
              <div v-for="check in qualityChecks" :key="check" class="quality-row">
                <span class="check-dot">✓</span>
                <span>{{ check }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 有结果 (单张模式) -->
      <div v-if="mode === 'single' && hasResult">

        <!-- 品种 Banner -->
        <div class="breed-banner">
          <div>
            <div class="breed-label">识别品种</div>
            <div class="breed-name">{{ result.class_top1 }}</div>
          </div>
          <div class="banner-right">
            <div class="conf-pill"
              :style="{ background: confColor + '18', color: confColor, borderColor: confColor + '40' }">
              <div class="conf-pct-text">{{ confPct }}%</div>
              <div class="conf-sub-text">{{ confLabel }}</div>
            </div>
            <div class="latency-pill">⏱ {{ result.latency_ms }} ms</div>
            <button class="banner-action" :class="{ 'banner-action-ok': copySuccess }" @click="copyResult" :title="copySuccess ? $t('common.copied') : $t('common.copy') + ' JSON'">
              <el-icon :size="14"><component :is="copySuccess ? 'Check' : 'CopyDocument'" /></el-icon>
            </button>
            <button class="banner-action" @click="downloadResult" :title="$t('common.download')">
              <el-icon :size="14"><Download /></el-icon>
            </button>
            <button class="banner-action banner-action-feedback" @click="openFeedback" :title="$t('predict.feedback')">
              <el-icon :size="14"><Warning /></el-icon>
            </button>
          </div>
        </div>

        <el-row :gutter="14" style="margin-bottom:14px">
          <!-- Top-5 -->
          <el-col :span="15">
            <el-card style="height:100%">
              <template #header>
                <div class="ph">
                  <el-icon color="#6366f1" :size="16"><TrendCharts /></el-icon>
                  <span>Top-5 品种置信度</span>
                </div>
              </template>
              <div class="top5">
                <div v-for="(item, idx) in top5Visible" :key="idx" class="top5-row">
                  <span class="rank" :class="idx === 0 ? 'rank-top' : ''">{{ idx + 1 }}</span>
                  <span class="breed-name-sm">{{ item.label }}</span>
                  <div class="bar-track">
                    <div class="bar-fill"
                      :style="{
                        width: (item.confidence * 100).toFixed(1) + '%',
                        background: idx === 0 ? 'linear-gradient(90deg,#6366f1,#22d3ee)' : '#cbd5e1'
                      }">
                    </div>
                  </div>
                  <span class="pct-num" :style="{ color: idx === 0 ? '#6366f1' : '#94a3b8' }">
                    {{ (item.confidence * 100).toFixed(1) }}%
                  </span>
                </div>
                <!-- Top-1 极高时折叠提示 -->
                <div v-if="top5Collapsed" class="top5-collapsed-hint" @click="showAllTop5 = true">
                  <el-icon><ArrowDownBold /></el-icon>
                  <span>模型对此结果极度自信（≥99%），其余 4 个候选概率几乎为 0 — 点击展开</span>
                </div>
                <div v-else-if="result.class_confidence >= 0.99" class="top5-collapsed-hint subtle" @click="showAllTop5 = false">
                  <el-icon><ArrowUpBold /></el-icon>
                  <span>收起</span>
                </div>
              </div>
            </el-card>
          </el-col>

          <!-- 宠物区域占比 + 推理信息 -->
          <el-col :span="9">
            <el-card style="height:100%">
              <template #header>
                <div class="ph">
                  <el-icon color="#22d3ee" :size="16"><PictureFilled /></el-icon>
                  <span>宠物区域占比</span>
                </div>
              </template>
              <div class="area-wrap">
                <el-progress
                  type="circle"
                  :percentage="areaPct"
                  :width="110"
                  :stroke-width="8"
                  :color="[
                    { color: '#6366f1', percentage: 40 },
                    { color: '#22d3ee', percentage: 100 }
                  ]"
                />
                <div class="area-label">前景像素占全图比例</div>
                <div class="infer-stats">
                  <div class="infer-stat">
                    <div class="is-val" style="color:#f59e0b">{{ result.latency_ms }}</div>
                    <div class="is-lbl">延迟(ms)</div>
                  </div>
                  <div class="infer-sep"></div>
                  <div class="infer-stat">
                    <div class="is-val" style="color:#6366f1">37</div>
                    <div class="is-lbl">分类数</div>
                  </div>
                </div>
              </div>
            </el-card>
          </el-col>
        </el-row>

        <!-- 分割 + Grad-CAM 可视化 -->
        <el-card>
          <template #header>
            <div class="ph">
              <el-icon color="#6366f1" :size="16"><PictureFilled /></el-icon>
              <span>多维度可视化对比</span>
              <span style="margin-left:auto;display:inline-flex;align-items:center;gap:6px">
                <el-tag v-if="result.gradcam_url" type="danger" size="small" effect="plain">
                  <el-icon style="margin-right:3px"><Aim /></el-icon>含 Grad-CAM
                </el-tag>
                <el-tag v-else-if="gradcamLoading" type="warning" size="small" effect="plain">
                  <el-icon class="rotating-icon" style="margin-right:3px"><Loading /></el-icon>生成 Grad-CAM…
                </el-tag>
              </span>
            </div>
          </template>
          <div class="seg-grid" :class="{ 'four-col': result.gradcam_url }">
            <div class="seg-item">
              <img :src="preview" class="seg-img" />
              <div class="seg-cap">
                <span class="seg-dot" style="background:#64748b"></span>原图
              </div>
            </div>
            <div class="seg-item">
              <img :src="BACKEND + result.mask_url" class="seg-img" />
              <div class="seg-cap">
                <span class="seg-dot" style="background:#6366f1"></span>预测 Mask
              </div>
            </div>
            <div class="seg-item">
              <img :src="BACKEND + result.overlay_url" class="seg-img" />
              <div class="seg-cap">
                <span class="seg-dot" style="background:#22d3ee"></span>叠加可视化
              </div>
            </div>
            <div class="seg-item" v-if="result.gradcam_url">
              <img :src="BACKEND + result.gradcam_url" class="seg-img gradcam-highlight" />
              <div class="seg-cap">
                <span class="seg-dot" style="background:#ef4444"></span>Grad-CAM 热力图
              </div>
            </div>
          </div>
          <div class="vis-notes">
            <p>Mask 白色区域为宠物前景（置信度 > 0.5），叠加图以蓝绿色高亮前景区域</p>
            <p v-if="result.gradcam_url">热力图中<b style="color:#ef4444">暖色</b>为模型高关注区域（面部/耳朵/毛色），基于 ResNet-34 layer4 Grad-CAM 生成</p>
          </div>
        </el-card>

        <!-- WebSocket 实时日志面板 -->
        <el-card v-if="wsEnabled && wsLog.length" style="margin-top:14px">
          <template #header>
            <div class="ph" style="justify-content:space-between;width:100%">
              <span style="display:inline-flex;align-items:center;gap:8px">
                <el-icon color="#6366f1" :size="16"><Connection /></el-icon>
                {{ $t('predict.realtimeLog') }}
                <el-tag :type="wsState === 'done' ? 'success' : (wsState === 'error' ? 'danger' : 'info')" size="small" effect="plain">
                  {{ wsState }}
                </el-tag>
              </span>
              <el-button size="small" text @click="clearWsLog">{{ $t('common.clear') }}</el-button>
            </div>
          </template>
          <el-progress :percentage="wsProgress" :stroke-width="4"
            :status="wsState === 'done' ? 'success' : (wsState === 'error' ? 'exception' : '')" />
          <div class="ws-log">
            <div v-for="(line, i) in wsLog" :key="i" class="ws-line" :class="`ws-${line.level}`">
              <span class="ws-t">{{ line.t }}</span>
              <span class="ws-lvl">{{ line.level.toUpperCase() }}</span>
              <span class="ws-msg">{{ line.msg }}</span>
            </div>
          </div>
        </el-card>
      </div>

      <!-- ═══ Compare Mode UI ═══ -->
      <template v-if="mode === 'compare'">
        <!-- Hero 标题 -->
        <div class="cmp-hero">
          <div class="cmp-hero-text">
            <div class="cmp-hero-kicker">
              <span class="cmp-hero-dot"></span>
              MODEL COMPARISON · 同图三模型推理
            </div>
            <h2>{{ $t('predict.compareTitle') }}</h2>
            <p>{{ $t('predict.compareDesc') }}</p>
          </div>
          <div class="cmp-hero-stat">
            <div class="cmp-hero-stat-num">3</div>
            <div class="cmp-hero-stat-lbl">Models</div>
          </div>
        </div>

        <!-- 上传 + 运行按钮 -->
        <el-card class="cmp-upload-card">
          <div class="cmp-upload-row">
            <el-upload drag :auto-upload="false" :on-change="onCompareFile"
              :show-file-list="false" accept="image/*" class="uploader cmp-uploader">
              <div v-if="!comparePreview" class="upload-idle cmp-upload-idle">
                <el-icon :size="22" color="#7C3AED"><UploadFilled /></el-icon>
                <p class="upload-hint">拖拽 / 点击上传图片</p>
              </div>
              <div v-else class="cmp-upload-preview">
                <img :src="comparePreview" />
                <div class="cmp-upload-replace">
                  <el-icon :size="14"><RefreshRight /></el-icon>
                  <span>重新选择</span>
                </div>
              </div>
            </el-upload>
            <div class="cmp-upload-cta">
              <el-button type="primary" size="large" :loading="compareLoading"
                :disabled="!compareFile" @click="runCompare" class="cmp-run-btn">
                <el-icon v-if="!compareLoading" style="margin-right:6px"><VideoPlay /></el-icon>
                {{ compareLoading ? $t('predict.inferring') : $t('predict.compareRunInfer') }}
              </el-button>
              <div class="cmp-cta-tip">
                <el-icon :size="12"><InfoFilled /></el-icon>
                同时调用 ResNet-34（预训练）/ ResNet-34（随机初始化）/ SimpleCNN
              </div>
            </div>
          </div>
          <el-alert v-if="compareError" :title="compareError" type="error"
            show-icon :closable="false" style="margin-top:10px" />
        </el-card>

        <!-- 结果区 -->
        <div v-if="!compareResult" class="cmp-empty-row">
          <el-icon :size="32" color="#CBD5E1"><DataLine /></el-icon>
          <span>选择图片并点击「运行三模型对比」开始</span>
        </div>

        <div v-else class="cmp-results">
          <div v-for="m in compareResult.models" :key="m.key"
            class="cmp-card" :style="{ '--c': m.color }">

            <!-- 顶部色带 -->
            <div class="cmp-card-bar"></div>

            <!-- 模型身份 (上半区) -->
            <div class="cmp-card-head">
              <div class="cmp-card-rank" :title="m.short || m.name">
                {{ m.key === 'pretrained' ? 'PT' : (m.key === 'random_init' ? 'RI' : 'CNN') }}
              </div>
              <div class="cmp-card-id">
                <div class="cmp-card-name">{{ m.name }}</div>
                <div class="cmp-card-meta">
                  <span class="cmp-meta-pill">{{ m.init }}</span>
                  <span class="cmp-meta-dot">·</span>
                  <span>{{ m.params }} params</span>
                </div>
              </div>
              <div class="cmp-card-acc">
                <div class="cmp-card-acc-num">{{ (m.test_acc * 100).toFixed(1) }}<span>%</span></div>
                <div class="cmp-card-acc-lbl">Test Acc</div>
              </div>
            </div>

            <!-- 预测结果 (下半区) -->
            <div v-if="m.result.available" class="cmp-card-pred">
              <div class="cmp-pred-main">
                <div class="cmp-pred-lbl">本图预测</div>
                <div class="cmp-pred-breed">{{ m.result.top1 }}</div>
              </div>
              <div class="cmp-pred-conf-block">
                <div class="cmp-pred-conf-num">
                  {{ (m.result.confidence * 100).toFixed(1) }}<span>%</span>
                </div>
                <div class="cmp-pred-bar-wrap">
                  <div class="cmp-pred-bar" :style="{ width: (m.result.confidence * 100) + '%' }"></div>
                </div>
                <div class="cmp-pred-latency">⏱ {{ m.result.latency_ms }} ms</div>
              </div>
            </div>
            <div v-else class="cmp-card-unavailable">
              <el-icon :size="18"><CircleClose /></el-icon>
              <span>权重未加载</span>
            </div>
          </div>

          <!-- 对比观察 -->
          <div class="cmp-insight">
            <div class="cmp-insight-icon"><el-icon :size="14"><InfoFilled /></el-icon></div>
            <div class="cmp-insight-body">
              <div class="cmp-insight-title">对比观察</div>
              <div class="cmp-insight-text">
                预训练 ResNet-34 在本图置信度
                <b style="color:#2563EB">{{ (compareResult.models[0].result.confidence * 100).toFixed(1) }}%</b>，
                随机初始化版本仅约
                <b style="color:#94A3B8">{{ (compareResult.models[1].result.confidence * 100).toFixed(1) }}%</b>
                (≈ 1/37 均匀分布)，SimpleCNN
                <b style="color:#F59E0B">{{ (compareResult.models[2].result.confidence * 100).toFixed(1) }}%</b>
                介于两者之间 — 直观体现 <b>迁移学习 + 充足训练</b> 对细粒度分类的关键作用。
              </div>
            </div>
          </div>
        </div>
      </template>

      <!-- ═══ Batch Mode UI ═══ -->
      <template v-if="batchMode">

        <!-- 上传 + 控制区 (始终显示在批量主区顶部) -->
        <div class="batch-control">
          <div class="batch-control-upload"
            @drop.prevent="onBatchDrop"
            @dragover.prevent>
            <el-upload
              :auto-upload="false" :on-change="onBatchChange" :show-file-list="false"
              accept="image/*" multiple drag class="uploader batch-uploader"
            >
              <div class="batch-upload-idle">
                <div class="bui-icon">
                  <el-icon :size="22" color="#10B981"><UploadFilled /></el-icon>
                </div>
                <div class="bui-text">
                  <div class="bui-title">拖拽图片 / 文件夹 · 点击选择 · <kbd>Ctrl+V</kbd> 粘贴</div>
                  <div class="bui-sub">支持递归扫描子目录 · 最大 {{ BATCH_CONCURRENCY }} 路并发</div>
                </div>
                <div class="bui-counter" v-if="batchStats.total">
                  <span>{{ batchStats.total }}</span>
                  <small>张</small>
                </div>
              </div>
            </el-upload>
          </div>

          <div class="batch-control-actions">
            <el-button type="primary" size="large" :loading="batchRunning"
              :disabled="!batchStats.pending && !batchStats.failed"
              @click="runBatchInfer" class="batch-run-btn">
              <el-icon v-if="!batchRunning" style="margin-right:6px"><DataAnalysis /></el-icon>
              {{
                batchRunning
                  ? `推理中 ${batchStats.done + batchStats.failed}/${batchStats.total}`
                  : (batchStats.total === 0
                      ? '等待添加图片'
                      : (batchStats.failed
                          ? `重试失败 + 继续 (${batchStats.pending + batchStats.failed})`
                          : (batchStats.pending
                              ? `开始批量推理 (${batchStats.pending})`
                              : '✓ 全部完成')))
              }}
            </el-button>
            <el-button size="large" :disabled="!batchStats.total || batchRunning" @click="clearBatch">
              <el-icon style="margin-right:4px"><Delete /></el-icon>清空
            </el-button>
          </div>
        </div>

        <el-progress v-if="batchStats.total" :percentage="batchStats.progress"
          :status="batchRunning ? '' : (batchStats.failed ? 'warning' : (batchStats.done === batchStats.total ? 'success' : ''))"
          :stroke-width="6" style="margin: 4px 0 14px" />

        <!-- 空状态 (无任务) -->
        <div v-if="!batchStats.total" class="batch-empty">
          <div class="batch-empty-icon">
            <el-icon :size="42" color="#94a3b8"><Files /></el-icon>
          </div>
          <h3>批量推理工作台</h3>
          <p>从上方拖拽 / 选择图片，将并发执行分类 + 分割多任务推理。每张完成后可点击查看完整可视化结果。</p>
          <div class="batch-empty-features">
            <div class="bef-item"><span class="bef-num">1</span><span>支持任意数量图片，最大 {{ BATCH_CONCURRENCY }} 路并发</span></div>
            <div class="bef-item"><span class="bef-num">2</span><span>每张展示分类 + 分割 mask + 区域占比</span></div>
            <div class="bef-item"><span class="bef-num">3</span><span>失败可单张重试，结果可导出 CSV</span></div>
          </div>
        </div>

        <!-- 摘要栏 -->
        <div v-if="batchStats.total" class="batch-summary">
          <div class="bs-stat">
            <div class="bs-val">{{ batchStats.total }}</div>
            <div class="bs-lbl">总任务</div>
          </div>
          <div class="bs-sep"></div>
          <div class="bs-stat">
            <div class="bs-val" style="color:#22c55e">{{ batchStats.done }}</div>
            <div class="bs-lbl">已完成</div>
          </div>
          <div class="bs-stat">
            <div class="bs-val" style="color:#ef4444">{{ batchStats.failed }}</div>
            <div class="bs-lbl">失败</div>
          </div>
          <div class="bs-stat">
            <div class="bs-val" style="color:#6366f1">{{ batchStats.running }}</div>
            <div class="bs-lbl">推理中</div>
          </div>
          <div class="bs-sep"></div>
          <div class="bs-stat" v-if="batchStats.done">
            <div class="bs-val">{{ (batchStats.avgConf * 100).toFixed(1) }}%</div>
            <div class="bs-lbl">平均置信度</div>
          </div>
          <div class="bs-stat" v-if="batchStats.done">
            <div class="bs-val">{{ batchStats.cats }}<span class="bs-sub">猫</span> / {{ batchStats.dogs }}<span class="bs-sub">狗</span></div>
            <div class="bs-lbl">物种分布</div>
          </div>
          <div class="bs-stat" v-if="batchStats.done">
            <div class="bs-val">{{ Math.round(batchStats.totalTime / Math.max(batchStats.done, 1)) }}<span class="bs-sub">ms</span></div>
            <div class="bs-lbl">平均耗时</div>
          </div>
        </div>

        <!-- 工具栏 -->
        <div v-if="batchStats.total" class="batch-toolbar">
          <el-radio-group v-model="batchFilter" size="small">
            <el-radio-button value="all">全部 ({{ batchStats.total }})</el-radio-button>
            <el-radio-button value="cat" :disabled="!batchStats.cats">🐱 猫 ({{ batchStats.cats }})</el-radio-button>
            <el-radio-button value="dog" :disabled="!batchStats.dogs">🐶 狗 ({{ batchStats.dogs }})</el-radio-button>
            <el-radio-button value="low" :disabled="!batchStats.lowConf">⚠ 低置信 ({{ batchStats.lowConf }})</el-radio-button>
            <el-radio-button value="err" :disabled="!batchStats.failed">✕ 失败 ({{ batchStats.failed }})</el-radio-button>
          </el-radio-group>
          <el-select v-model="batchSort" size="small" style="width:150px">
            <el-option label="默认顺序" value="order" />
            <el-option label="置信度 ↓" value="conf-desc" />
            <el-option label="置信度 ↑" value="conf-asc" />
          </el-select>
          <div style="flex:1"></div>
          <el-button v-if="batchStats.failed" size="small" type="warning" plain @click="retryAllFailed" :disabled="batchRunning">
            <el-icon style="margin-right:4px"><RefreshRight /></el-icon>重试失败
          </el-button>
          <el-button v-if="batchStats.done" size="small" type="primary" plain @click="exportBatchCSV">
            <el-icon style="margin-right:4px"><Download /></el-icon>导出 CSV
          </el-button>
        </div>

        <!-- 任务卡片网格 -->
        <div v-if="batchStats.total" class="batch-grid">
          <div v-for="task in filteredTasks" :key="task.id"
            class="task-card" :class="`status-${task.status}`"
            @click="openDetail(task)">

            <!-- 缩略图 + 状态遮罩 -->
            <div class="tc-thumb-wrap">
              <img :src="task.preview" class="tc-thumb" />
              <div v-if="task.status === 'pending'" class="tc-overlay tc-pending">
                <el-icon :size="22"><Clock /></el-icon>
                <span>等待</span>
              </div>
              <div v-if="task.status === 'running'" class="tc-overlay tc-running">
                <el-icon :size="22" class="spin"><Loading /></el-icon>
                <span>推理中…</span>
              </div>
              <div v-if="task.status === 'error'" class="tc-overlay tc-error">
                <el-icon :size="22"><CircleClose /></el-icon>
                <span>失败</span>
              </div>
              <!-- 物种标识 -->
              <div v-if="task.status === 'done'" class="tc-species" :class="isCat(task.result.class_top1) ? 'cat' : 'dog'">
                {{ isCat(task.result.class_top1) ? '🐱' : '🐶' }}
              </div>
              <!-- 删除按钮 -->
              <button class="tc-remove" @click.stop="removeBatchTask(task.id)" title="移除">
                <el-icon :size="12"><Close /></el-icon>
              </button>
            </div>

            <!-- 信息区 -->
            <div class="tc-body">
              <div class="tc-name" :title="task.name">{{ task.name }}</div>

              <template v-if="task.status === 'done'">
                <div class="tc-breed">{{ task.result.class_top1 }}</div>
                <div class="tc-meta">
                  <div class="tc-conf">
                    <div class="tc-conf-bar" :style="{
                      width: (task.result.class_confidence * 100) + '%',
                      background: confColorOf(task.result.class_confidence)
                    }"></div>
                    <span class="tc-conf-val" :style="{ color: confColorOf(task.result.class_confidence) }">
                      {{ (task.result.class_confidence * 100).toFixed(1) }}%
                    </span>
                  </div>
                </div>
                <div class="tc-extras">
                  <span class="tc-extra" title="前景占比">
                    <el-icon :size="11"><PictureFilled /></el-icon>
                    {{ Math.round(task.result.pet_area_ratio * 100) }}%
                  </span>
                  <span class="tc-extra" title="推理耗时">
                    <el-icon :size="11"><Timer /></el-icon>
                    {{ task.result.latency_ms }}ms
                  </span>
                </div>
              </template>

              <template v-else-if="task.status === 'error'">
                <div class="tc-err">{{ task.error }}</div>
                <el-button size="small" type="warning" plain @click.stop="retryTask(task)" style="width:100%;margin-top:6px">
                  <el-icon style="margin-right:4px"><RefreshRight /></el-icon>重试
                </el-button>
              </template>

              <template v-else>
                <div class="tc-placeholder">{{ task.status === 'running' ? '正在双模型推理…' : '排队等待推理' }}</div>
              </template>
            </div>
          </div>
        </div>
      </template>
    </div>

    <!-- ═══ 批量结果详情 Dialog ═══ -->
    <el-dialog v-model="batchDetail.visible" :title="batchDetail.task?.name" width="900px" top="6vh">
      <template v-if="batchDetail.task?.result">
        <div class="bd-banner">
          <div>
            <div class="bd-kicker">{{ isCat(batchDetail.task.result.class_top1) ? '🐱 猫科' : '🐶 犬科' }}</div>
            <div class="bd-breed">{{ batchDetail.task.result.class_top1 }}</div>
          </div>
          <div class="bd-pills">
            <div class="bd-pill" :style="{
              background: confColorOf(batchDetail.task.result.class_confidence) + '20',
              color: confColorOf(batchDetail.task.result.class_confidence),
              borderColor: confColorOf(batchDetail.task.result.class_confidence) + '50'
            }">
              <strong>{{ (batchDetail.task.result.class_confidence * 100).toFixed(1) }}%</strong>
              <span>置信度</span>
            </div>
            <div class="bd-pill bd-pill-neutral">
              <strong>{{ Math.round(batchDetail.task.result.pet_area_ratio * 100) }}%</strong>
              <span>前景占比</span>
            </div>
            <div class="bd-pill bd-pill-neutral">
              <strong>{{ batchDetail.task.result.latency_ms }}ms</strong>
              <span>耗时</span>
            </div>
          </div>
        </div>

        <el-row :gutter="14" style="margin-top:14px">
          <el-col :span="12">
            <div class="bd-section-title">Top-5 候选</div>
            <div class="top5">
              <div v-for="(it, i) in batchDetail.task.result.top5" :key="i" class="top5-row">
                <span class="rank" :class="i === 0 ? 'rank-top' : ''">{{ i + 1 }}</span>
                <span class="breed-name-sm">{{ it.label }}</span>
                <div class="bar-track">
                  <div class="bar-fill" :style="{
                    width: (it.confidence * 100) + '%',
                    background: i === 0 ? 'linear-gradient(90deg,#6366f1,#22d3ee)' : '#cbd5e1'
                  }"></div>
                </div>
                <span class="pct-num" :style="{ color: i === 0 ? '#6366f1' : '#94a3b8' }">
                  {{ (it.confidence * 100).toFixed(1) }}%
                </span>
              </div>
            </div>
          </el-col>
          <el-col :span="12">
            <div class="bd-section-title">分割可视化</div>
            <div class="bd-seg-grid">
              <div class="seg-item">
                <img :src="batchDetail.task.preview" class="seg-img" />
                <div class="seg-cap"><span class="seg-dot" style="background:#64748b"></span>原图</div>
              </div>
              <div class="seg-item">
                <img :src="BACKEND + batchDetail.task.result.mask_url" class="seg-img" />
                <div class="seg-cap"><span class="seg-dot" style="background:#6366f1"></span>Mask</div>
              </div>
              <div class="seg-item">
                <img :src="BACKEND + batchDetail.task.result.overlay_url" class="seg-img" />
                <div class="seg-cap"><span class="seg-dot" style="background:#22d3ee"></span>叠加</div>
              </div>
            </div>
          </el-col>
        </el-row>
      </template>
    </el-dialog>

    <!-- ═══ Camera Dialog ═══ -->
    <el-dialog v-model="cameraVisible" :before-close="closeCamera" :show-close="true"
      width="640px" top="8vh" align-center class="camera-dialog">
      <template #header>
        <div class="cam-dialog-header">
          <div class="cam-dialog-title">
            <el-icon :size="18" color="#10B981"><VideoCamera /></el-icon>
            实时摄像头识别
          </div>
          <div class="cam-dialog-sub">
            将宠物对准摄像头中央，点击「拍摄并识别」立即调用 ResNet-34 + U-Net 多任务推理
          </div>
        </div>
      </template>

      <div class="cam-stage">
        <video ref="cameraVideoEl" class="cam-video" playsinline muted />
        <div v-if="!cameraReady && !cameraError" class="cam-overlay cam-loading">
          <el-icon :size="32" class="rotating-icon"><Loading /></el-icon>
          <span>正在启动摄像头…</span>
        </div>
        <div v-if="cameraError" class="cam-overlay cam-error">
          <el-icon :size="32"><CircleClose /></el-icon>
          <span>{{ cameraError }}</span>
          <small>请检查浏览器摄像头权限是否已允许</small>
        </div>
        <div v-if="cameraReady" class="cam-frame">
          <div class="cam-corner cam-corner-tl"></div>
          <div class="cam-corner cam-corner-tr"></div>
          <div class="cam-corner cam-corner-bl"></div>
          <div class="cam-corner cam-corner-br"></div>
          <div class="cam-live">
            <span class="cam-live-dot"></span>LIVE
          </div>
        </div>
      </div>

      <template #footer>
        <div class="cam-actions">
          <el-button @click="closeCamera" size="default">取消</el-button>
          <el-button type="primary" size="default" :disabled="!cameraReady"
            @click="captureCamera" class="cam-shoot-btn">
            <el-icon style="margin-right:6px"><Aim /></el-icon>
            拍摄并识别
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- ═══ Feedback Dialog ═══ -->
    <el-dialog v-model="feedbackVisible" :title="$t('feedback.title')" width="500px" top="15vh">
      <div v-if="!feedbackDone" class="fb-form">
        <div class="fb-row">
          <span class="fb-lbl">{{ $t('feedback.predictedAs') }}</span>
          <span class="fb-pred">
            {{ result?.class_top1 }}
            <span class="fb-conf">{{ result ? (result.class_confidence * 100).toFixed(1) : 0 }}%</span>
          </span>
        </div>
        <div class="fb-row fb-row-block">
          <span class="fb-lbl">{{ $t('feedback.correctBreed') }} *</span>
          <el-select v-model="feedbackForm.correctBreed" filterable
            :placeholder="$t('feedback.selectBreed')" style="width:100%">
            <el-option v-for="b in ALL_BREEDS" :key="b" :label="b" :value="b" />
          </el-select>
        </div>
        <div class="fb-row fb-row-block">
          <span class="fb-lbl">{{ $t('feedback.note') }}</span>
          <el-input v-model="feedbackForm.note" type="textarea" :rows="2"
            :placeholder="$t('feedback.notePlaceholder')" maxlength="500" show-word-limit />
        </div>
      </div>
      <div v-else class="fb-success">
        <el-icon :size="40" color="#16A34A"><CircleCheck /></el-icon>
        <p>{{ $t('predict.feedbackThanks') }}</p>
      </div>
      <template #footer v-if="!feedbackDone">
        <el-button @click="feedbackVisible = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="feedbackSubmitting"
          :disabled="!feedbackForm.correctBreed" @click="sendFeedback">
          {{ $t('common.submit') }}
        </el-button>
      </template>
    </el-dialog>
  </div><!-- /.predict-layout -->
  </div><!-- /.predict-page -->
</template>

<style scoped>
/* ═══ Layout ═══ */
.predict-page { display: flex; flex-direction: column; gap: 14px; }

.predict-layout {
  display: grid; gap: 18px; align-items: start;
}
.predict-layout.layout-single  { grid-template-columns: 330px 1fr; }
.predict-layout.layout-batch   { grid-template-columns: 1fr; }
.predict-layout.layout-compare { grid-template-columns: 1fr; }

@media (max-width: 900px) {
  .predict-layout.layout-single { grid-template-columns: 1fr; }
}

/* ═══ Top Mode Bar (segmented tabs) ═══ */
.predict-modebar {
  display: flex; align-items: center; gap: 12px;
  background: var(--c-card, #FFFFFF);
  border: 1px solid var(--c-border, #E2E8F0);
  border-radius: var(--radius-lg, 14px);
  padding: 6px; box-shadow: 0 1px 2px rgba(15,23,42,.03);
}
.mb-tabs {
  flex: 1; display: grid; grid-template-columns: repeat(3, 1fr); gap: 4px;
}
.mb-tab {
  position: relative; cursor: pointer; user-select: none;
  display: flex; align-items: center; gap: 11px;
  padding: 9px 14px; border-radius: 10px;
  background: transparent; border: 0; text-align: left;
  transition: all .25s cubic-bezier(.33,1,.68,1);
}
.mb-tab:hover:not(.active) { background: rgba(15,23,42,.025); }
.mb-tab-icon {
  flex-shrink: 0; width: 32px; height: 32px; border-radius: 9px;
  display: flex; align-items: center; justify-content: center;
  background: color-mix(in srgb, var(--tc) 10%, white);
  color: var(--tc);
  transition: all .25s ease;
}
.mb-tab-text { min-width: 0; line-height: 1.3; }
.mb-tab-label {
  font-size: 13.5px; font-weight: 700; color: var(--c-dark, #0F172A);
  white-space: nowrap;
}
.mb-tab-desc {
  font-size: 11px; font-weight: 500; color: var(--c-muted, #94A3B8);
  margin-top: 1px; white-space: nowrap;
}
.mb-tab.active {
  background: linear-gradient(135deg, color-mix(in srgb, var(--tc) 8%, white), color-mix(in srgb, var(--tc) 4%, white));
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--tc) 25%, white) inset, 0 4px 12px color-mix(in srgb, var(--tc) 14%, transparent);
}
.mb-tab.active .mb-tab-icon {
  background: var(--tc); color: #fff;
  box-shadow: 0 4px 14px color-mix(in srgb, var(--tc) 35%, transparent);
}
.mb-tab.active .mb-tab-label { color: var(--tc); }

.mb-history {
  flex-shrink: 0; cursor: pointer;
  display: inline-flex; align-items: center; gap: 6px;
  padding: 8px 14px; border-radius: 10px;
  background: transparent; border: 1px solid var(--c-border, #E2E8F0);
  font-size: 12.5px; font-weight: 600; color: var(--c-text-body, #334155);
  transition: all .2s ease;
}
.mb-history:hover { border-color: var(--c-primary, #2563EB); color: var(--c-primary, #2563EB); }
.mb-history.active { background: rgba(37,99,235,.06); border-color: rgba(37,99,235,.3); color: #2563EB; }
.mb-history-count {
  display: inline-flex; align-items: center; justify-content: center;
  min-width: 18px; height: 18px; padding: 0 5px; border-radius: 100px;
  background: #EF4444; color: #fff; font-size: 10px; font-weight: 800;
}

@media (max-width: 900px) {
  .mb-tab-desc { display: none; }
  .mb-tab { padding: 9px 10px; }
  .mb-history span:not(.mb-history-count) { display: none; }
}

.ph { display: flex; align-items: center; gap: 8px; font-weight: 800; font-size: 14px; }
.rotating-icon { animation: spin-icon .9s linear infinite; }
@keyframes spin-icon { to { transform: rotate(360deg); } }

/* ═══ Upload — Clean Style ═══ */
.uploader :deep(.el-upload-dragger) {
  border: 2px dashed #CBD5E1; border-radius: var(--radius, 12px);
  background: #FAFBFC;
  transition: all .2s ease; padding: 0; height: auto;
}
.uploader :deep(.el-upload-dragger:hover) {
  border-color: var(--c-primary-soft, #3B82F6);
  background: #F0F4FF;
}
.upload-idle { padding: 32px 20px; display: flex; flex-direction: column; align-items: center; gap: 8px; }
.upload-icon-ring {
  width: 56px; height: 56px; border-radius: 50%;
  background: #EFF6FF;
  border: 2px solid #BFDBFE;
  display: flex; align-items: center; justify-content: center; margin-bottom: 4px;
}
.upload-hint { margin: 0; font-size: 13.5px; color: #64748B; }
.upload-hint em { color: var(--c-primary, #1E40AF); font-style: normal; font-weight: 700; }
.upload-sub  { margin: 0; font-size: 11px; color: #94A3B8; letter-spacing: .3px; text-align: center; }
/* ─── Sample Library ─── */
.sample-section { margin-top: 14px; padding-top: 12px; border-top: 1px dashed var(--c-border, #E2E8F0); }
.sample-title {
  display: flex; align-items: center; gap: 6px;
  font-size: 11px; font-weight: 600; color: var(--c-muted, #64748B);
  margin-bottom: 8px;
}
.sample-grid {
  display: grid; grid-template-columns: repeat(6, 1fr); gap: 6px;
}
.sample-thumb {
  position: relative; border: 1px solid var(--c-border, #E2E8F0);
  border-radius: 8px; overflow: hidden; cursor: pointer; padding: 0;
  background: transparent; aspect-ratio: 1;
  transition: all .2s ease;
}
.sample-thumb img { width: 100%; height: 100%; object-fit: cover; display: block; }
.sample-thumb:hover {
  transform: translateY(-2px) scale(1.06);
  box-shadow: var(--shadow-md);
  border-color: var(--c-primary, #2563EB);
  z-index: 2;
}
.sample-badge {
  position: absolute; top: 2px; right: 2px;
  width: 16px; height: 16px; border-radius: 50%;
  background: rgba(255,255,255,.9); backdrop-filter: blur(4px);
  font-size: 10px; line-height: 1;
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 1px 3px rgba(0,0,0,.15);
}

.preview-box { position: relative; overflow: hidden; border-radius: 12px; }
.preview-img { width: 100%; max-height: 240px; object-fit: cover; display: block; }
.preview-overlay {
  position: absolute; inset: 0; background: rgba(15,23,42,.45);
  backdrop-filter: blur(2px);
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 6px; color: #fff; font-size: 12px; opacity: 0; transition: opacity .25s;
}
.preview-box:hover .preview-overlay { opacity: 1; }

/* Model info */
.model-info-list { display: flex; flex-direction: column; gap: 9px; }
.model-info-row  { display: flex; align-items: center; gap: 10px; transition: all .2s ease; padding: 2px 0; }
.model-info-row:hover { transform: translateX(3px); }
.mi-badge { padding: 4px 10px; border-radius: 8px; font-size: 10.5px; font-weight: 800; }
.mi-name  { font-size: 13px; font-weight: 700; color: var(--c-dark, #0F172A); }
.mi-sub   { font-size: 10.5px; color: #94a3b8; }

/* Tips */
.tips { display: flex; flex-direction: column; gap: 9px; }
.tip-row { display: flex; align-items: flex-start; gap: 9px; font-size: 12.5px; color: var(--c-text-body, #334155); line-height: 1.6; }
.tip-dot {
  width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; margin-top: 5px;
  box-shadow: 0 0 6px currentColor;
}

/* ═══ Standby — Clean ═══ */
.empty-state {
  background: var(--c-card, #FFFFFF);
  border-radius: var(--radius, 12px);
  border: 1px solid var(--c-border, #E2E8F0);
  box-shadow: var(--shadow); padding: 22px;
  position: relative; overflow: hidden;
}
.standby-board {
  min-height: auto;
  background: var(--c-card, #FFFFFF);
}
.standby-hero {
  display: grid; grid-template-columns: minmax(0, 1fr) 210px;
  gap: 16px; align-items: stretch; padding: 18px;
  border: 1px solid var(--c-border, #E2E8F0); border-radius: var(--radius, 12px);
  background: #F8FAFC;
}
.standby-copy { display: flex; flex-direction: column; justify-content: center; min-width: 0; }
.standby-kicker {
  display: inline-flex; align-items: center; gap: 7px; align-self: flex-start;
  padding: 5px 12px; border-radius: 999px;
  background: #EFF6FF;
  border: 1px solid #BFDBFE;
  color: var(--c-primary, #1E40AF);
  font-size: 11px; font-weight: 700; margin-bottom: 12px;
}
.pulse-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: #22C55E;
  box-shadow: 0 0 6px rgba(34,197,94,.3);
  animation: pulse 2s infinite;
}
.standby-copy h2 { margin: 0 0 6px; color: var(--c-dark, #0F172A); font-size: 19px; line-height: 1.25; font-weight: 800; }
.standby-copy p { margin: 0; max-width: 600px; color: var(--c-muted, #64748B); font-size: 13px; line-height: 1.8; }
.standby-actions { display: flex; flex-wrap: wrap; gap: 7px; margin-top: 16px; }
.action-chip {
  padding: 5px 10px; border-radius: 8px;
  background: rgba(255,255,255,.8); border: 1px solid rgba(99,102,241,.1);
  color: var(--c-text-body, #334155); font-size: 11px; font-weight: 700;
  transition: all .2s ease;
}
.action-chip:hover { border-color: rgba(99,102,241,.2); transform: translateY(-1px); }
.standby-preview {
  min-height: 150px; border-radius: 13px; border: 2px dashed rgba(99,102,241,.15);
  background: linear-gradient(135deg, rgba(255,255,255,.5), rgba(238,242,255,.3));
  overflow: hidden; display: flex; align-items: center; justify-content: center;
  transition: all .25s ease;
}
.standby-preview:hover { border-color: rgba(99,102,241,.25); }
.standby-img { width: 100%; height: 100%; min-height: 150px; object-fit: cover; display: block; }
.standby-placeholder { display: flex; flex-direction: column; align-items: center; gap: 8px; color: #94a3b8; font-weight: 700; }
.empty-emoji { font-size: 48px; line-height: 1; animation: float 5s ease-in-out infinite; }

/* Output preview grid */
.standby-output-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; margin-top: 12px; }
.output-card {
  position: relative; overflow: hidden; display: flex; gap: 11px; align-items: flex-start;
  padding: 14px; border-radius: 12px;
  border: 1px solid rgba(99,102,241,.06);
  background: rgba(255,255,255,.8); backdrop-filter: blur(8px);
  transition: all .25s ease;
}
.output-card:hover {
  border-color: rgba(99,102,241,.15);
  box-shadow: 0 6px 20px rgba(99,102,241,.08);
  transform: translateY(-2px);
}
.output-card::before {
  content: "";
  position: absolute; inset: 0 auto 0 0; width: 3px;
  background: var(--accent);
}
.output-tag {
  min-width: 40px; height: 28px; border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  background: color-mix(in srgb, var(--accent) 10%, white); color: var(--accent);
  font-size: 10px; font-weight: 900;
}
.output-title { color: #1e293b; font-size: 13px; font-weight: 800; margin-bottom: 4px; }
.output-desc  { color: #64748b; font-size: 11px; line-height: 1.55; }

/* Detail grid */
.standby-detail-grid { display: grid; grid-template-columns: 1.15fr .85fr; gap: 10px; margin-top: 12px; }
.standby-panel {
  padding: 15px; border-radius: 12px;
  border: 1px solid rgba(99,102,241,.06);
  background: rgba(255,255,255,.8); backdrop-filter: blur(8px);
}
.panel-title { color: #1e293b; font-size: 13.5px; font-weight: 800; margin-bottom: 12px; }
.empty-flow  { display: flex; align-items: center; justify-content: flex-start; gap: 8px; margin-bottom: 14px; }
.ef-step { display: flex; flex-direction: column; align-items: center; gap: 5px; }
.ef-icon {
  width: 48px; height: 48px; border-radius: 12px;
  display: flex; align-items: center; justify-content: center; font-size: 22px;
  box-shadow: 0 2px 8px rgba(0,0,0,.06);
}
.ef-label { font-size: 11px; color: var(--c-muted, #64748B); font-weight: 600; }
.ef-arrow {
  font-size: 16px; padding: 0 3px;
  color: #CBD5E1;
}
.empty-tags { display: flex; justify-content: flex-start; gap: 6px; flex-wrap: wrap; }
.quality-list { display: grid; gap: 9px; }
.quality-row { display: flex; align-items: flex-start; gap: 8px; color: var(--c-text-body, #334155); font-size: 12px; line-height: 1.6; }
.check-dot {
  width: 18px; height: 18px; border-radius: 50%;
  display: inline-flex; align-items: center; justify-content: center; flex-shrink: 0;
  background: linear-gradient(135deg, rgba(34,197,94,.12), rgba(16,185,129,.08));
  color: #16a34a; font-size: 10px; font-weight: 900;
  box-shadow: 0 0 8px rgba(34,197,94,.1);
}

/* (legacy .mode-bar replaced by .predict-modebar above) */

/* ═══ Batch — Workbench ═══ */
.batch-actions { display: flex; gap: 8px; margin-top: 12px; }
.batch-drop-zone { position: relative; }
.upload-hint kbd {
  display: inline-block; padding: 1px 5px; margin: 0 2px;
  background: #F1F5F9; border: 1px solid #CBD5E1; border-bottom-width: 2px;
  border-radius: 4px; font-size: 10px; font-family: 'Fira Code', monospace;
  color: #475569; vertical-align: middle;
}

/* ═══ Batch Control Bar ═══ */
.batch-control {
  display: grid; grid-template-columns: 1fr auto; gap: 12px; align-items: stretch;
  margin-bottom: 4px;
}
.batch-control-upload :deep(.el-upload),
.batch-control-upload :deep(.el-upload-dragger) {
  width: 100%; height: 100%; padding: 0;
}
.batch-control-upload :deep(.el-upload-dragger) {
  border: 2px dashed rgba(16,185,129,.32);
  border-radius: var(--radius, 12px);
  background: linear-gradient(135deg, rgba(16,185,129,.04), rgba(34,197,94,.02));
  transition: all .25s ease;
  display: flex; align-items: center; justify-content: stretch;
}
.batch-control-upload :deep(.el-upload-dragger:hover) {
  border-color: #10B981;
  background: rgba(16,185,129,.06);
}
.batch-upload-idle {
  display: flex; align-items: center; gap: 14px; padding: 14px 18px; width: 100%;
  text-align: left;
}
.bui-icon {
  width: 44px; height: 44px; flex-shrink: 0; border-radius: 11px;
  background: linear-gradient(135deg, rgba(16,185,129,.16), rgba(34,197,94,.08));
  border: 1px solid rgba(16,185,129,.22);
  display: flex; align-items: center; justify-content: center;
}
.bui-text { flex: 1; min-width: 0; }
.bui-title {
  font-size: 13.5px; font-weight: 700; color: var(--c-dark, #0F172A);
  line-height: 1.3;
}
.bui-title kbd {
  display: inline-block; padding: 1px 5px; margin: 0 2px;
  background: #F1F5F9; border: 1px solid #CBD5E1; border-bottom-width: 2px;
  border-radius: 4px; font-size: 10.5px; font-family: 'Fira Code', monospace;
  color: #475569;
}
.bui-sub {
  font-size: 11.5px; color: var(--c-muted, #64748B);
  margin-top: 3px; line-height: 1.4;
}
.bui-counter {
  flex-shrink: 0; display: flex; align-items: baseline; gap: 3px;
  padding: 4px 12px; border-radius: 100px;
  background: linear-gradient(135deg, #10B981 0%, #059669 100%);
  color: #fff;
  box-shadow: 0 4px 12px rgba(16,185,129,.3);
}
.bui-counter span { font-size: 18px; font-weight: 800; font-family: 'Fira Code', monospace; line-height: 1; }
.bui-counter small { font-size: 10px; font-weight: 700; opacity: .9; }

.batch-control-actions {
  display: flex; gap: 8px; align-items: stretch;
}
.batch-run-btn {
  height: auto !important; min-height: 76px;
  font-weight: 700 !important; font-size: 13.5px !important;
  padding: 0 22px !important;
  background: linear-gradient(135deg, #10B981 0%, #059669 100%) !important;
  border: 0 !important;
  box-shadow: 0 4px 14px rgba(16,185,129,.28) !important;
}
.batch-run-btn:hover:not(:disabled) {
  box-shadow: 0 8px 22px rgba(16,185,129,.4) !important;
  transform: translateY(-1px);
}
.batch-run-btn:disabled {
  background: #CBD5E1 !important;
  box-shadow: none !important;
}
.batch-control-actions > .el-button:not(.batch-run-btn) {
  height: auto !important; min-height: 76px;
}

@media (max-width: 900px) {
  .batch-control { grid-template-columns: 1fr; }
  .batch-run-btn, .batch-control-actions > .el-button { min-height: 48px !important; }
}

/* Empty state */
.batch-empty {
  background: var(--c-card, #FFFFFF);
  border: 2px dashed var(--c-border, #E2E8F0);
  border-radius: var(--radius, 12px);
  padding: 60px 32px; text-align: center;
}
.batch-empty-icon {
  width: 80px; height: 80px; border-radius: 50%;
  background: #F1F5F9; display: flex; align-items: center; justify-content: center;
  margin: 0 auto 16px;
}
.batch-empty h3 { font-size: 18px; font-weight: 800; color: var(--c-dark, #0F172A); margin: 0 0 8px; }
.batch-empty p { font-size: 13px; color: var(--c-muted, #64748B); line-height: 1.7; max-width: 480px; margin: 0 auto 20px; }
.batch-empty-features { display: flex; flex-direction: column; gap: 8px; max-width: 380px; margin: 0 auto; text-align: left; }
.bef-item {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 14px; border-radius: 10px;
  background: #F8FAFC; border: 1px solid var(--c-border, #E2E8F0);
  font-size: 12.5px; color: var(--c-text-body, #334155);
}
.bef-num {
  width: 22px; height: 22px; border-radius: 50%;
  background: var(--c-primary, #1E40AF); color: #fff;
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 800; flex-shrink: 0;
}

/* Summary */
.batch-summary {
  display: flex; align-items: center; gap: 18px;
  background: linear-gradient(135deg, #0F172A, #1E293B);
  border-radius: var(--radius, 12px);
  padding: 16px 22px; margin-bottom: 12px;
  box-shadow: var(--shadow);
}
.bs-stat { text-align: center; min-width: 72px; }
.bs-val {
  font-size: 22px; font-weight: 800; color: #F1F5F9;
  font-family: 'Fira Code', monospace; line-height: 1.1;
}
.bs-sub { font-size: 11px; color: #94A3B8; font-weight: 600; margin: 0 2px; }
.bs-lbl { font-size: 10.5px; color: #94A3B8; margin-top: 4px; letter-spacing: .3px; font-weight: 600; }
.bs-sep { width: 1px; height: 32px; background: rgba(148,163,184,.2); }

/* Toolbar */
.batch-toolbar {
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
  background: #F8FAFC; padding: 10px 14px;
  border-radius: var(--radius, 12px);
  border: 1px solid var(--c-border, #E2E8F0);
  margin-bottom: 14px;
}

/* Task grid */
.batch-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
}
.task-card {
  position: relative; overflow: hidden;
  border-radius: var(--radius, 12px);
  border: 1px solid var(--c-border, #E2E8F0);
  background: var(--c-card, #FFFFFF);
  box-shadow: var(--shadow-xs);
  transition: all .2s ease;
  cursor: pointer;
}
.task-card.status-done:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
  border-color: #6366F1;
}
.task-card.status-pending { opacity: .7; }
.task-card.status-running { border-color: #6366F1; box-shadow: 0 0 0 2px rgba(99,102,241,.12); }
.task-card.status-error { border-color: #FCA5A5; }
.task-card.status-error, .task-card.status-pending, .task-card.status-running { cursor: default; }

.tc-thumb-wrap { position: relative; aspect-ratio: 4/3; overflow: hidden; background: #F1F5F9; }
.tc-thumb { width: 100%; height: 100%; object-fit: cover; display: block; }
.tc-overlay {
  position: absolute; inset: 0;
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px;
  font-size: 12px; font-weight: 700; backdrop-filter: blur(4px);
}
.tc-pending { background: rgba(148,163,184,.55); color: #fff; }
.tc-running { background: rgba(99,102,241,.55); color: #fff; }
.tc-error   { background: rgba(239,68,68,.55); color: #fff; }
.spin { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.tc-species {
  position: absolute; top: 8px; left: 8px;
  width: 26px; height: 26px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 14px; line-height: 1;
  background: rgba(255,255,255,.95); backdrop-filter: blur(8px);
  box-shadow: 0 2px 8px rgba(0,0,0,.15);
}
.tc-remove {
  position: absolute; top: 6px; right: 6px;
  width: 22px; height: 22px; border-radius: 50%;
  background: rgba(15,23,42,.55); border: 0;
  color: #fff; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  opacity: 0; transition: all .2s ease;
}
.task-card:hover .tc-remove { opacity: 1; }
.tc-remove:hover { background: #EF4444; }

.tc-body { padding: 10px 12px 12px; }
.tc-name {
  font-size: 11px; color: var(--c-muted, #64748B);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  margin-bottom: 4px;
}
.tc-breed {
  font-size: 14px; font-weight: 800; color: var(--c-dark, #0F172A);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  margin-bottom: 8px;
}
.tc-conf {
  position: relative; height: 22px;
  background: #F1F5F9; border-radius: 6px; overflow: hidden;
  display: flex; align-items: center;
}
.tc-conf-bar {
  position: absolute; left: 0; top: 0; bottom: 0;
  opacity: .25; transition: width .4s var(--ease, ease);
}
.tc-conf-val {
  position: relative; font-size: 12px; font-weight: 800;
  font-family: 'Fira Code', monospace;
  padding: 0 8px; z-index: 1;
}
.tc-extras { display: flex; gap: 10px; margin-top: 8px; }
.tc-extra {
  display: inline-flex; align-items: center; gap: 4px;
  font-size: 10.5px; color: var(--c-muted, #64748B); font-weight: 600;
  font-family: 'Fira Code', monospace;
}
.tc-err { font-size: 12px; color: var(--c-red, #DC2626); padding: 8px 0 4px; line-height: 1.5; }
.tc-placeholder {
  font-size: 12px; color: var(--c-muted, #64748B);
  padding: 14px 0; text-align: center; font-style: italic;
}

/* Detail Dialog */
.bd-banner {
  display: flex; justify-content: space-between; align-items: center;
  background: linear-gradient(135deg, #0F172A, #1E293B);
  padding: 18px 22px; border-radius: var(--radius, 12px);
  color: #F1F5F9;
}
.bd-kicker { font-size: 11px; color: #94A3B8; letter-spacing: .4px; text-transform: uppercase; font-weight: 700; margin-bottom: 4px; }
.bd-breed { font-size: 22px; font-weight: 800; letter-spacing: -.02em; }
.bd-pills { display: flex; gap: 8px; }
.bd-pill {
  border: 1px solid; border-radius: 10px; padding: 8px 14px;
  display: flex; flex-direction: column; align-items: center; line-height: 1.2;
}
.bd-pill strong { font-size: 16px; font-weight: 800; font-family: 'Fira Code', monospace; }
.bd-pill span { font-size: 10px; opacity: .8; margin-top: 2px; font-weight: 600; }
.bd-pill-neutral { background: rgba(255,255,255,.08); border-color: rgba(255,255,255,.15); color: #CBD5E1; }
.bd-section-title { font-size: 13px; font-weight: 800; color: var(--c-dark, #0F172A); margin-bottom: 10px; }
.bd-seg-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.bd-seg-grid .seg-img { aspect-ratio: 1; }

/* ═══ History ═══ */
.history-list { display: flex; flex-direction: column; gap: 4px; max-height: 260px; overflow-y: auto; }
.history-row {
  display: grid; grid-template-columns: 1fr 50px 1fr 90px; gap: 6px; align-items: center;
  padding: 7px 8px; border-radius: var(--radius-sm, 8px); font-size: 12px;
  border-bottom: 1px solid var(--c-border, #E2E8F0);
}
.history-row:last-child { border-bottom: 0; }
.hist-breed { font-weight: 700; color: var(--c-dark, #0F172A); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.hist-conf { font-weight: 800; font-family: 'Fira Code', monospace; text-align: center; }
.hist-file { color: var(--c-muted, #64748B); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.hist-time { color: var(--c-muted, #64748B); font-size: 11px; text-align: right; }

/* ═══ Result Banner — Professional Dark ═══ */
.breed-banner {
  position: relative; overflow: hidden;
  background: #0F172A;
  border-radius: var(--radius, 12px); padding: 20px 24px;
  display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px;
}
.breed-banner::before { display: none; }
.breed-label { font-size: 11px; color: #64748B; margin-bottom: 4px; letter-spacing: .6px; text-transform: uppercase; font-weight: 700; }
.breed-name {
  font-size: 22px; font-weight: 800; letter-spacing: -.02em;
  color: #F1F5F9;
}
.banner-right { display: flex; align-items: center; gap: 10px; position: relative; z-index: 1; }
.conf-pill {
  padding: 8px 16px; border-radius: 100px; border: 1px solid;
  display: flex; flex-direction: column; align-items: center; line-height: 1.2;
}
.conf-pct-text { font-size: 20px; font-weight: 800; font-family: 'Fira Code', monospace; }
.conf-sub-text { font-size: 10.5px; font-weight: 600; opacity: .85; }
.banner-action {
  width: 32px; height: 32px; border-radius: 8px;
  border: 1px solid rgba(255,255,255,.12);
  background: rgba(255,255,255,.04); color: #CBD5E1;
  cursor: pointer; transition: all .2s ease;
  display: flex; align-items: center; justify-content: center;
}
.banner-action:hover { background: rgba(255,255,255,.1); color: #F1F5F9; transform: translateY(-1px); }
.banner-action-ok { background: rgba(34,197,94,.2) !important; color: #4ADE80 !important; border-color: rgba(34,197,94,.4) !important; }
.latency-pill {
  background: rgba(255,255,255,.06); border: 1px solid rgba(255,255,255,.1);
  color: #94A3B8; font-size: 11px; font-weight: 600; padding: 5px 11px; border-radius: 8px;
  font-family: 'Fira Code', monospace;
}

/* ═══ Top-5 ═══ */
.top5 { display: flex; flex-direction: column; gap: 10px; }
.top5-row { display: flex; align-items: center; gap: 8px; transition: all .2s ease; }
.top5-row:hover { transform: translateX(3px); }
.top5-collapsed-hint {
  display: flex; align-items: center; gap: 8px; padding: 10px 14px;
  background: linear-gradient(90deg, rgba(99,102,241,.06), rgba(34,211,238,.04));
  border: 1px dashed rgba(99,102,241,.25); border-radius: 8px;
  color: var(--c-primary, #2563EB); font-size: 12px; font-weight: 600;
  cursor: pointer; transition: all .2s ease;
}
.top5-collapsed-hint:hover { background: linear-gradient(90deg, rgba(99,102,241,.1), rgba(34,211,238,.08)); border-color: var(--c-primary, #2563EB); }
.top5-collapsed-hint.subtle {
  background: transparent; border: 0; padding: 4px 0;
  color: var(--c-muted, #64748B); font-size: 11px; justify-content: center;
}
.top5-collapsed-hint.subtle:hover { color: var(--c-primary, #2563EB); background: transparent; }
.rank {
  width: 22px; height: 22px; border-radius: 7px;
  background: rgba(241,245,249,.8); color: #94a3b8;
  font-size: 10px; font-weight: 800;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.rank-top {
  background: var(--c-primary, #1E40AF); color: #fff;
  box-shadow: 0 2px 6px rgba(30,64,175,.2);
}
.breed-name-sm {
  width: 150px; font-size: 12.5px; color: var(--c-text-body, #334155); font-weight: 600; flex-shrink: 0;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.bar-track {
  flex: 1; height: 8px;
  background: rgba(241,245,249,.8); border-radius: 100px; overflow: hidden;
}
.bar-fill  { height: 100%; border-radius: 100px; box-shadow: 0 0 8px rgba(99,102,241,.15); }
.pct-num   { width: 44px; text-align: right; font-size: 12px; font-weight: 700; flex-shrink: 0; }

/* ═══ Area ═══ */
.area-wrap { display: flex; flex-direction: column; align-items: center; gap: 10px; padding: 10px 0; }
.area-label { font-size: 11.5px; color: #94a3b8; font-weight: 600; }
.infer-stats { display: flex; align-items: center; gap: 16px; margin-top: 4px; }
.infer-stat  { text-align: center; }
.is-val { font-size: 20px; font-weight: 800; line-height: 1; }
.is-lbl { font-size: 10.5px; color: #94a3b8; margin-top: 3px; font-weight: 600; }
.infer-sep { width: 1px; height: 26px; background: rgba(99,102,241,.1); }

/* ═══ Seg Grid ═══ */
.seg-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.seg-grid.four-col { grid-template-columns: repeat(4, 1fr); }
.gradcam-highlight { border-color: #fca5a5 !important; box-shadow: 0 0 12px rgba(239,68,68,.12); }
.vis-notes { margin-top: 10px; padding: 0 4px; }
.vis-notes p { margin: 0 0 3px; font-size: 11.5px; color: #94a3b8; line-height: 1.65; }
.seg-item { text-align: center; }
.seg-img {
  width: 100%; aspect-ratio: 1; object-fit: cover;
  border-radius: 12px; border: 1px solid rgba(226,232,240,.5);
  transition: all .25s ease; cursor: zoom-in; display: block;
}
.seg-img:hover {
  transform: scale(1.04);
  box-shadow: 0 8px 28px rgba(99,102,241,.12);
  position: relative; z-index: 5;
}
.seg-cap {
  display: flex; align-items: center; justify-content: center; gap: 6px;
  margin-top: 7px; font-size: 11.5px; color: #64748b; font-weight: 600;
}
.seg-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; box-shadow: 0 0 6px currentColor; }

/* ═══ WebSocket Log Panel ═══ */
.ws-toggle {
  display: flex; align-items: center; gap: 8px;
  margin-top: 10px; padding-top: 8px;
  border-top: 1px dashed var(--c-border, #E2E8F0);
  font-size: 12px; color: var(--c-muted, #64748B); font-weight: 600;
}
.ws-log {
  background: #0F172A; color: #E2E8F0;
  border-radius: 8px; padding: 10px 14px; margin-top: 10px;
  font-family: 'Fira Code', monospace; font-size: 11.5px;
  max-height: 280px; overflow-y: auto;
}
.ws-line { display: flex; gap: 10px; padding: 2px 0; line-height: 1.55; }
.ws-t { color: #64748B; flex-shrink: 0; }
.ws-lvl {
  flex-shrink: 0; width: 50px; font-weight: 700;
  font-size: 10px; padding: 1px 6px; border-radius: 4px; text-align: center;
  background: rgba(255,255,255,.06);
}
.ws-info  .ws-lvl { color: #93C5FD; background: rgba(147,197,253,.12); }
.ws-ok    .ws-lvl { color: #4ADE80; background: rgba(74,222,128,.14); }
.ws-error .ws-lvl { color: #F87171; background: rgba(248,113,113,.16); }
.ws-done  .ws-lvl { color: #FBBF24; background: rgba(251,191,36,.16); }
.ws-msg { flex: 1; word-break: break-all; }

/* ═══ Banner Feedback Action ═══ */
.banner-action-feedback { color: #FBBF24 !important; }
.banner-action-feedback:hover { background: rgba(251,191,36,.18) !important; color: #FCD34D !important; border-color: rgba(251,191,36,.4) !important; }

/* ═══ Compare Mode — Hero ═══ */
.cmp-hero {
  position: relative; overflow: hidden;
  border-radius: var(--radius-lg, 16px);
  background: linear-gradient(135deg, #1E1B4B 0%, #312E81 50%, #4C1D95 100%);
  color: #fff; padding: 22px 26px; margin-bottom: 14px;
  display: flex; align-items: center; justify-content: space-between; gap: 16px;
  box-shadow: 0 8px 28px rgba(76,29,149,.18);
}
.cmp-hero::before {
  content: ''; position: absolute; right: -40px; top: -60px;
  width: 220px; height: 220px; border-radius: 50%;
  background: radial-gradient(circle, rgba(167,139,250,.32), transparent 65%);
  pointer-events: none;
}
.cmp-hero-text { position: relative; z-index: 1; }
.cmp-hero-kicker {
  display: inline-flex; align-items: center; gap: 7px;
  font-size: 10.5px; font-weight: 700; letter-spacing: .12em; text-transform: uppercase;
  color: #C4B5FD; margin-bottom: 8px;
}
.cmp-hero-dot {
  width: 6px; height: 6px; border-radius: 50%; background: #A78BFA;
  box-shadow: 0 0 12px #A78BFA; animation: tspulse 1.6s ease-in-out infinite;
}
.cmp-hero-text h2 {
  margin: 0 0 4px; font-size: 22px; font-weight: 800; letter-spacing: -.01em;
}
.cmp-hero-text p {
  margin: 0; font-size: 12.5px; color: rgba(255,255,255,.72); line-height: 1.7;
  max-width: 640px;
}
.cmp-hero-stat {
  position: relative; z-index: 1; flex-shrink: 0; text-align: center;
  padding: 10px 22px; background: rgba(255,255,255,.08);
  border: 1px solid rgba(255,255,255,.14); border-radius: 14px;
  backdrop-filter: blur(10px);
}
.cmp-hero-stat-num {
  font-size: 38px; font-weight: 900; line-height: 1;
  background: linear-gradient(135deg, #FBBF24 0%, #F472B6 100%);
  -webkit-background-clip: text; background-clip: text; color: transparent;
  font-family: 'Fira Code', monospace;
}
.cmp-hero-stat-lbl {
  margin-top: 4px; font-size: 10.5px; font-weight: 700;
  letter-spacing: .14em; color: rgba(255,255,255,.6); text-transform: uppercase;
}

/* ═══ Compare Upload Card ═══ */
.cmp-upload-card { margin-bottom: 14px; }
.cmp-upload-card :deep(.el-card__body) { padding: 14px; }
.cmp-upload-row {
  display: grid; grid-template-columns: 1fr 1fr; gap: 14px; align-items: stretch;
}
.cmp-uploader { width: 100%; }
.cmp-uploader :deep(.el-upload),
.cmp-uploader :deep(.el-upload-dragger) {
  width: 100%; height: 100%; min-height: 130px; padding: 0;
}
.cmp-uploader :deep(.el-upload-dragger) {
  border: 1.5px dashed rgba(124,58,237,.35);
  border-radius: 10px;
  background: linear-gradient(135deg, rgba(124,58,237,.04), rgba(168,85,247,.02));
  transition: all .2s ease;
}
.cmp-uploader :deep(.el-upload-dragger:hover) {
  border-color: #7C3AED; background: rgba(124,58,237,.06);
}
.cmp-upload-idle {
  display: flex; align-items: center; justify-content: center;
  gap: 12px; height: 100%; min-height: 130px;
}
.cmp-upload-idle .upload-hint {
  margin: 0; font-size: 13px; font-weight: 700; color: #4C1D95;
}
.cmp-upload-preview {
  position: relative; height: 100%; min-height: 130px; overflow: hidden; border-radius: 8px;
}
.cmp-upload-preview img {
  width: 100%; height: 100%; object-fit: cover;
}
.cmp-upload-replace {
  position: absolute; right: 8px; top: 8px;
  display: inline-flex; align-items: center; gap: 4px;
  padding: 4px 10px; border-radius: 100px;
  background: rgba(15,23,42,.7); color: #fff; backdrop-filter: blur(8px);
  font-size: 11px; font-weight: 600;
}
.cmp-upload-cta {
  display: flex; flex-direction: column; gap: 8px; justify-content: center;
}
.cmp-run-btn {
  height: 48px !important; font-weight: 700 !important; font-size: 14px !important;
  background: linear-gradient(135deg, #7C3AED 0%, #6D28D9 100%) !important;
  border: 0 !important;
  box-shadow: 0 4px 14px rgba(124,58,237,.3);
  transition: all .25s ease;
}
.cmp-run-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 8px 22px rgba(124,58,237,.4);
}
.cmp-run-btn:disabled {
  background: #CBD5E1 !important; box-shadow: none;
}
.cmp-cta-tip {
  display: flex; align-items: center; gap: 5px;
  font-size: 11.5px; color: var(--c-muted, #64748B);
  background: rgba(124,58,237,.05); border: 1px solid rgba(124,58,237,.1);
  border-radius: 6px; padding: 6px 10px; line-height: 1.5;
}

/* ═══ Compare Empty / Results ═══ */
.cmp-empty-row {
  display: flex; align-items: center; justify-content: center; gap: 12px;
  padding: 32px 20px; color: var(--c-muted, #94A3B8); font-size: 13px;
  background: var(--c-card, #FFFFFF);
  border: 1.5px dashed var(--c-border, #E2E8F0); border-radius: var(--radius, 12px);
}
.cmp-results {
  display: flex; flex-direction: column; gap: 12px;
}

/* ═══ Compare Card ═══ */
.cmp-card {
  position: relative; overflow: hidden;
  background: var(--c-card, #FFFFFF);
  border: 1px solid var(--c-border, #E2E8F0);
  border-radius: var(--radius, 12px);
  transition: all .2s ease;
}
.cmp-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 28px rgba(15,23,42,.08);
  border-color: var(--c);
}
.cmp-card-bar {
  height: 3px; background: linear-gradient(90deg, var(--c) 0%, transparent 100%);
}

/* —— 上半区：模型身份 —— */
.cmp-card-head {
  display: grid;
  grid-template-columns: 50px 1fr auto;
  gap: 16px; align-items: center;
  padding: 16px 20px 14px;
}
.cmp-card-rank {
  width: 38px; height: 38px; border-radius: 10px;
  background: color-mix(in srgb, var(--c) 12%, white);
  color: var(--c); font-size: 14px; font-weight: 800;
  display: flex; align-items: center; justify-content: center;
  font-family: 'Fira Code', monospace;
}
.cmp-card-id { min-width: 0; }
.cmp-card-name {
  font-size: 15px; font-weight: 800; color: var(--c-dark, #0F172A);
  line-height: 1.25; margin-bottom: 5px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.cmp-card-meta {
  display: flex; align-items: center; gap: 6px; flex-wrap: wrap;
  font-size: 11.5px; color: var(--c-muted, #64748B);
}
.cmp-meta-pill {
  display: inline-block; padding: 2px 9px; border-radius: 100px;
  background: color-mix(in srgb, var(--c) 8%, white);
  color: var(--c); font-weight: 600;
  border: 1px solid color-mix(in srgb, var(--c) 22%, white);
}
.cmp-meta-dot { color: #CBD5E1; }
.cmp-card-acc { text-align: right; flex-shrink: 0; }
.cmp-card-acc-num {
  font-size: 24px; font-weight: 800; line-height: 1;
  color: var(--c); font-family: 'Fira Code', monospace;
}
.cmp-card-acc-num span { font-size: 14px; margin-left: 1px; opacity: .8; }
.cmp-card-acc-lbl {
  margin-top: 3px; font-size: 10px; font-weight: 700;
  color: var(--c-muted, #94A3B8); letter-spacing: .1em; text-transform: uppercase;
}

/* —— 下半区：预测 —— */
.cmp-card-pred {
  display: grid; grid-template-columns: 1fr 1.4fr; gap: 18px;
  padding: 12px 20px 16px;
  border-top: 1px solid var(--c-border, #F1F5F9);
  background: linear-gradient(180deg, #FAFBFC 0%, var(--c-card, #FFFFFF) 100%);
}
.cmp-pred-main { display: flex; flex-direction: column; justify-content: center; }
.cmp-pred-lbl {
  font-size: 10px; font-weight: 700; letter-spacing: .12em;
  color: var(--c-muted, #94A3B8); text-transform: uppercase;
  margin-bottom: 4px;
}
.cmp-pred-breed {
  font-size: 18px; font-weight: 800; color: var(--c-dark, #0F172A);
  line-height: 1.15;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.cmp-pred-conf-block {
  display: flex; flex-direction: column; gap: 6px; justify-content: center;
}
.cmp-pred-conf-num {
  font-size: 26px; font-weight: 800; line-height: 1; color: var(--c);
  font-family: 'Fira Code', monospace;
  display: flex; align-items: baseline; gap: 2px;
}
.cmp-pred-conf-num span { font-size: 14px; opacity: .7; }
.cmp-pred-bar-wrap {
  position: relative; height: 6px; background: #F1F5F9;
  border-radius: 3px; overflow: hidden;
}
.cmp-pred-bar {
  position: absolute; left: 0; top: 0; bottom: 0;
  background: linear-gradient(90deg, var(--c) 0%, color-mix(in srgb, var(--c) 70%, white) 100%);
  border-radius: 3px; transition: width .6s cubic-bezier(.33,1,.68,1);
}
.cmp-pred-latency {
  font-size: 10.5px; color: var(--c-muted, #94A3B8);
  font-family: 'Fira Code', monospace;
}

/* —— Unavailable —— */
.cmp-card-unavailable {
  display: flex; align-items: center; gap: 8px;
  padding: 14px 20px;
  border-top: 1px solid var(--c-border, #F1F5F9);
  background: #F8FAFC;
  color: #94A3B8; font-size: 12px; font-weight: 600;
}

/* ═══ Compare Insight ═══ */
.cmp-insight {
  display: flex; gap: 12px;
  padding: 14px 16px; margin-top: 4px;
  background: linear-gradient(135deg, rgba(37,99,235,.04), rgba(124,58,237,.04));
  border: 1px solid rgba(37,99,235,.14);
  border-radius: var(--radius, 12px);
}
.cmp-insight-icon {
  flex-shrink: 0; width: 28px; height: 28px; border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  background: #2563EB; color: #fff;
  box-shadow: 0 4px 12px rgba(37,99,235,.25);
}
.cmp-insight-body { flex: 1; }
.cmp-insight-title {
  font-size: 12px; font-weight: 800; color: var(--c-dark, #0F172A);
  margin-bottom: 4px; letter-spacing: .02em;
}
.cmp-insight-text {
  font-size: 12.5px; line-height: 1.8; color: var(--c-text-body, #334155);
}

/* —— 紧凑屏适配 —— */
@media (max-width: 1100px) {
  .cmp-hero { flex-direction: column; align-items: flex-start; gap: 14px; }
  .cmp-upload-row { grid-template-columns: 1fr; }
  .cmp-card-head { grid-template-columns: 38px 1fr; }
  .cmp-card-acc { grid-column: 2; text-align: left; margin-top: 2px; }
  .cmp-card-pred { grid-template-columns: 1fr; gap: 10px; }
}

/* ═══ Camera Dialog ═══ */
.camera-dialog :deep(.el-dialog) {
  background: linear-gradient(180deg, #0F172A 0%, #1E293B 100%);
  border: 1px solid rgba(255,255,255,.08);
  border-radius: 16px;
  overflow: hidden;
}
.camera-dialog :deep(.el-dialog__header) {
  background: rgba(255,255,255,.03);
  border-bottom: 1px solid rgba(255,255,255,.06);
  padding: 16px 22px; margin: 0;
}
.camera-dialog :deep(.el-dialog__body) { padding: 16px 22px; }
.camera-dialog :deep(.el-dialog__footer) {
  background: rgba(255,255,255,.02);
  border-top: 1px solid rgba(255,255,255,.06);
  padding: 14px 22px;
}
.camera-dialog :deep(.el-dialog__headerbtn) { top: 18px; right: 18px; }
.camera-dialog :deep(.el-dialog__close) { color: #94A3B8; font-size: 18px; }
.camera-dialog :deep(.el-dialog__close:hover) { color: #fff; }

.cam-dialog-header { padding: 0; }
.cam-dialog-title {
  display: flex; align-items: center; gap: 8px;
  font-size: 16px; font-weight: 800; color: #F1F5F9;
  letter-spacing: -.01em;
}
.cam-dialog-sub {
  margin-top: 4px; font-size: 11.5px; color: #94A3B8; line-height: 1.6;
}

.cam-stage {
  position: relative; width: 100%; aspect-ratio: 16/9;
  background: #000; border-radius: 12px; overflow: hidden;
  box-shadow: inset 0 0 0 1px rgba(255,255,255,.08);
}
.cam-video {
  width: 100%; height: 100%; object-fit: cover; display: block;
  /* 镜像翻转，符合自拍习惯 */
  transform: scaleX(-1);
}
.cam-overlay {
  position: absolute; inset: 0; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 10px;
  color: #CBD5E1; background: rgba(15,23,42,.8); backdrop-filter: blur(4px);
}
.cam-overlay span { font-size: 14px; font-weight: 600; }
.cam-overlay small { font-size: 11px; color: #94A3B8; }
.cam-error { color: #FCA5A5; }
.cam-error small { color: #94A3B8; }

.cam-frame {
  position: absolute; inset: 28px;
  pointer-events: none;
}
.cam-corner {
  position: absolute; width: 28px; height: 28px;
  border-color: #10B981; border-style: solid; border-width: 0;
}
.cam-corner-tl { top: 0; left: 0; border-top-width: 3px; border-left-width: 3px; border-top-left-radius: 6px; }
.cam-corner-tr { top: 0; right: 0; border-top-width: 3px; border-right-width: 3px; border-top-right-radius: 6px; }
.cam-corner-bl { bottom: 0; left: 0; border-bottom-width: 3px; border-left-width: 3px; border-bottom-left-radius: 6px; }
.cam-corner-br { bottom: 0; right: 0; border-bottom-width: 3px; border-right-width: 3px; border-bottom-right-radius: 6px; }

.cam-live {
  position: absolute; top: -8px; right: -8px;
  display: inline-flex; align-items: center; gap: 5px;
  padding: 3px 9px; border-radius: 100px;
  background: rgba(239,68,68,.95); color: #fff;
  font-size: 10px; font-weight: 800; letter-spacing: .12em;
  box-shadow: 0 4px 12px rgba(239,68,68,.35);
}
.cam-live-dot {
  width: 6px; height: 6px; border-radius: 50%; background: #fff;
  animation: campulse 1.2s ease-in-out infinite;
}
@keyframes campulse { 0%,100%{opacity:1} 50%{opacity:.3} }

.cam-actions {
  display: flex; justify-content: flex-end; gap: 8px;
}
.cam-actions .el-button {
  height: 38px;
}
.cam-shoot-btn {
  background: linear-gradient(135deg, #10B981 0%, #059669 100%) !important;
  border: 0 !important; font-weight: 700 !important;
  padding: 0 22px !important;
  box-shadow: 0 4px 14px rgba(16,185,129,.3) !important;
}
.cam-shoot-btn:disabled { background: #475569 !important; box-shadow: none !important; opacity: .6; }

/* 触发按钮 (上传卡 header 中) */
.camera-btn-trigger {
  background: linear-gradient(135deg, rgba(16,185,129,.1), rgba(34,197,94,.05)) !important;
  border-color: rgba(16,185,129,.3) !important;
  color: #059669 !important;
}
.camera-btn-trigger:hover {
  background: linear-gradient(135deg, #10B981, #059669) !important;
  color: #fff !important;
  border-color: #10B981 !important;
}

/* ═══ Feedback Dialog ═══ */
.fb-form { display: flex; flex-direction: column; gap: 14px; }
.fb-row { display: flex; align-items: center; gap: 12px; font-size: 13px; }
.fb-row-block { flex-direction: column; align-items: stretch; gap: 6px; }
.fb-lbl { color: var(--c-muted, #64748B); font-weight: 600; min-width: 80px; }
.fb-pred { font-weight: 700; color: var(--c-dark); display: inline-flex; align-items: center; gap: 8px; }
.fb-conf { font-size: 11px; padding: 2px 8px; border-radius: 100px; background: rgba(245,158,11,.12); color: #D97706; font-family: 'Fira Code', monospace; }
.fb-success { display: flex; flex-direction: column; align-items: center; gap: 12px; padding: 24px 0; color: var(--c-text-body); font-size: 14px; font-weight: 600; }

/* ═══ Responsive ═══ */
@media (max-width: 1200px) {
  .seg-grid.four-col { grid-template-columns: repeat(2, 1fr); }
  .standby-hero, .standby-detail-grid { grid-template-columns: 1fr; }
  .standby-output-grid { grid-template-columns: 1fr; }
}

</style>
