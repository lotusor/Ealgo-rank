<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { checkUsernameAvailable, listSchools, register, updateMe } from '@/api'
import type { School, UserMe } from '@/api/types'
import { useToast } from '@/composables/useToast'

const props = defineProps<{
  mode: 'create' | 'complete'
  prefill?: UserMe | null
}>()
const emit = defineEmits<{ (e: 'done', user: UserMe): void }>()

const router = useRouter()
const auth = useAuthStore()
const toast = useToast()

const needsUsername = computed(() => props.mode === 'complete' && !!props.prefill?.needs_username)
const username = ref(needsUsername.value ? '' : (props.prefill?.username ?? ''))
const password = ref('')
const password2 = ref('')
const schoolCode = ref<string | null>(null)
const realName = ref(props.prefill?.real_name ?? '')
const studentNo = ref(props.prefill?.student_no ?? '')

const schools = ref<School[]>([])
const loading = ref(false)
const error = ref('')

// ---------- 用户名实时查重 ----------
type UsernameState = 'idle' | 'checking' | 'ok' | 'bad'
const usernameState = ref<UsernameState>('idle')
const usernameHint = ref('')
const usernameEditable = computed(() => props.mode === 'create' || needsUsername.value)

const CHECK_DEBOUNCE_MS = 400
let checkTimer: ReturnType<typeof setTimeout> | null = null
let checkSeq = 0

function resetUsernameCheck(state: UsernameState = 'idle', hint = '') {
  if (checkTimer) {
    clearTimeout(checkTimer)
    checkTimer = null
  }
  checkSeq += 1
  usernameState.value = state
  usernameHint.value = hint
}

watch(username, (val) => {
  if (!usernameEditable.value) return
  const v = (val || '').trim()
  if (!v) return resetUsernameCheck()
  if (v.length < 3 || v.length > 20) {
    return resetUsernameCheck('bad', '用户名需为 3-20 个字符')
  }
  resetUsernameCheck('checking', '检查中…')
  const seq = checkSeq
  checkTimer = setTimeout(async () => {
    try {
      const res = await checkUsernameAvailable(v)
      if (seq !== checkSeq) return
      usernameState.value = res.available ? 'ok' : 'bad'
      usernameHint.value = res.available ? '该用户名可用' : res.reason
    } catch {
      if (seq !== checkSeq) return
      usernameState.value = 'idle'
      usernameHint.value = '无法校验用户名，提交时会再次核对'
    }
  }, CHECK_DEBOUNCE_MS)
})

onUnmounted(() => {
  if (checkTimer) clearTimeout(checkTimer)
})

const usernameHintColor = computed(() => {
  if (usernameState.value === 'ok') return 'var(--color-success, #16a34a)'
  if (usernameState.value === 'bad') return 'var(--color-danger, #dc2626)'
  return undefined
})

onMounted(async () => {
  try {
    const res = await listSchools({ page_size: 200 })
    schools.value = res.results
  } catch {
    toast.error('学校列表加载失败，请稍后重试')
  }
})

// 密码强度（仅 create 模式展示）
const passwordScore = computed(() => {
  const p = password.value
  if (!p) return 0
  let s = 0
  if (p.length >= 8) s++
  if (/[a-z]/.test(p) && /[A-Z]/.test(p)) s++
  if (/\d/.test(p)) s++
  if (/[^A-Za-z0-9]/.test(p)) s++
  return s
})
const passwordStrength = computed(() => {
  const map = [
    { p: 0, text: '', color: 'var(--color-border-strong)' },
    { p: 25, text: '弱', color: '#dc2626' },
    { p: 50, text: '中', color: '#f59e0b' },
    { p: 75, text: '强', color: '#16a34a' },
    { p: 100, text: '很强', color: '#16a34a' },
  ]
  return map[passwordScore.value]
})

function extractError(e: any): string {
  const d = e?.response?.data
  if (!d) return e?.message || '请求失败，请稍后重试'
  if (typeof d === 'string') return d
  if (d.detail) return d.detail
  const msgs: string[] = []
  for (const k in d) {
    const v = d[k]
    if (Array.isArray(v)) msgs.push(`${k}：${v.join('；')}`)
    else if (typeof v === 'string') msgs.push(`${k}：${v}`)
  }
  return msgs.join('  ') || '提交失败'
}

