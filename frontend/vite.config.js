import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173
  },
  build: {
    chunkSizeWarningLimit: 1500,
    rollupOptions: {
      output: {
        // 手动分包：把大型第三方库拆成独立 chunk，便于浏览器并发加载和长缓存
        manualChunks: {
          'vendor-vue':         ['vue', 'vue-router', 'vue-i18n'],
          'vendor-echarts':     ['echarts'],
          'vendor-element':     ['element-plus', '@element-plus/icons-vue'],
          'vendor-pdf':         ['html2canvas-pro', 'jspdf'],
        },
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: false,
    include: ['test/**/*.test.js'],
  },
})
