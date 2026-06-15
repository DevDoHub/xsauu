import { createApp } from 'vue'
import App from './App.vue'
import './assets/main.css'
import axios from 'axios'
import store from './store'

// 创建 Vue 应用程序
const app = createApp(App)
app.config.globalProperties.$axios = axios

// 注册 Vuex Store
// Requirements: 8.6 - 确保 store 在应用启动时正确初始化
app.use(store)

app.provide("$axios", axios);

// 挂载应用程序
app.mount('#app')