async function onSubmit() {
  error.value = ''
  if (usernameEditable.value && !username.value.trim()) {
    error.value = needsUsername.value ? '请设置一个用户名（它会显示在排行榜上）' : '请输入用户名'
    return
  }
  if (usernameEditable.value && usernameState.value === 'bad') {
    error.value = usernameHint.value || '用户名不可用，请更换'
    return
  }
  if (props.mode === 'create') {
    if (!password.value) {
      error.value = '请输入密码'
      return
    }
    if (password.value !== password2.value) {
      error.value = '两次输入的密码不一致'
      return
    }
  }
  if (!schoolCode.value) {
    error.value = '请选择所属学校'
    return
  }

  loading.value = true
  try {
    if (props.mode === 'create') {
      const res = await register({
        username: username.value.trim(),
        password: password.value,
        password2: password2.value,
        real_name: realName.value.trim() || undefined,
        student_no: studentNo.value.trim() || undefined,
        school_code: schoolCode.value ?? undefined,
      })
      auth.token = localStorage.getItem('access_token')
      auth.setUser(res.user)
      toast.success('注册成功')
      emit('done', res.user)
    } else {
      const user = await updateMe({
        username: needsUsername.value ? username.value.trim() || undefined : undefined,
        real_name: realName.value.trim() || undefined,
        student_no: studentNo.value.trim() || undefined,
        school_code: schoolCode.value ?? undefined,
      })
      auth.setUser(user)
      toast.success('资料已保存')
      emit('done', user)
    }
  } catch (e: any) {
    error.value = extractError(e)
  } finally {
    loading.value = false
  }
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
        <h2 class="h3" style="margin-bottom: var(--space-2)">{{ props.mode === 'create' ? '创建账号' : '补全资料' }}</h2>
        <p class="body-sm text-secondary">{{ props.mode === 'create' ? '填写基础信息，开启你的排名之旅' : '完善身份信息，纳入学校排名体系' }}</p>
      </div>

      <div v-if="error" class="alert alert-error" style="margin-bottom: var(--space-4)">{{ error }}</div>

      <form @submit.prevent="onSubmit">
        <div v-if="usernameEditable" class="field">
          <label class="field-label">用户名</label>
          <input
            v-model="username"
            class="input"
            type="text"
            placeholder="3-20 个字符，支持中文/字母/数字/_-."
            :maxlength="20"
            :style="usernameState === 'bad' ? 'border-color: var(--color-danger)' : ''"
          />
          <div v-if="needsUsername && usernameState === 'idle' && !usernameHint" class="field-hint">
            这个名字会显示在排行榜上，设置后不可修改
          </div>
          <div v-else-if="usernameHint" class="field-hint" :style="{ color: usernameHintColor }">{{ usernameHint }}</div>
        </div>
        <div v-else class="field">
          <label class="field-label">用户名</label>
          <input class="input" :value="props.prefill?.username" readonly placeholder="通行证账号" />
        </div>

        <template v-if="props.mode === 'create'">
          <div class="field">
            <label class="field-label">密码</label>
            <input v-model="password" class="input" type="password" placeholder="至少 8 位，含大小写/数字更佳" />
          </div>
          <div v-if="password" style="height: 6px; border-radius: 999px; background: var(--color-bg-inset); overflow: hidden; margin: -8px 0 12px">
            <div :style="{ width: passwordStrength.p + '%', height: '100%', background: passwordStrength.color, transition: 'width .2s' }" />
          </div>
          <div class="field">
            <label class="field-label">确认密码</label>
            <input v-model="password2" class="input" type="password" placeholder="再次输入密码" autocomplete="new-password" />
          </div>
        </template>

        <div class="field">
          <label class="field-label">所属学校</label>
          <select v-model="schoolCode" class="select">
            <option :value="null" disabled>选择你的学校</option>
            <option v-for="s in schools" :key="s.id" :value="s.code">{{ s.name }}</option>
          </select>
        </div>

        <div class="field-grid">
          <div class="field">
            <label class="field-label">真实姓名（选填）</label>
            <input v-model="realName" class="input" placeholder="选填" />
          </div>
          <div class="field">
            <label class="field-label">学号（选填）</label>
            <input v-model="studentNo" class="input" placeholder="选填" />
          </div>
        </div>

        <button type="submit" class="btn btn-primary btn-block btn-lg" :disabled="loading" style="margin-top: var(--space-4)">
          {{ loading ? '提交中…' : props.mode === 'create' ? '注册并继续' : '保存并继续' }}
        </button>
      </form>
    </div>
  </div>
</template>

<style scoped>
.field-grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-3); }
@media (max-width: 560px) { .field-grid { grid-template-columns: 1fr; } }
</style>
