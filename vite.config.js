import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  base: './',
  build: {
    chunkSizeWarningLimit: 550,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('/echarts/')) return 'echarts'
          if (id.includes('/element-plus/')) return 'element-plus'
          if (id.includes('/vue/')) return 'vue-vendor'
        }
      }
    }
  }
})
