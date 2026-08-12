<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useToast } from '@/composables/useToast'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const toast = useToast()

const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')

async function onSubmit() {
  error.value = ''
  if (!username.value || !password.value) {
    error.value = '请输入用户名和密码'
    return
  }
  loading.value = true
  try {
    await auth.login(username.value, password.value)
    const redirect = (route.query.redirect as string) || (auth.isAdmin ? '/dashboard' : '/u/rankings')
    toast.success('登录成功')
    router.push(redirect)
  } catch (e: any) {
    error.value = e?.response?.data?.detail || '登录失败，请检查用户名或密码'
  } finally {
    loading.value = false
  }
}

function goPassport() {
  router.push({ name: 'register' })
}
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
        <h1 class="h2" style="margin-bottom: var(--space-2)">欢迎回到 E-algo Rank</h1>
        <p class="body-sm text-secondary">登录以查看你的竞赛排名与成绩</p>
      </div>

      <button class="btn btn-lg btn-block" style="background: linear-gradient(135deg, #7c3aed, #6366f1); color: #fff; height: 52px; margin-bottom: var(--space-5)" @click="goPassport">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" /></svg>
        使用 Lotus Passport 登录
      </button>

      <div style="display: flex; align-items: center; gap: var(--space-4); margin-bottom: var(--space-6)">
        <div style="flex: 1; height: 1px; background: var(--color-divider)" />
        <span class="caption text-tertiary">或使用本地账号</span>
        <div style="flex: 1; height: 1px; background: var(--color-divider)" />
      </div>

      <div v-if="error" class="alert alert-error" style="margin-bottom: var(--space-4)">{{ error }}</div>

      <form @submit.prevent="onSubmit">
        <div class="field">
          <label class="field-label">用户名</label>
          <input v-model="username" class="input" type="text" placeholder="用户名 / 学号" autocomplete="username" />
        </div>
        <div class="field">
          <label class="field-label">密码</label>
          <input v-model="password" class="input" type="password" placeholder="请输入密码" autocomplete="current-password" @keyup.enter="onSubmit" />
        </div>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-5)">
          <label style="display: flex; align-items: center; gap: var(--space-2); font-size: 13px; color: var(--color-text-secondary); cursor: pointer">
            <input type="checkbox" checked style="accent-color: var(--color-primary)" /> 记住我
          </label>
          <a class="link caption">忘记密码？</a>
        </div>
        <button type="submit" class="btn btn-primary btn-block btn-lg" :disabled="loading">
          {{ loading ? '登录中…' : '登录' }}
        </button>
      </form>

      <p class="caption text-tertiary" style="text-align: center; margin-top: var(--space-6)">
        还没有账号？<a class="link" @click="goPassport">通过 Lotus Passport 注册</a>
      </p>
    </div>
  </div>
</template>
