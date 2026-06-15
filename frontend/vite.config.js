import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    host: true, // 监听 0.0.0.0，允许通过本机 IP / 局域网 IP 访问
    port: 5173,
    proxy: {
      // 后端 API 代理
      '/api': {
        target: 'http://192.168.238.100:5020',
        changeOrigin: true
      },
      // 报警截图静态文件
      '/alarm_images': {
        target: 'http://192.168.238.100:5020',
        changeOrigin: true
      },
      // mediamtx API 代理（获取在线摄像头列表）
      '/mediamtx-api': {
        target: 'http://192.168.238.100:9997',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/mediamtx-api/, '')
      },
      // Socket.IO 代理（语音通话使用）
      '/socket.io': {
        target: 'http://127.0.0.1:5020',
        changeOrigin: true,
        ws: true  // 启用 WebSocket 代理
      }
    }
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets'
  }
})