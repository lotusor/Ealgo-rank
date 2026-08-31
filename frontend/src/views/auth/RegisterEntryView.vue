<script setup lang="ts">
import { useRouter } from 'vue-router'
import PassportLoginButtons from '@/components/auth/PassportLoginButtons.vue'

const router = useRouter()
</script>

<template>
  <div class="auth-wrap">
    <div style="position: absolute; inset: 0; background: var(--gradient-hero-glow); pointer-events: none" />
    <a class="auth-brand" @click="router.push({ name: 'home' })">
      <span class="brand-mark"><img src="/logo-64.png" alt="E-algo Rank" /></span>
      <span>E-algo <span class="brand-accent">Rank</span></span>
    </a>

    <div class="auth-card">
      <div style="text-align: center; margin-bottom: var(--space-8)">
        <h1 class="h2" style="margin-bottom: var(--space-2)">欢迎来到 E-algo Rank</h1>
        <p class="body-sm text-secondary">登录或注册，开启你的算法竞赛排名之旅</p>
      </div>

      <PassportLoginButtons />

      <div class="divider" />

      <p class="body-sm text-tertiary" style="text-align: center; margin-bottom: var(--space-4)">
        没有 Lotus Passport？可用本地账号登录（仅限管理员 / 兜底场景）。
      </p>
      <div style="display: flex; justify-content: center">
        <button class="btn btn-ghost" @click="router.push({ name: 'login' })">管理员本地登录</button>
      </div>

      <p class="caption text-tertiary" style="text-align: center; margin-top: var(--space-6)">
        登录即表示同意 <a class="link">用户协议</a> 与 <a class="link">隐私政策</a>
      </p>
    </div>
  </div>
</template>
