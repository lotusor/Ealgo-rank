<script setup lang="ts">
import { ref, computed, onMounted, useId, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
import Dialog from '@/components/ui/Dialog.vue'
import {
  listAnnouncements,
  createAnnouncement,
  updateAnnouncement,
  deleteAnnouncement,
} from '@/api'
import type { Announcement } from '@/api/types'

/**
 * 系统公告模块（任务1）：页面内容区左上角的公告条。
 * 数据来源为后端公告接口（Announcement 模型 + 超管发布接口），
 * 不再用 localStorage 持久化（前端的过渡方案已废弃）。
 */

interface EditableAnnouncement extends Partial<Announcement> {}

const auth = useAuthStore()

const list = ref<Announcement[]>([])
const dismissed = ref<Set<number>>(new Set())
const editorOpen = ref(false)
const editing = ref<EditableAnnouncement | null>(null)
const pending = ref(false)
const editorError = ref('')
const editorId = useId()

watch(editorOpen, (open) => {
  if (!open) editing.value = null
})

const LEVEL_CLS: Record<Announcement['level'], string> = {
  info: 'badge-info',
  success: 'badge-success',
  warning: 'badge-warning',
  danger: 'badge-danger',
}

async function load() {
  try {
    list.value = await listAnnouncements()
  } catch {
    list.value = []
  }
}

const visible = computed(() =>
  list.value
    .filter((a) => !dismissed.value.has(a.id))
    .sort((a, b) => Number(b.pinned) - Number(a.pinned)),
)
const current = computed(() => visible.value[0] || null)

function dismiss() {
  if (current.value) {
    dismissed.value.add(current.value.id)
    dismissed.value = new Set(dismissed.value)
  }
}

function openEditor(a?: Announcement) {
  if (pending.value || editorOpen.value) return
  editing.value = a
    ? { ...a }
    : { title: '', content: '', level: 'info', pinned: false, is_active: true }
  editorError.value = ''
  editorOpen.value = true
}

function closeEditor() {
  if (pending.value) return
  editorOpen.value = false
}

async function saveEditor() {
  const e = editing.value
  if (pending.value || !e) return
  if (!e.title?.trim() || !e.content?.trim()) {
    editorError.value = '请填写标题和内容'
    return
  }
  const payload = {
    title: e.title.trim(),
    content: e.content.trim(),
    level: e.level ?? 'info',
    pinned: Boolean(e.pinned),
    is_active: e.is_active ?? true,
  }
  pending.value = true
  editorError.value = ''
  let saved = false
  try {
    if (e.id != null) {
      await updateAnnouncement(e.id, payload)
    } else {
      await createAnnouncement(payload)
    }
    // 刷新期间也保持锁定，避免迟到响应关闭随后打开的编辑器。
    await load()
    saved = true
  } catch {
    editorError.value = '保存公告失败，请重试'
  } finally {
    pending.value = false
  }
  if (saved) closeEditor()
}

async function removeEditor() {
  const e = editing.value
  if (pending.value || e?.id == null) return
  pending.value = true
  editorError.value = ''
  let removed = false
  try {
    await deleteAnnouncement(e.id)
    await load()
    removed = true
  } catch {
    editorError.value = '删除公告失败，请重试'
  } finally {
    pending.value = false
  }
  if (removed) closeEditor()
}

onMounted(load)
</script>

<template>
  <div v-if="current" class="announce" :class="'announce-' + current.level">
    <svg class="announce-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <path d="M3 11l18-5v12L3 14v-3z" />
      <path d="M11.6 16.8a3 3 0 1 1-5.8-1.6" />
    </svg>
    <div class="announce-body">
      <div class="announce-title">
        <span class="badge" :class="LEVEL_CLS[current.level]">公告</span>
        {{ current.title }}
      </div>
      <div class="announce-text">{{ current.content }}</div>
    </div>
    <button
      v-if="auth.isSuperAdmin"
      class="announce-act"
      title="新建公告"
      :disabled="pending"
      @click="openEditor()"
    >
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M12 5v14M5 12h14" />
      </svg>
    </button>
    <button
      v-if="auth.isSuperAdmin"
      class="announce-act"
      title="管理公告"
      :disabled="pending"
      @click="openEditor(current)"
    >
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
        <path d="M18.5 2.5a2.12 2.12 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
      </svg>
    </button>
    <button class="announce-act" title="忽略" @click="dismiss">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M18 6L6 18M6 6l12 12" />
      </svg>
    </button>
  </div>

  <div v-else-if="auth.isSuperAdmin" class="announce-create">
    <button class="btn btn-ghost" :disabled="pending" @click="openEditor()">新建公告</button>
  </div>

  <!-- 管理弹窗 -->
  <Dialog
    v-model:open="editorOpen"
    :title="editing && editing.id != null ? '编辑公告' : '新建公告'"
    :busy="pending"
    :described-by="editorError ? `${editorId}-error` : undefined"
  >
    <div class="field">
      <label class="field-label" :for="`${editorId}-title`">标题</label>
      <input :id="`${editorId}-title`" class="input" v-model="editing!.title" :disabled="pending" placeholder="公告标题" />
    </div>
    <div class="field">
      <label class="field-label" :for="`${editorId}-content`">内容</label>
      <textarea :id="`${editorId}-content`" class="textarea" v-model="editing!.content" :disabled="pending" placeholder="公告内容" />
    </div>
    <div class="field-row">
      <div class="field">
        <label class="field-label" :for="`${editorId}-level`">级别</label>
        <select :id="`${editorId}-level`" class="select" v-model="editing!.level" :disabled="pending">
          <option value="info">普通</option>
          <option value="success">成功</option>
          <option value="warning">警告</option>
          <option value="danger">重要</option>
        </select>
      </div>
      <label class="field-check" :for="`${editorId}-pinned`">
        <input :id="`${editorId}-pinned`" type="checkbox" v-model="editing!.pinned" :disabled="pending" /> 置顶
      </label>
      <label class="field-check" :for="`${editorId}-active`">
        <input :id="`${editorId}-active`" type="checkbox" v-model="editing!.is_active" :disabled="pending" /> 启用
      </label>
    </div>
    <p v-if="editorError" :id="`${editorId}-error`" class="editor-error" role="alert">{{ editorError }}</p>
    <p v-if="pending" role="status">正在处理，请稍候…</p>
    <template #footer="{ close }">
      <button
        v-if="editing && editing.id != null"
        class="btn btn-ghost btn-sm"
        :disabled="pending"
        @click="removeEditor"
      >
        删除
      </button>
      <span style="flex: 1" />
      <button class="btn btn-ghost btn-sm" :disabled="pending" @click="close">取消</button>
      <button class="btn btn-primary btn-sm" :disabled="pending" @click="saveEditor">保存</button>
    </template>
  </Dialog>
</template>

<style scoped>
.announce {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  margin: var(--space-5) auto 0;
  max-width: var(--container-wide, 1200px);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  background: var(--color-bg-elevated);
  position: relative;
}
.announce::before {
  content: '';
  position: absolute;
  left: 0;
  top: var(--space-3);
  bottom: var(--space-3);
  width: 3px;
  border-radius: 3px;
  background: var(--color-primary);
}
.announce-info::before { background: var(--color-info); }
.announce-success::before { background: var(--color-success); }
.announce-warning::before { background: var(--color-warning); }
.announce-danger::before { background: var(--color-danger); }
.announce-icon {
  width: 18px;
  height: 18px;
  margin-top: 2px;
  color: var(--color-primary);
  flex-shrink: 0;
}
.announce-body { flex: 1; min-width: 0; }
.announce-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--color-text-primary);
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.announce-text {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin-top: 2px;
  line-height: 1.5;
}
.announce-act {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: var(--radius-md);
  background: transparent;
  border: 1px solid transparent;
  color: var(--color-text-tertiary);
  cursor: pointer;
  flex-shrink: 0;
}
.announce-act:hover {
  background: var(--color-bg-overlay);
  color: var(--color-text-primary);
}
.field-row {
  display: flex;
  align-items: flex-end;
  gap: var(--space-4);
}
.field-check {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: 14px;
  color: var(--color-text-secondary);
  padding-bottom: var(--space-3);
  white-space: nowrap;
}
.announce-create {
  display: flex;
  justify-content: flex-end;
  width: 100%;
  max-width: var(--container-wide);
  margin: var(--space-2) auto 0;
  padding-inline: var(--page-padding-x);
}
.announce-create .btn,
.modal-footer .btn {
  min-width: var(--control-height-lg);
  min-height: var(--control-height-lg);
}
.editor-error {
  margin-top: var(--space-3);
  color: var(--color-danger);
}
</style>
