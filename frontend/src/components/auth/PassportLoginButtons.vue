<script setup lang="ts">
import { ref } from 'vue'
import { startPassportOAuth, type PassportProvider } from '@/api'

const loadingProvider = ref<PassportProvider | null>(null)
const error = ref('')

// 微信 OAuth 护照侧暂未启用（返回「当前功能开发中」），先不展示，避免点出 400。
const providers: {
  id: PassportProvider
  name: string
  sub: string
  bg: string
}[] = [
  {
    id: 'github',
    name: 'GitHub',
    sub: '使用 GitHub 账号登录',
    bg: 'linear-gradient(135deg, #24292f, #1b1f23)',
  },
  {
    id: 'qq',
    name: 'QQ',
    sub: '使用 QQ 账号登录',
    bg: 'linear-gradient(135deg, #12b7f5, #0ea6dd)',
  },
]

async function onClick(p: PassportProvider) {
  loadingProvider.value = p
  error.value = ''
  try {
    await startPassportOAuth(p)
    // 浏览器会整页跳转到第三方授权页，不会走到这里
  } catch (e: any) {
    error.value = e?.message || '登录发起失败，请稍后重试'
    loadingProvider.value = null
  }
}
</script>

<template>
  <div class="passport-providers">
    <button
      v-for="p in providers"
      :key="p.id"
      class="pp-btn"
      :style="{ background: p.bg }"
      :disabled="loadingProvider !== null"
      @click="onClick(p.id)"
    >
      <span class="pp-name">{{
        loadingProvider === p.id ? '正在跳转…' : p.name
      }}</span>
      <span class="pp-sub">{{ p.sub }}</span>
    </button>
    <p v-if="error" class="pp-error">{{ error }}</p>
  </div>
</template>

<style scoped>
.passport-providers {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.pp-btn {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  height: 56px;
  padding: 0 20px;
  border: none;
  border-radius: 14px;
  color: #fff;
  cursor: pointer;
  text-align: left;
  transition: opacity 0.15s ease, transform 0.05s ease;
}
.pp-btn:hover:not(:disabled) {
  opacity: 0.92;
}
.pp-btn:active:not(:disabled) {
  transform: scale(0.99);
}
.pp-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.pp-name {
  font-size: 15px;
  font-weight: 600;
}
.pp-sub {
  font-size: 12px;
  opacity: 0.75;
}
.pp-error {
  margin: 4px 2px 0;
  font-size: 13px;
  color: #ef4444;
}
</style>
