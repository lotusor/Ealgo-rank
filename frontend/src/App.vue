<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useTheme } from '@/composables/useTheme'
import { SESSION_KEY } from '@/api/session'

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
function onSessionChange(event: StorageEvent) {
  // 换号后重建视图，避免旧身份表单使用另一标签页的新令牌。
  if (event.key === SESSION_KEY) window.location.reload()
}
onMounted(() => {
  window.addEventListener('auth:logout', onLogout)
  window.addEventListener('storage', onSessionChange)
})
onUnmounted(() => {
  window.removeEventListener('auth:logout', onLogout)
  window.removeEventListener('storage', onSessionChange)
})
</script>

<template>
  <router-view />
</template>

<style>
/* 布局壳不参与转场，避免改变固定导航和浮层的定位参照。 */
.page-enter-active,
.page-leave-active {
  transition: opacity var(--duration-base) var(--ease-standard);
}
.page-enter-from,
.page-leave-to {
  opacity: 0;
}
@media (prefers-reduced-motion: reduce) {
  .page-enter-active,
  .page-leave-active {
    transition: none;
  }
}
</style>
