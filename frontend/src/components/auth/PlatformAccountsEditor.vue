<script setup lang="ts">
import { computed, reactive } from 'vue'
import {
  bindPlatformAccount,
  updatePlatformAccount,
  unbindPlatformAccount,
} from '@/api'
import type { PlatformAccount } from '@/api/types'
import { BINDABLE_PLATFORMS, platformClass, platformLabel } from '@/platforms/meta'
import { useToast } from '@/composables/useToast'

const props = defineProps<{ accounts: PlatformAccount[] }>()
const emit = defineEmits<{ (e: 'changed'): void }>()

const toast = useToast()

const accounts = computed(() => props.accounts)

function accountOf(p: string) {
  return accounts.value.find((a) => a.platform === p)
}

// 每个平台的编辑态：null=未编辑，'add'=新增，'edit'=修改
// 用 reactive 而非 ref({})：动态新增 key（editing.value[p]=...）才能触发响应式
const editing = reactive<Record<string, 'add' | 'edit' | null>>({})
const input = reactive<Record<string, string>>({})
const busy = reactive<Record<string, boolean>>({})
const error = reactive<Record<string, string>>({})

function startAdd(p: string) {
  editing[p] = 'add'
  input[p] = ''
  error[p] = ''
}

function startEdit(p: string, a: PlatformAccount) {
  editing[p] = 'edit'
  input[p] = a.handle
  error[p] = ''
}

function cancel(p: string) {
  editing[p] = null
  input[p] = ''
  error[p] = ''
}

async function save(p: string) {
  const handle = (input[p] || '').trim()
  if (!handle) {
    error[p] = '请输入平台账号 ID'
    return
  }
  busy[p] = true
  error[p] = ''
  try {
    const existing = accountOf(p)
    if (existing) {
      await updatePlatformAccount(existing.id, { handle })
      toast.success('平台账号已更新')
    } else {
      await bindPlatformAccount({ platform: p, handle })
      toast.success('平台账号绑定成功')
    }
    editing[p] = null
    input[p] = ''
    emit('changed')
  } catch (e: any) {
    error[p] = extractError(e)
  } finally {
    busy[p] = false
  }
}

async function unbind(p: string, a: PlatformAccount) {
  if (!confirm(`确定解绑 ${a.handle} 吗？解绑后其全部历史参赛记录将被移除且不再计入排名；重新绑定同一 ID 后，历史成绩会由系统自动回补（牛客未打过 rated 的场次除外）。`)) return
  busy[p] = true
  try {
    await unbindPlatformAccount(a.id)
    toast.success('已解绑')
    emit('changed')
  } catch (e: any) {
    error[p] = extractError(e)
  } finally {
    busy[p] = false
  }
}

function extractError(e: any): string {
  const d = e?.response?.data
  if (!d) return e?.message || '操作失败，请稍后重试'
  if (d.errors?.handle) return d.errors.handle
  if (d.errors?.platform) return d.errors.platform
  if (d.detail) return typeof d.detail === 'string' ? d.detail : '操作失败'
  return '操作失败，请稍后重试'
}

function fmtNextEdit(s: string | null) {
  if (!s) return ''
  const d = new Date(s)
  return isNaN(d.getTime()) ? '' : d.toLocaleString('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  })
}
</script>

<template>
  <div class="pa-list">
    <div v-for="p in BINDABLE_PLATFORMS" :key="p.key" class="pa-item">
      <div class="pa-head">
        <span class="platform-tag" :class="platformClass(p.key)">
          {{ platformLabel(p.key) }}
        </span>
        <span class="pa-name">{{ p.label }}</span>
        <span v-if="!accountOf(p.key)" class="badge badge-muted">未绑定</span>
        <span v-else class="badge badge-success">已绑定</span>
      </div>

      <!-- 已绑定展示态 -->
      <div v-if="accountOf(p.key) && editing[p.key] !== 'edit'" class="pa-body">
        <div class="pa-handle">
          <span class="num" style="font-size: 15px; color: var(--color-text-primary)">
            {{ accountOf(p.key)!.handle }}
          </span>
          <span v-if="!accountOf(p.key)!.can_edit_handle" class="caption text-tertiary">
            下次可改：{{ fmtNextEdit(accountOf(p.key)!.handle_next_edit_at) || '一周后' }}
          </span>
        </div>
        <div class="pa-actions">
          <button
            class="btn btn-ghost btn-sm"
            :disabled="!accountOf(p.key)!.can_edit_handle || busy[p.key]"
            @click="startEdit(p.key, accountOf(p.key)!)"
          >
            修改
          </button>
          <button
            class="btn btn-ghost btn-sm text-danger"
            :disabled="busy[p.key]"
            @click="unbind(p.key, accountOf(p.key)!)"
          >
            解绑
          </button>
        </div>
      </div>

      <!-- 新增/编辑态 -->
      <div v-else-if="editing[p.key]" class="pa-body pa-edit">
        <input
          v-model="input[p.key]"
          class="input"
          :placeholder="p.bindHint"
          :disabled="busy[p.key]"
          @keyup.enter="save(p.key)"
        />
        <div class="caption text-tertiary">{{ p.bindGuide }}</div>
        <div v-if="error[p.key]" class="field-hint" style="color: var(--color-danger)">{{ error[p.key] }}</div>
        <div class="pa-actions">
          <button class="btn btn-ghost btn-sm" :disabled="busy[p.key]" @click="cancel(p.key)">取消</button>
          <button class="btn btn-primary btn-sm" :disabled="busy[p.key]" @click="save(p.key)">
            {{ busy[p.key] ? '保存中…' : '保存' }}
          </button>
        </div>
      </div>

      <!-- 未绑定引导 -->
      <div v-else class="pa-body pa-empty">
        <div style="display: flex; flex-direction: column; gap: 2px; flex: 1">
          <span class="caption text-tertiary">{{ p.bindHint }}</span>
          <span class="caption text-tertiary" style="font-size: 12px">{{ p.bindGuide }}</span>
        </div>
        <button class="btn btn-secondary btn-sm" @click="startAdd(p.key)">绑定账号</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.pa-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
.pa-item {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  background: var(--color-bg-elevated);
}
.pa-head {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-3);
}
.pa-name {
  font-weight: 600;
  font-size: 14px;
  color: var(--color-text-primary);
  flex: 1;
}
.pa-body {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-wrap: wrap;
}
.pa-handle {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
  min-width: 160px;
}
.pa-actions {
  display: flex;
  gap: var(--space-2);
}
.pa-edit {
  flex-direction: column;
  align-items: stretch;
}
.pa-empty {
  justify-content: space-between;
}
.text-danger {
  color: var(--color-danger);
}
</style>
