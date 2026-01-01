import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['stopper.svg'],
      manifest: {
        name: 'STOPPER',
        short_name: 'STOPPER',
        description: '멈추면 보이는 한 끼의 %',
        theme_color: '#EF4444',
        background_color: '#ffffff',
        display: 'standalone',
        icons: [
          {
            src: 'stopper.svg',
            sizes: 'any',
            type: 'image/svg+xml'
          }
        ]
      }
    })
  ],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8003',
        changeOrigin: true
      }
    }
  }
})
