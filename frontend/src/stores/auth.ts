import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { fetchMe, login as apiLogin, logout as apiLogout } from '@/api'
import type { UserMe } from '@/api/types'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('access_token'))
  const user = ref<UserMe | null>(null)

  const isAuthenticated = computed(() => !!token.value)
  const isSuperAdmin = computed(() => !!user.value?.is_super_admin)
  const isSchoolAdmin = computed(() => !!user.value?.is_school_admin)
  // 管理后台可见角色：任意管理员
  const isAdmin = computed(
    () => isSuperAdmin.value || isSchoolAdmin.value,
  )
  // 资料是否补全 — 路由守卫据此强制走补全流程。门槛两条：
  //   ① 已绑定学校；② passport 首登的占位用户名(UUID)已被用户认领。
  // 第 ② 条不能省：占位 UUID 会直接出现在个人排行榜与管理员审核页。
  const isProfileComplete = computed(
    () => !!user.value?.school && !user.value?.needs_username,
  )

  async function login(username: string, password: string) {
    await apiLogin(username, password)
    token.value = localStorage.getItem('access_token')
    await loadMe()
  }

  async function loadMe() {
    user.value = await fetchMe()
  }

  // 注册 / 补全资料后直接写入 user（无需再请求 /me/）
  function setUser(u: UserMe) {
    user.value = u
  }

  function logout() {
    apiLogout()
    token.value = null
    user.value = null
  }

  return {
    token,
    user,
    isAuthenticated,
    isSuperAdmin,
    isSchoolAdmin,
    isAdmin,
    isProfileComplete,
    login,
    loadMe,
    setUser,
    logout,
  }
})
