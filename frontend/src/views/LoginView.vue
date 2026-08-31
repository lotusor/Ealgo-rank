<script setup lang="ts">
import LotusPassportEntry from '@/components/auth/LotusPassportEntry.vue'
</script>

<template>
  <div class="auth-wrap">
    <div style="position: absolute; inset: 0; background: var(--gradient-hero-glow); pointer-events: none" />
    <a class="auth-brand" href="/u">
      <span class="brand-mark"><img src="/logo-64.png" alt="E-algo Rank" /></span>
      <span>E-algo <span class="brand-accent">Rank</span></span>
    </a>

    <div class="auth-card">
      <div style="text-align: center; margin-bottom: var(--space-8)">
        <h1 class="h2" style="margin-bottom: var(--space-2)">欢迎回到 E-algo Rank</h1>
        <p class="body-sm text-secondary">登录以查看你的竞赛排名与成绩</p>
      </div>

      <!-- 登录完全交给莲花通行证：方式（GitHub / QQ / 邮箱等）在通行证内选择 -->
      <LotusPassportEntry />

      <p class="caption text-tertiary" style="text-align: center; margin-top: var(--space-5)">
        登录过程由莲花通行证统一提供保护
      </p>
      <p class="caption text-tertiary" style="text-align: center; margin-top: var(--space-4)">
        登录即表示同意 <a class="link">用户协议</a> 与 <a class="link">隐私政策</a>
      </p>
    </div>
  </div>
</template>
