<script setup lang="ts">
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { publishNotification } from '@/api'
import { useToast } from '@/composables/useToast'

const auth = useAuthStore()
const toast = useToast()

const title = ref('')
const message = ref('')
const link = ref('')
// broadcast = 全站广播；specific = 指定 user_ids
const mode = ref<'broadcast' | 'specific'>('broadcast')
const userIdsRaw = ref('')
const sending = ref(false)
const lastCount = ref<number | null>(null)

async function send() {
  if (!title.value.trim()) {
    toast.error('请填写站内信标题')
    return
  }
  const payload: {
    title: string
    message?: string
    link?: string
    user_ids?: number[]
  } = {
    title: title.value.trim(),
    message: message.value,
    link: link.value,
  }
  if (mode.value === 'specific') {
    const ids = userIdsRaw.value
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean)
      .map(Number)
      .filter((n) => !Number.isNaN(n))
    if (!ids.length) {
      toast.error('请填写至少一个有效用户 ID（逗号分隔）')
      return
    }
    payload.user_ids = ids
  }

  sending.value = true
  try {
    const res = await publishNotification(payload)
    lastCount.value = res.count
    toast.success(`已发送给 ${res.count} 位用户`)
    title.value = ''
    message.value = ''
    link.value = ''
    userIdsRaw.value = ''
    mode.value = 'broadcast'
  } catch (e: any) {
    const detail = e?.response?.data?.detail || '发布失败，请稍后重试'
    toast.error(typeof detail === 'string' ? detail : '发布失败')
  } finally {
    sending.value = false
  }
}
</script>

<template>
  <div class="page">
    <header class="page-head">
      <div>
        <h1>群发站内信</h1>
        <p class="page-sub">仅超级管理员可发布。可全站广播，或指定接收用户。</p>
      </div>
    </header>

    <div class="card publish-card">
      <div class="form-group">
        <label>标题 <span class="req">*</span></label>
        <input v-model="title" class="input" placeholder="例如：系统维护通知" maxlength="120" />
      </div>

      <div class="form-group">
        <label>正文</label>
        <textarea v-model="message" class="input" rows="4" placeholder="站内信内容（可选）"></textarea>
      </div>

      <div class="form-group">
        <label>跳转链接</label>
        <input v-model="link" class="input" placeholder="可选，如 /admin/applications/12" />
      </div>

      <div class="form-group">
        <label>接收范围</label>
        <div class="radio-row">
          <label class="radio">
            <input type="radio" value="broadcast" v-model="mode" /> 全站广播（所有用户）
          </label>
          <label class="radio">
            <input type="radio" value="specific" v-model="mode" /> 指定用户
          </label>
        </div>
        <input
          v-if="mode === 'specific'"
          v-model="userIdsRaw"
          class="input"
          placeholder="用户 ID，多个用逗号分隔，如 12,34,56"
        />
      </div>

      <div class="actions">
        <button class="btn btn-primary" :disabled="sending" @click="send">
          {{ sending ? '发送中…' : '发布站内信' }}
        </button>
        <span v-if="lastCount !== null" class="sent-hint">上次发送：{{ lastCount }} 位用户</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.publish-card {
  max-width: 640px;
}
.form-group {
  margin-bottom: var(--space-5);
}
.form-group label {
  display: block;
  margin-bottom: var(--space-2);
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
}
.req {
  color: var(--color-danger);
}
.input {
  width: 100%;
}
.radio-row {
  display: flex;
  gap: var(--space-5);
}
.radio {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  font-weight: 500;
  cursor: pointer;
}
.actions {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}
.sent-hint {
  font-size: 13px;
  color: var(--color-text-muted);
}
</style>
