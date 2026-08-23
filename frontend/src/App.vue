<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useTheme } from '@/composables/useTheme'

const auth = useAuthStore()
const router = useRouter()
// 主题切换由 useTheme 在模块加载时应用到 <html data-theme>，这里仅保留引用。
useTheme()

// 监听后端强制登出（token 失效且刷新失败）：清理状态并回登录页，
// 带上当前路径，登录成功后原路返回。
function onLogout() {
  const redirect = router.currentRoute.value.fullPath
  auth.logout()
  if (router.currentRoute.value.name !== 'login') {
    router.replace({ name: 'login', query: { redirect } })
  }
}
onMounted(() => window.addEventListener('auth:logout', onLogout))
onUnmounted(() => window.removeEventListener('auth:logout', onLogout))
</script>

<template>
  <router-view v-slot="{ Component }">
    <component :is="Component" />
  </router-view>
</template>
