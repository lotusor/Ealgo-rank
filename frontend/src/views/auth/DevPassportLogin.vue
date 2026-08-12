<script setup lang="ts">
const PASSPORT_URL = import.meta.env.VITE_PASSPORT_URL as string | undefined

async function goDevPassport() {
  if (!PASSPORT_URL) {
    window.alert('未配置 VITE_PASSPORT_URL')
    return
  }
  try {
    const resp = await fetch(`${PASSPORT_URL}/api/v1/dev/login/`)
    if (!resp.ok) throw new Error(`dev-login HTTP ${resp.status}（生产环境该端点已禁用）`)
    const d = await resp.json()
    if (!d.access || !d.refresh) throw new Error('dev-login 未返回令牌')
    const frag = new URLSearchParams({
      access_token: d.access,
      token_type: d.token_type || 'Bearer',
      refresh_token: d.refresh,
      passport_user_id: d.passport_user_id || '',
    })
    window.location.href = `${window.location.origin}/auth/callback#${frag.toString()}`
  } catch (e) {
    window.alert(`模拟通行证登录失败：${e instanceof Error ? e.message : '请重试'}`)
  }
}
</script>

<template>
  <div style="text-align: center; margin-top: var(--space-4)">
    <button class="btn btn-ghost btn-sm" @click="goDevPassport">[DEV] 模拟通行证登录（跳过 GitHub）</button>
  </div>
</template>
