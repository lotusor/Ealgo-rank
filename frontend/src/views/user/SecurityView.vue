<script setup lang="ts">
import { computed, ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { setPassword } from '@/api'
import { useToast } from '@/composables/useToast'

const auth = useAuthStore()
const toast = useToast()

const hasLocalPassword = computed(() => !!auth.user?.has_usable_password)

const oldPassword = ref('')
const password1 = ref('')
const password2 = ref('')
const loading = ref(false)
const error = ref('')
const success = ref(false)

// 密码强度（仅展示）
const score = computed(() => {
  const p = password1.value
  if (!p) return 0
  let s = 0
  if (p.length >= 8) s++
  if (/[a-z]/.test(p) && /[A-Z]/.test(p)) s++
  if (/\d/.test(p)) s++
  if (/[^A-Za-z0-9]/.test(p)) s++
  return s
})
const strength = computed(() => {
  return [
    { p: 0, text: '', color: 'var(--color-border-strong)' },
    { p: 25, text: '弱', color: '#dc2626' },
    { p: 50, text: '中', color: '#f59e0b' },
    { p: 75, text: '强', color: '#16a34a' },
    { p: 100, text: '很强', color: '#16a34a' },
  ][score.value]
})

function reset() {
  oldPassword.value = ''
  password1.value = ''
  password2.value = ''
  error.value = ''
  success.value = false
}

async function onSubmit() {
  error.value = ''
  success.value = false
  if (hasLocalPassword.value && !oldPassword.value) {
    error.value = '请输入原密码'
    return
  }
  if (!password1.value) {
    error.value = '请输入新密码'
    return
  }
  if (password1.value !== password2.value) {
    error.value = '两次输入的密码不一致'
    return
  }
  loading.value = true
  try {
    const payload: { old_password?: string; new_password1: string; new_password2: string } = {
      new_password1: password1.value,
      new_password2: password2.value,
    }
    if (hasLocalPassword.value) payload.old_password = oldPassword.value
    const res = await setPassword(payload)
    success.value = true
    toast.success(res.detail || '密码已设置')
    reset()
    // 刷新本地状态（has_usable_password 变为 true）
    await auth.loadMe()
  } catch (e: any) {
    error.value =
      e?.response?.data?.old_password?.[0] ||
      e?.response?.data?.new_password2?.[0] ||
      e?.response?.data?.new_password1?.[0] ||
      e?.response?.data?.detail ||
      '操作失败，请稍后重试'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="container-wide" style="max-width: 640px">
    <div class="section-title" style="margin-bottom: var(--space-6)">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /></svg>
      账号安全
    </div>

    <div class="card card-pad">
      <p class="body-sm text-secondary" style="margin-bottom: var(--space-6)">
        <template v-if="hasLocalPassword">
          你已设置本地密码，可在此修改。修改后其他设备的会话将被登出。
        </template>
        <template v-else>
          你当前通过 Lotus Passport 登录，尚未设置本地密码。设置一个本地密码后，
          即使通行证不可用，也能用「用户名 + 密码」直接登录。
        </template>
      </p>

      <div v-if="error" class="alert alert-error" style="margin-bottom: var(--space-4)">{{ error }}</div>
      <div v-if="success" class="alert alert-success" style="margin-bottom: var(--space-4)">
        密码已{{ hasLocalPassword ? '修改' : '设置' }}成功
      </div>

      <form @submit.prevent="onSubmit">
        <div v-if="hasLocalPassword" class="field">
          <label class="field-label">原密码</label>
          <input v-model="oldPassword" class="input" type="password" placeholder="请输入当前密码" autocomplete="current-password" />
        </div>

        <div class="field">
          <label class="field-label">{{ hasLocalPassword ? '新密码' : '设置本地密码' }}</label>
          <input v-model="password1" class="input" type="password" placeholder="至少 8 位，含大小写/数字更佳" autocomplete="new-password" />
        </div>
        <div v-if="password1" style="height: 6px; border-radius: 999px; background: var(--color-bg-inset); overflow: hidden; margin: -8px 0 12px">
          <div :style="{ width: strength.p + '%', height: '100%', background: strength.color, transition: 'width .2s' }" />
        </div>

        <div class="field">
          <label class="field-label">确认密码</label>
          <input v-model="password2" class="input" type="password" placeholder="再次输入密码" autocomplete="new-password" @keyup.enter="onSubmit" />
        </div>

        <button type="submit" class="btn btn-primary btn-block btn-lg" :disabled="loading" style="margin-top: var(--space-4)">
          {{ loading ? '提交中…' : (hasLocalPassword ? '修改密码' : '设置本地密码') }}
        </button>
      </form>
    </div>
  </div>
</template>

<style scoped>
.card-pad { padding: var(--space-8); }
.alert-success {
  background: color-mix(in srgb, var(--color-success, #10b981) 12%, transparent);
  border: 1px solid color-mix(in srgb, var(--color-success, #10b981) 40%, transparent);
  color: var(--color-success, #10b981);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-md);
  font-size: 14px;
}
</style>
