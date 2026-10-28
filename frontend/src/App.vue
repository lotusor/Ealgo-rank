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
/*
 * 页面转场只作用于「布局内容区里的页面组件」，不碰布局壳：
 * 壳一旦被 transform，固定导航与浮层的定位参照会跟着走，滚动位置也会跳。
 * 进出用不对称时长——离场快（让位），入场略缓（把注意力带到新页）。
 */
.page-enter-active {
  transition:
    opacity var(--duration-page-in) var(--ease-out),
    transform var(--duration-page-in) var(--ease-out);
}
.page-leave-active {
  transition:
    opacity var(--duration-page-out) var(--ease-standard),
    transform var(--duration-page-out) var(--ease-standard);
}
.page-enter-from {
  opacity: 0;
  transform: translateY(10px);
}
.page-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}
@media (prefers-reduced-motion: reduce) {
  .page-enter-active,
  .page-leave-active {
    transition: none;
  }
  .page-enter-from,
  .page-leave-to {
    opacity: 1;
    transform: none;
  }
}
</style>
