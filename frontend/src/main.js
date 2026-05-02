import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElIcons from '@element-plus/icons-vue'

import App from './App.vue'
import router from './router'
import { i18n } from './i18n'
import './style.css'

const app = createApp(App)

Object.keys(ElIcons).forEach(key => {
  app.component(key, ElIcons[key])
})

app.use(router).use(ElementPlus).use(i18n).mount('#app')
