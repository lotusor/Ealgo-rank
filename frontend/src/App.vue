<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useTheme } from '@/composables/useTheme'

const auth = useAuthStore()
// 主题切换由 useTheme 在模块加载时应用到 <html data-theme>，这里仅保留引用。
useTheme()

// 监听后端强制登出（token 失效且刷新失败）
function onLogout() {
  auth.logout()
}
onMounted(() => window.addEventListener('auth:logout', onLogout))
onUnmounted(() => window.removeEventListener('auth:logout', onLogout))
</script>

<template>
  <router-view v-slot="{ Component }">
    <component :is="Component" />
  </router-view>
</template>
