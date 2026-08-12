<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'

/**
 * 系统公告模块（任务1）：页面内容区左上角的公告条。
 * 后端暂无公告接口，当前用 localStorage 持久化（演示/过渡用），
 * 后续接后端公告接口时只需把 load/save 换成 API 调用即可。
 */

interface Announcement {
  id: string
  title: string
  content: string
  level: 'info' | 'success' | 'warning' | 'danger'
  pinned: boolean
  updated_at: string
}

const STORE_KEY = 'sys_announcements_v1'
const auth = useAuthStore()

const list = ref<Announcement[]>([])
const dismissed = ref<Set<string>>(new Set())
const editorOpen = ref(false)
const editing = ref<Announcement | null>(null)

const LEVEL_CLS: Record<Announcement['level'], string> = {
  info: 'badge-info',
  success: 'badge-success',
  warning: 'badge-warning',
  danger: 'badge-danger',
}

function seed(): Announcement[] {
  return [
    {
      id: 'seed-1',
      title: '欢迎使用 E-algo Rank',
      content: '系统已接入 Codeforces / AtCoder / 牛客三大平台，榜单每日自动同步更新。',
      level: 'info',
      pinned: true,
      updated_at: new Date().toISOString(),
    },
  ]
}

function load() {
  try {
    const raw = localStorage.getItem(STORE_KEY)
    list.value = raw ? (JSON.parse(raw) as Announcement[]) : seed()
  } catch {
    list.value = seed()
  }
}

function persist() {
  localStorage.setItem(STORE_KEY, JSON.stringify(list.value))
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
  editing.value = a
    ? { ...a }
    : {
        id: 'a-' + Date.now(),
        title: '',
        content: '',
        level: 'info',
        pinned: false,
        updated_at: new Date().toISOString(),
      }
  editorOpen.value = true
}

function saveEditor() {
  const e = editing.value
  if (!e || !e.title.trim() || !e.content.trim()) return
  e.updated_at = new Date().toISOString()
  const idx = list.value.findIndex((x) => x.id === e.id)
  if (idx >= 0) list.value[idx] = { ...e }
  else list.value.unshift({ ...e })
  persist()
  editorOpen.value = false
  editing.value = null
}

function removeEditor() {
  if (editing.value) {
    list.value = list.value.filter((x) => x.id !== editing.value!.id)
    persist()
  }
  editorOpen.value = false
  editing.value = null
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
      title="管理公告"
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

  <!-- 管理弹窗 -->
  <div v-if="editorOpen" class="modal-overlay" @click.self="editorOpen = false">
    <div class="modal">
      <div class="modal-header">
        <span>{{ editing && list.some((x) => x.id === editing!.id) ? '编辑公告' : '新建公告' }}</span>
      </div>
      <div class="modal-body">
        <div class="field">
          <label class="field-label">标题</label>
          <input class="input" v-model="editing!.title" placeholder="公告标题" />
        </div>
        <div class="field">
          <label class="field-label">内容</label>
          <textarea class="textarea" v-model="editing!.content" placeholder="公告内容" />
        </div>
        <div class="field-row">
          <div class="field">
            <label class="field-label">级别</label>
            <select class="select" v-model="editing!.level">
              <option value="info">普通</option>
              <option value="success">成功</option>
              <option value="warning">警告</option>
              <option value="danger">重要</option>
            </select>
          </div>
          <label class="field-check">
            <input type="checkbox" v-model="editing!.pinned" /> 置顶
          </label>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-ghost btn-sm" @click="removeEditor" v-if="editing && list.some((x) => x.id === editing!.id)">删除</button>
        <span style="flex: 1" />
        <button class="btn btn-ghost btn-sm" @click="editorOpen = false">取消</button>
        <button class="btn btn-primary btn-sm" @click="saveEditor">保存</button>
      </div>
    </div>
  </div>
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
</style>
