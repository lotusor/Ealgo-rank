import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { fetchMe, login as apiLogin } from '@/api'
import type { UserMe } from '@/api/types'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('access_token'))
  const authSource = ref<string>(localStorage.getItem('auth_source') || 'local')
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
    authSource.value = localStorage.getItem('auth_source') || 'local'
    await loadMe()
  }

  async function loadMe() {
    user.value = await fetchMe()
  }

  // passport 回调 / 注册成功后写入完整登录态（token + source + user）
  function setSession(access: string, refresh: string, source: string) {
    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)
    localStorage.setItem('auth_source', source)
    token.value = access
    authSource.value = source
  }

  // 注册 / 补全资料后直接写入 user（无需再请求 /me/）
  function setUser(u: UserMe) {
    user.value = u
  }

  async function logout() {
    // 尽力吊销 passport 侧 jti（离线验签不查黑名单，显式吊销更稳妥）
    const source = authSource.value
    const pp = import.meta.env.VITE_PASSPORT_URL as string | undefined
    if (source === 'passport' && token.value && pp) {
      try {
        await fetch(`${pp}/api/v1/logout/`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${token.value}` },
        })
      } catch {
        /* 吊销失败不阻断本地清理 */
      }
    }
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('auth_source')
    token.value = null
    authSource.value = 'local'
    user.value = null
  }

  return {
    token,
    authSource,
    user,
    isAuthenticated,
    isSuperAdmin,
    isSchoolAdmin,
    isAdmin,
    isProfileComplete,
    login,
    loadMe,
    setSession,
    setUser,
    logout,
  }
})
