import { createI18n } from 'vue-i18n'
import zh from './locales/zh.js'
import en from './locales/en.js'

const saved = localStorage.getItem('pet-vision-locale') || 'zh'

export const i18n = createI18n({
  legacy: false,
  globalInjection: true,
  locale: saved,
  fallbackLocale: 'zh',
  messages: { zh, en },
})

export function setLocale(loc) {
  i18n.global.locale.value = loc
  localStorage.setItem('pet-vision-locale', loc)
  document.documentElement.lang = loc === 'zh' ? 'zh-CN' : 'en'
}
