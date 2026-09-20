<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useToast } from '@/composables/useToast'
import LotusPassportEntry from '@/components/auth/LotusPassportEntry.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const toast = useToast()

// 本站账号密码登录（OAuth 首登后在安全页设置密码即可使用）
const showLocal = ref(false)
const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')

function onForgotPassword() {
  toast.info('当前功能开发中')
}

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

      <!-- 主入口：lotus通行证（GitHub / QQ / 邮箱等方式在通行证内选择） -->
      <LotusPassportEntry />

      <!-- 次入口：本站账号密码登录（默认收起） -->
      <div class="local-toggle">
        <span class="toggle-divider" />
        <button class="toggle-link" type="button" @click="showLocal = !showLocal">
          {{ showLocal ? '收起账号密码登录' : '使用本站账号密码登录' }}
        </button>
        <span class="toggle-divider" />
      </div>

      <Transition name="fold">
        <div v-if="showLocal" class="local-form">
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
              <a class="link caption" @click="onForgotPassword">忘记密码？</a>
            </div>
            <button type="submit" class="btn btn-primary btn-block btn-lg" :disabled="loading">
              {{ loading ? '登录中…' : '登录' }}
            </button>
          </form>
          <p class="caption text-tertiary" style="text-align: center; margin-top: var(--space-4)">
            首次使用通行证登录后，在「账号安全」设置密码即可使用本站账号登录
          </p>
        </div>
      </Transition>

      <p class="caption text-tertiary" style="text-align: center; margin-top: var(--space-4)">
        登录即表示同意 <a class="link">用户协议</a> 与 <a class="link">隐私政策</a>
      </p>
    </div>
  </div>
</template>

<style scoped>
.local-toggle {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-top: 18px;
}
.toggle-divider {
  flex: 1;
  height: 1px;
  background: var(--color-divider);
}
.toggle-link {
  border: none;
  background: none;
  padding: 6px 2px;
  font-size: 13px;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: color 0.15s ease;
}
.toggle-link:hover {
  color: var(--color-primary);
}
.local-form {
  margin-top: var(--space-5);
  padding-top: var(--space-5);
  border-top: 1px dashed var(--color-divider);
}
.fold-enter-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}
.fold-enter-from {
  opacity: 0;
  transform: translateY(-6px);
}
.alert-error {
  background: var(--color-danger-subtle);
  border: 1px solid rgba(239, 68, 68, 0.25);
  color: var(--color-danger);
  border-radius: var(--radius-md);
  padding: var(--space-3) var(--space-4);
  font-size: 13px;
}
</style>
