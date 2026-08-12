<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import type { UserMe } from '@/api/types'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const loading = ref(true)
const failed = ref(false)
const hint = ref('正在与 Lotus Passport 完成身份验证，请稍候…')

function goTarget() {
  if (auth.isProfileComplete) {
    router.replace(auth.isAdmin ? { name: 'dashboard' } : { name: 'rankings' })
  } else {
    router.replace({ name: 'register-complete' })
  }
}

onMounted(async () => {
  const q = route.query as Record<string, string>

  if (q.mock) {
    const fake: UserMe = {
      id: -1,
      username: q.username || 'dev_passport_user',
      email: '',
      real_name: '',
      student_no: '',
      role: 'normal',
      role_display: '普通用户',
      school: null,
      school_bound_at: null,
      platform_accounts: [],
      is_super_admin: false,
      is_school_admin: false,
      needs_username: false,
      date_joined: '',
    }
    auth.token = 'mock'
    auth.setUser(fake)
    loading.value = false
    router.replace({ name: 'register-complete' })
    return
  }

  const hash = window.location.hash.replace(/^#/, '')
  const frag = new URLSearchParams(hash)
  const access = frag.get('access_token')
  const refresh = frag.get('refresh_token')

  if (!access || !refresh) {
    loading.value = false
    failed.value = true
    hint.value = '授权回调异常，可能是授权已过期或被拒绝。'
    return
  }

  localStorage.setItem('access_token', access)
  localStorage.setItem('refresh_token', refresh)
  localStorage.setItem('auth_source', 'passport')
  history.replaceState(null, '', window.location.pathname + window.location.search)
  auth.token = access
  try {
    await auth.loadMe()
  } catch {
    auth.logout()
    loading.value = false
    failed.value = true
    hint.value = '登录态校验失败，请重新登录。'
    return
  }
  loading.value = false
  goTarget()
})
</script>

<template>
  <div class="auth-wrap">
    <div style="position: absolute; inset: 0; background: var(--gradient-hero-glow); pointer-events: none" />
    <a class="auth-brand" @click="router.push({ name: 'home' })">
      <span class="brand-mark"><svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.5"><path d="M3 17l4-4 4 4 4-8 4 8" /></svg></span>
      <span>E-algo <span class="brand-accent">Rank</span></span>
    </a>

    <div class="auth-card" style="max-width: 440px; text-align: center">
      <div v-if="loading">
        <div style="width: 56px; height: 56px; border: 3px solid var(--color-primary-subtle, rgba(99,102,241,.3)); border-top-color: var(--color-primary); border-radius: var(--radius-full); margin: 0 auto var(--space-6); animation: spin .8s linear infinite" />
        <h2 class="h3" style="margin-bottom: var(--space-2)">正在处理认证回调</h2>
        <p class="body-sm text-secondary">{{ hint }}</p>
      </div>

      <div v-else-if="!failed">
        <div style="width: 64px; height: 64px; border-radius: var(--radius-full); background: var(--color-success-subtle, rgba(16,185,129,.12)); display: flex; align-items: center; justify-content: center; margin: 0 auto var(--space-5)">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="var(--color-success, #10b981)" stroke-width="2.5"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" /><path d="M22 4L12 14.01l-3-3" /></svg>
        </div>
        <h2 class="h3" style="margin-bottom: var(--space-2)">认证成功</h2>
        <p class="body-sm text-secondary" style="margin-bottom: var(--space-6)">已通过 Lotus Passport 完成身份验证，即将跳转…</p>
        <button class="btn btn-primary btn-block btn-lg" @click="goTarget">进入首页</button>
      </div>

      <div v-else>
        <div style="width: 64px; height: 64px; border-radius: var(--radius-full); background: var(--color-danger-subtle, rgba(239,68,68,.12)); display: flex; align-items: center; justify-content: center; margin: 0 auto var(--space-5)">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="var(--color-danger, #ef4444)" stroke-width="2"><circle cx="12" cy="12" r="10" /><path d="M15 9l-6 6M9 9l6 6" /></svg>
        </div>
        <h2 class="h3" style="margin-bottom: var(--space-2)">认证失败</h2>
        <p class="body-sm text-secondary" style="margin-bottom: var(--space-6)">{{ hint }}</p>
        <button class="btn btn-primary btn-block btn-lg" @click="router.push({ name: 'register' })">重新登录</button>
      </div>
    </div>
  </div>
</template>
