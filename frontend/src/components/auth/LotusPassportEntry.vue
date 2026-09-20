<script setup lang="ts">
/**
 * lotus通行证统一登录入口（provider 无关）。
 * 点击后整页跳转 passport 统一登录页，登录方式（GitHub / QQ / 邮箱等）
 * 全部在通行证侧选择，完成后携授权码回本站完成登录。
 */
import { ref } from 'vue'
import { startPassportGenericLogin } from '@/api'

const loading = ref(false)
const error = ref('')

async function onLogin() {
  if (loading.value) return
  loading.value = true
  error.value = ''
  try {
    await startPassportGenericLogin()
    // 成功时整页跳走，不会回到这里
  } catch (e: any) {
    error.value = e?.message || '无法发起通行证登录，请稍后重试'
    loading.value = false
  }
}
</script>

<template>
  <div class="lotus-wrap">
    <button class="lotus-entry" :disabled="loading" @click="onLogin">
      <span class="lotus-icon-ring">
        <img class="lotus-icon" src="/lotus-icon.png" alt="Lotus Passport" draggable="false" />
      </span>
      <span class="lotus-texts">
        <span class="lotus-title">
          {{ loading ? '正在前往lotus通行证…' : '使用 Lotus 通行证登录' }}
        </span>
        <span class="lotus-sub">统一身份认证 · GitHub / QQ / 邮箱等方式在通行证内选择</span>
      </span>
      <svg
        class="lotus-arrow"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
      >
        <path d="M5 12h14" />
        <path d="M13 6l6 6-6 6" />
      </svg>
    </button>
    <p v-if="error" class="lotus-error">{{ error }}</p>
  </div>
</template>

<style scoped>
.lotus-wrap {
  animation: lotus-fade-up 0.5s cubic-bezier(0.22, 1, 0.36, 1) backwards;
}
.lotus-entry {
  position: relative;
  display: flex;
  align-items: center;
  gap: 16px;
  width: 100%;
  min-height: 72px;
  padding: 14px 18px;
  border: 1px solid var(--color-border);
  border-radius: 18px;
  background:
    linear-gradient(135deg, rgba(99, 102, 241, 0.10), rgba(6, 182, 212, 0.06)),
    var(--color-bg-elevated);
  color: var(--color-text-primary);
  cursor: pointer;
  text-align: left;
  overflow: hidden;
  transition:
    transform 0.18s cubic-bezier(0.22, 1, 0.36, 1),
    box-shadow 0.18s ease,
    border-color 0.18s ease;
}
/* 掠过的高光 */
.lotus-entry::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(115deg, transparent 30%, rgba(255, 255, 255, 0.08) 45%, transparent 60%);
  transform: translateX(-120%);
  transition: transform 0.6s ease;
  pointer-events: none;
}
.lotus-entry:hover:not(:disabled) {
  transform: translateY(-2px);
  border-color: var(--color-primary);
  box-shadow: 0 10px 30px rgba(99, 102, 241, 0.25), var(--shadow-glow);
}
.lotus-entry:hover:not(:disabled)::after {
  transform: translateX(120%);
}
.lotus-entry:active:not(:disabled) {
  transform: translateY(0) scale(0.995);
}
.lotus-entry:disabled {
  opacity: 0.7;
  cursor: progress;
}
.lotus-entry:focus-visible {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.3);
}

.lotus-icon-ring {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  padding: 3px;
  flex-shrink: 0;
  background: conic-gradient(from 210deg, #6366f1, #06b6d4, #d9543f, #6366f1);
}
.lotus-icon {
  width: 100%;
  height: 100%;
  border-radius: 9px;
  object-fit: cover;
  display: block;
  transition: transform 0.25s ease;
}
.lotus-entry:hover:not(:disabled) .lotus-icon {
  transform: scale(1.06);
}

.lotus-texts {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
  flex: 1;
}
.lotus-title {
  font-size: 15px;
  font-weight: 700;
}
.lotus-sub {
  font-size: 12px;
  color: var(--color-text-tertiary);
  line-height: 1.4;
}

.lotus-arrow {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  color: var(--color-text-tertiary);
  transition: transform 0.18s ease, color 0.18s ease;
}
.lotus-entry:hover:not(:disabled) .lotus-arrow {
  transform: translateX(4px);
  color: var(--color-primary);
}

.lotus-error {
  margin-top: 10px;
  font-size: 13px;
  color: var(--color-danger);
}

@keyframes lotus-fade-up {
  from {
    opacity: 0;
    transform: translateY(14px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
@media (prefers-reduced-motion: reduce) {
  .lotus-wrap,
  .lotus-entry,
  .lotus-entry::after,
  .lotus-icon,
  .lotus-arrow {
    animation: none !important;
    transition: none !important;
  }
}
</style>
