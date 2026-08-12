<script setup lang="ts">
import { useRouter } from 'vue-router'
import { defineAsyncComponent } from 'vue'

const router = useRouter()
const PASSPORT_URL = import.meta.env.VITE_PASSPORT_URL as string | undefined

async function goPassport() {
  if (!PASSPORT_URL) {
    router.push({
      name: 'auth-callback',
      query: { mock: '1', passport_user_id: 'dev_demo', username: 'dev_passport_user' },
    })
    return
  }
  const cb = `${window.location.origin}/auth/callback`
  try {
    const resp = await fetch(`${PASSPORT_URL}/api/v1/oauth/github/login/?redirect_uri=${encodeURIComponent(cb)}`)
    const data = await resp.json()
    if (data.authorize_url) {
      window.location.href = data.authorize_url
    } else {
      throw new Error(data?.error?.message || '未返回授权地址')
    }
  } catch (e) {
    window.alert(`跳转通行证失败：${e instanceof Error ? e.message : '请重试'}`)
  }
}

const DevPassportLogin = import.meta.env.DEV
  ? defineAsyncComponent(() => import('./DevPassportLogin.vue'))
  : null
</script>

<template>
  <div class="auth-wrap">
    <div style="position: absolute; inset: 0; background: var(--gradient-hero-glow); pointer-events: none" />
    <a class="auth-brand" @click="router.push({ name: 'home' })">
      <span class="brand-mark"><svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.5"><path d="M3 17l4-4 4 4 4-8 4 8" /></svg></span>
      <span>E-algo <span class="brand-accent">Rank</span></span>
    </a>

    <div class="auth-card">
      <div style="text-align: center; margin-bottom: var(--space-8)">
        <h1 class="h2" style="margin-bottom: var(--space-2)">欢迎来到 E-algo Rank</h1>
        <p class="body-sm text-secondary">登录或注册，开启你的算法竞赛排名之旅</p>
      </div>

      <button class="btn btn-lg btn-block" style="background: linear-gradient(135deg, #7c3aed, #6366f1); color: #fff; height: 52px" @click="goPassport">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" /></svg>
        使用 Lotus Passport 登录
      </button>

      <div class="divider" />

      <p class="body-sm text-tertiary" style="text-align: center; margin-bottom: var(--space-4)">
        没有 Lotus Passport？可用本地账号登录（仅限管理员 / 兜底场景）。
      </p>
      <div style="display: flex; justify-content: center">
        <button class="btn btn-ghost" @click="router.push({ name: 'login' })">管理员本地登录</button>
      </div>

      <component :is="DevPassportLogin" v-if="DevPassportLogin" />

      <p class="caption text-tertiary" style="text-align: center; margin-top: var(--space-6)">
        登录即表示同意 <a class="link">用户协议</a> 与 <a class="link">隐私政策</a>
      </p>
    </div>
  </div>
</template>
