<script setup>
import { computed, ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { setLocale } from './i18n'
import http from './api/http'

const route = useRoute()
const { t, locale } = useI18n()

const pageMetaKey = {
  '/':         'intro',
  '/dataset':  'dataset',
  '/predict':  'predict',
  '/analysis': 'analysis',
  '/extra':    'extra',
}
const currentMeta = computed(() => {
  const k = pageMetaKey[route.path]
  return k
    ? { title: t(`page.${k}.title`), desc: t(`page.${k}.desc`) }
    : { title: '', desc: '' }
})

const backendOk = ref(null)

onMounted(async () => {
  document.documentElement.classList.remove('dark')
  localStorage.removeItem('pet-vision-theme')
  try { await http.get('/'); backendOk.value = true }
  catch { backendOk.value = false }
})

const navItems = computed(() => [
  { path: '/',         label: t('nav.intro'),    icon: 'HomeFilled',   color: '#818cf8', shadow: 'rgba(129,140,248,.5)'  },
  { path: '/dataset',  label: t('nav.dataset'),  icon: 'DataAnalysis', color: '#22d3ee', shadow: 'rgba(34,211,238,.5)'   },
  { path: '/predict',  label: t('nav.predict'),  icon: 'Camera',       color: '#34d399', shadow: 'rgba(52,211,153,.5)'   },
  { path: '/analysis', label: t('nav.analysis'), icon: 'TrendCharts',  color: '#fb923c', shadow: 'rgba(251,146,60,.5)'   },
  { path: '/extra',    label: t('nav.extra'),    icon: 'Star',         color: '#c084fc', shadow: 'rgba(192,132,252,.5)'  },
])

function toggleLang() {
  setLocale(locale.value === 'zh' ? 'en' : 'zh')
}
</script>

<template>
  <div class="app-shell">
    <!-- ===== 侧边栏 ===== -->
    <aside class="sidebar">
      <!-- 背景纹理 -->
      <div class="sb-dots"></div>
      <!-- 顶部辉光 -->
      <div class="sb-glow"></div>

      <!-- 品牌区 -->
      <div class="sb-brand">
        <div class="sb-logo">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"
            stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="4"  r="2.2"/>
            <circle cx="18" cy="8"  r="2.2"/>
            <circle cx="4"  cy="8"  r="2.2"/>
            <circle cx="20" cy="14" r="1.7"/>
            <path d="M11 10c-3.5 0-6 3-6 6 0 2 1.5 3.5 3.5 3.5.8 0 1.4-.3 2.5-.3s1.7.3 2.5.3c2 0 3.5-1.5 3.5-3.5 0-3-2.5-6-6-6Z"/>
          </svg>
        </div>
        <div class="sb-brand-text">
          <div class="sb-brand-name">Pet Vision</div>
          <div class="sb-brand-tag">
            <span class="sb-brand-version">v1.0</span>
            <span class="sb-brand-dot"></span>
            <span>Multi-task</span>
          </div>
        </div>
      </div>

      <!-- 导航 -->
      <nav class="sb-nav">
        <div class="sb-nav-section">
          <span>导航</span>
          <span class="sb-nav-count">{{ navItems.length }}</span>
        </div>
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="sb-item"
          :class="{ active: route.path === item.path }"
          :style="{ '--c': item.color, '--s': item.shadow }"
          :title="item.label"
        >
          <div class="sb-item-icon">
            <el-icon><component :is="item.icon" /></el-icon>
          </div>
          <span class="sb-item-label">{{ item.label }}</span>
          <el-icon class="sb-item-arrow" :size="12"><ArrowRight /></el-icon>
        </router-link>
      </nav>

      <!-- 模型快览卡 -->
      <div class="sb-info">
        <div class="sb-info-card">
          <div class="sb-info-title">
            <el-icon :size="11" color="#22D3EE"><Cpu /></el-icon>
            模型 · 实时状态
          </div>
          <div class="sb-info-rows">
            <div class="sb-info-row">
              <span class="sb-info-tag tag-cls">CLS</span>
              <span class="sb-info-name">ResNet-34</span>
              <span class="sb-info-val">98.65%</span>
            </div>
            <div class="sb-info-row">
              <span class="sb-info-tag tag-seg">SEG</span>
              <span class="sb-info-name">U-Net</span>
              <span class="sb-info-val">0.937</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 底部状态 -->
      <div class="sb-footer">
        <div class="sb-status">
          <div class="sb-status-dot"
            :class="backendOk === null ? 'warn' : backendOk ? 'ok' : 'err'">
          </div>
          <div class="sb-status-info">
            <div class="sb-status-title">
              {{ backendOk === null ? $t('common.connecting') : backendOk ? $t('common.backendOk') : $t('common.backendOff') }}
            </div>
            <div class="sb-status-sub">127.0.0.1 : 8000</div>
          </div>
          <div class="sb-status-pulse" v-if="backendOk"></div>
        </div>
      </div>
    </aside>

    <!-- ===== 主区域 ===== -->
    <div class="main-wrap">
      <!-- 顶部栏 -->
      <header class="topbar">
        <div class="topbar-left">
          <div class="topbar-title">{{ currentMeta.title }}</div>
          <div class="topbar-desc">{{ currentMeta.desc }}</div>
        </div>
        <div class="topbar-right">
          <div class="topbar-status">
            <div class="ts-dot"
              :class="backendOk === null ? 'connecting' : backendOk ? 'ok' : 'err'"></div>
            <span>{{ backendOk === null ? $t('common.connecting') : backendOk ? $t('common.backendOk') : $t('common.backendOff') }}</span>
          </div>
          <button class="lang-toggle" @click="toggleLang" :title="$t('language.label')">
            <el-icon :size="13"><Promotion /></el-icon>
            <span>{{ locale === 'zh' ? 'EN' : '中' }}</span>
          </button>
          <div class="topbar-badge">37{{ $t('common.classes') }} · 7,390{{ $t('common.images') }}</div>
        </div>
      </header>

      <!-- 内容 -->
      <main class="page-content">
        <router-view v-slot="{ Component }">
          <transition name="fade">
            <component :is="Component" :key="route.path" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<style scoped>
/* ─── Shell ─── */
.app-shell { display: flex; min-height: 100vh; }

/* ═══════════════════════════════════════
   Sidebar — Modern Dark with Color Accent
   ═══════════════════════════════════════ */
.sidebar {
  width: var(--sidebar-width, 240px); min-height: 100vh;
  position: fixed; top: 0; left: 0; bottom: 0; z-index: 100;
  display: flex; flex-direction: column;
  background: linear-gradient(180deg, #0B1220 0%, #0F172A 50%, #0B1220 100%);
  border-right: 1px solid rgba(255,255,255,.04);
  box-shadow: 2px 0 24px rgba(0,0,0,.18);
  overflow: hidden;
}
.sb-dots {
  position: absolute; inset: 0; pointer-events: none;
  background:
    radial-gradient(circle at 20% 0%, rgba(99,102,241,.08), transparent 40%),
    radial-gradient(circle at 80% 100%, rgba(34,211,238,.05), transparent 45%);
}
.sb-glow { display: none; }

/* ─── Brand ─── */
.sb-brand {
  position: relative; z-index: 1;
  display: flex; align-items: center; gap: 12px;
  padding: 22px 18px 18px;
  border-bottom: 1px solid rgba(255,255,255,.05);
}
.sb-logo {
  width: 42px; height: 42px; flex-shrink: 0; border-radius: 12px;
  background: linear-gradient(135deg, #6366F1 0%, #8B5CF6 50%, #EC4899 100%);
  display: flex; align-items: center; justify-content: center;
  color: #fff;
  box-shadow:
    0 6px 18px rgba(139,92,246,.32),
    inset 0 1px 0 rgba(255,255,255,.18);
  position: relative; overflow: hidden;
}
.sb-logo::before {
  content: ''; position: absolute; inset: 0;
  background: radial-gradient(circle at 30% 20%, rgba(255,255,255,.25), transparent 55%);
}
.sb-logo svg { width: 22px; height: 22px; position: relative; z-index: 1; }

.sb-brand-text { min-width: 0; }
.sb-brand-name {
  font-size: 16px; font-weight: 800; letter-spacing: -.3px;
  background: linear-gradient(135deg, #F8FAFC 0%, #C7D2FE 100%);
  -webkit-background-clip: text; background-clip: text; color: transparent;
}
.sb-brand-tag {
  display: flex; align-items: center; gap: 6px;
  font-size: 9.5px; color: #64748B; margin-top: 3px;
  font-weight: 700; letter-spacing: .04em;
}
.sb-brand-version {
  padding: 1px 6px; border-radius: 100px;
  background: rgba(99,102,241,.14);
  color: #A5B4FC;
  font-family: 'Fira Code', monospace;
}
.sb-brand-dot {
  width: 4px; height: 4px; border-radius: 50%; flex-shrink: 0;
  background: #475569;
}
@keyframes sbpulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:.3;transform:scale(.85)} }

/* ─── Nav ─── */
.sb-nav {
  flex: 1; padding: 14px 12px 8px;
  display: flex; flex-direction: column; gap: 3px;
  position: relative; z-index: 1;
  overflow-y: auto;
}
.sb-nav::-webkit-scrollbar { width: 0; }
.sb-nav-section {
  display: flex; align-items: center; justify-content: space-between;
  font-size: 10px; letter-spacing: .12em; color: #64748B;
  font-weight: 700; padding: 0 12px 4px; margin-bottom: 6px;
  text-transform: uppercase;
}
.sb-nav-count {
  display: inline-flex; align-items: center; justify-content: center;
  min-width: 18px; height: 16px; padding: 0 5px;
  border-radius: 100px; background: rgba(255,255,255,.06);
  font-size: 9px; color: #94A3B8;
  font-family: 'Fira Code', monospace;
}

.sb-item {
  --c: #94a3b8;
  display: flex; align-items: center; gap: 11px;
  min-height: 42px; padding: 7px 12px 7px 10px;
  border-radius: 10px; text-decoration: none;
  color: #94A3B8; font-size: 13.5px; font-weight: 600;
  transition: all .25s cubic-bezier(.33,1,.68,1);
  position: relative; cursor: pointer;
}
.sb-item:hover {
  background: rgba(255,255,255,.04);
  color: #F1F5F9;
  transform: translateX(2px);
}
.sb-item:hover .sb-item-icon {
  color: var(--c);
  background: color-mix(in srgb, var(--c) 16%, rgba(255,255,255,.04));
  border-color: color-mix(in srgb, var(--c) 28%, transparent);
}
.sb-item:hover .sb-item-arrow { opacity: .6; transform: translateX(0); }

/* Active — vibrant per-item color */
.sb-item.active {
  background: linear-gradient(
    135deg,
    color-mix(in srgb, var(--c) 22%, transparent) 0%,
    color-mix(in srgb, var(--c) 8%, transparent) 100%);
  color: #fff;
  box-shadow:
    inset 0 0 0 1px color-mix(in srgb, var(--c) 30%, transparent),
    0 6px 16px color-mix(in srgb, var(--c) 18%, transparent);
}
.sb-item.active .sb-item-icon {
  background: linear-gradient(135deg, var(--c) 0%, color-mix(in srgb, var(--c) 70%, #1E293B) 100%);
  color: #fff;
  border-color: transparent;
  box-shadow: 0 4px 14px color-mix(in srgb, var(--c) 40%, transparent);
}
.sb-item.active::before {
  content: ''; position: absolute;
  left: -12px; top: 8px; bottom: 8px;
  width: 3px; border-radius: 0 4px 4px 0;
  background: var(--c);
  box-shadow: 0 0 12px var(--c);
}
.sb-item.active .sb-item-arrow { opacity: 1; color: var(--c); transform: translateX(0); }

.sb-item-icon {
  width: 30px; height: 30px; flex-shrink: 0; border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  font-size: 14px; color: #64748B;
  background: rgba(255,255,255,.03);
  border: 1px solid rgba(255,255,255,.04);
  transition: all .25s ease;
}
.sb-item-label { flex: 1; min-width: 0; }
.sb-item-arrow {
  flex-shrink: 0; opacity: 0; color: #64748B;
  transform: translateX(-4px); transition: all .25s ease;
}

/* ─── Info Card (Model Live) ─── */
.sb-info { padding: 4px 14px 10px; position: relative; z-index: 1; }
.sb-info-card {
  background: linear-gradient(180deg, rgba(255,255,255,.04), rgba(255,255,255,.015));
  border: 1px solid rgba(255,255,255,.05);
  border-radius: 10px; padding: 10px 12px;
}
.sb-info-title {
  display: inline-flex; align-items: center; gap: 5px;
  font-size: 9.5px; font-weight: 700; letter-spacing: .08em;
  color: #94A3B8; text-transform: uppercase;
  margin-bottom: 8px;
}
.sb-info-rows { display: flex; flex-direction: column; gap: 6px; }
.sb-info-row {
  display: flex; align-items: center; gap: 8px;
  font-size: 11px; line-height: 1;
}
.sb-info-tag {
  flex-shrink: 0;
  font-size: 9px; font-weight: 800; letter-spacing: .08em;
  padding: 2px 6px; border-radius: 4px;
  font-family: 'Fira Code', monospace;
}
.sb-info-tag.tag-cls { background: rgba(59,130,246,.16); color: #93C5FD; }
.sb-info-tag.tag-seg { background: rgba(34,197,94,.16);  color: #86EFAC; }
.sb-info-name { flex: 1; color: #CBD5E1; font-weight: 600; }
.sb-info-val {
  color: #F1F5F9; font-weight: 800;
  font-family: 'Fira Code', monospace; font-size: 11px;
}

/* ─── Footer Status ─── */
.sb-footer { padding: 8px 14px 16px; position: relative; z-index: 1; }
.sb-status {
  position: relative; overflow: hidden;
  display: flex; align-items: center; gap: 10px;
  padding: 10px 12px;
  background: linear-gradient(180deg, rgba(255,255,255,.04), rgba(255,255,255,.015));
  border: 1px solid rgba(255,255,255,.06);
  border-radius: 12px;
}
.sb-status-info { flex: 1; min-width: 0; }
.sb-status-dot {
  width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0;
  position: relative;
}
.sb-status-dot.warn { background: #F59E0B; box-shadow: 0 0 8px rgba(245,158,11,.5); animation: sbpulse 1.2s infinite; }
.sb-status-dot.ok   { background: #22C55E; box-shadow: 0 0 10px rgba(34,197,94,.6); }
.sb-status-dot.err  { background: #EF4444; box-shadow: 0 0 8px rgba(239,68,68,.5); }
.sb-status-dot.ok::after {
  content: ''; position: absolute; inset: -3px; border-radius: 50%;
  border: 1.5px solid #22C55E; opacity: .6;
  animation: sbring 1.8s ease-out infinite;
}
@keyframes sbring {
  0%   { transform: scale(.7); opacity: .8; }
  100% { transform: scale(2); opacity: 0; }
}
.sb-status-title { font-size: 11.5px; font-weight: 700; color: #E2E8F0; line-height: 1.25; }
.sb-status-sub   { font-size: 9.5px; color: #64748B; margin-top: 2px; font-family: 'Fira Code', monospace; letter-spacing: .2px; }
.sb-status-pulse {
  position: absolute; right: -30px; top: 50%; transform: translateY(-50%);
  width: 80px; height: 60px;
  background: radial-gradient(ellipse, rgba(34,197,94,.18), transparent 70%);
  pointer-events: none;
}

/* ═══════════════════════════════════════
   Main Area — Clean Background
   ═══════════════════════════════════════ */
.main-wrap {
  flex: 1; margin-left: var(--sidebar-width, 240px); width: calc(100% - var(--sidebar-width, 240px));
  min-width: 0; display: flex; flex-direction: column; min-height: 100vh;
  background: var(--c-bg, #F8FAFC);
}

/* Topbar — Clean Professional */
.topbar {
  position: sticky; top: 0; z-index: 50;
  min-height: var(--header-height, 56px);
  background: rgba(255,255,255,.85);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--c-border, #E2E8F0);
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 28px;
  gap: 14px;
}
.topbar-left { display: flex; flex-direction: column; justify-content: center; gap: 1px; }
.topbar-title {
  font-size: 18px; font-weight: 800; line-height: 1.2; letter-spacing: -.02em;
  color: var(--c-dark, #0F172A);
}
.topbar-desc { font-size: 11.5px; color: var(--c-muted, #64748B); }
.topbar-right { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; justify-content: flex-end; }
.topbar-status {
  display: flex; align-items: center; gap: 6px;
  font-size: 11.5px; color: #64748b; font-weight: 600;
}
.ts-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.ts-dot.connecting { background: #F59E0B; box-shadow: 0 0 6px rgba(245,158,11,.4); animation: tspulse 1.2s infinite; }
.ts-dot.ok  { background: #22C55E; box-shadow: 0 0 6px rgba(34,197,94,.4); animation: tspulse 2s infinite; }
.ts-dot.err { background: #EF4444; box-shadow: 0 0 6px rgba(239,68,68,.4); }
@keyframes tspulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:.3;transform:scale(.8)} }
.topbar-badge {
  font-size: 11px; font-weight: 700;
  background: rgba(37,99,235,.06);
  color: var(--c-primary, #2563EB);
  border: 1px solid rgba(37,99,235,.2);
  padding: 4px 12px; border-radius: 100px;
  letter-spacing: .02em;
  transition: all .2s ease;
}
.lang-toggle {
  display: inline-flex; align-items: center; gap: 5px;
  background: var(--c-card, #FFFFFF);
  border: 1px solid var(--c-border, #E2E8F0);
  color: var(--c-text-body, #334155);
  font-size: 11.5px; font-weight: 700;
  padding: 4px 11px; border-radius: 100px;
  cursor: pointer; transition: all .2s ease;
}
.lang-toggle:hover {
  border-color: var(--c-primary, #2563EB);
  color: var(--c-primary, #2563EB);
  background: rgba(37,99,235,.04);
}
.topbar-badge:hover { background: rgba(37,99,235,.1); border-color: rgba(37,99,235,.35); }

/* Content */
.page-content {
  flex: 1; padding: 24px 28px 32px;
  max-width: 1360px; width: 100%; margin: 0 auto;
}

/* ─── Responsive ─── */
@media (max-width: 1200px) {
  .sidebar { width: 72px; }
  .sb-brand { justify-content: center; padding: 16px 8px 12px; }
  .sb-brand > div:last-child, .sb-nav-section, .sb-item span, .sb-status > div:last-child { display: none; }
  .sb-nav { padding: 8px 8px; }
  .sb-item { justify-content: center; padding: 8px 0; }
  .sb-item-icon { width: 32px; height: 32px; }
  .sb-footer { padding: 8px 10px 12px; }
  .sb-status { justify-content: center; padding: 10px 0; }
  .main-wrap { margin-left: 72px; width: calc(100% - 72px); }
  .page-content { padding: 18px 16px 24px; }
}
@media (max-width: 900px) {
  .topbar { padding: 0 18px; }
  .topbar-title { font-size: 16px; }
  .topbar-desc { font-size: 10.5px; }
  .topbar-badge { font-size: 10px; padding: 4px 10px; }
  .page-content { padding: 16px 14px 20px; }
}
@media (max-width: 640px) {
  .sidebar { width: 56px; }
  .sb-brand { padding: 12px 6px 10px; }
  .sb-logo { width: 36px; height: 36px; }
  .sb-logo-icon { font-size: 18px; }
  .sb-sep, .sb-footer { display: none; }
  .sb-nav { padding: 8px 6px; gap: 4px; align-items: center; }
  .sb-item { width: 40px; height: 40px; padding: 0; }
  .sb-item.active::before { left: 0; width: 3px; height: 20px; }
  .main-wrap { margin-left: 56px; width: calc(100% - 56px); }
  .topbar { min-height: 48px; padding: 0 10px; }
  .topbar-desc, .topbar-status span { display: none; }
  .topbar-badge { font-size: 9.5px; padding: 3px 8px; }
  .page-content { padding: 10px 10px 16px; }
}
</style>
