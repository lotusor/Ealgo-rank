<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { listApplications, cancelApplication } from '@/api'
import type { Application } from '@/api/types'
import EmptyState from '@/components/ui/EmptyState.vue'

const router = useRouter()
const rows = ref<Application[]>([])
const loading = ref(true)
const cancelling = ref<number | null>(null)

async function load() {
  loading.value = true
  try {
    // 后端对非超管自动只返回本人申请
    const data = await listApplications({ page_size: 20 })
    rows.value = data.results
  } catch {
    /* 保持空态 */
  } finally {
    loading.value = false
  }
}
onMounted(load)

async function onCancel(a: Application) {
  if (!confirm(`确定撤回对「${a.school?.name || '未选择学校'}」的管理员申请吗？`)) return
  cancelling.value = a.id
  try {
    await cancelApplication(a.id)
    await load()
  } finally {
    cancelling.value = null
  }
}

function statusCls(s: string) {
  return s === 'approved'
    ? 'badge-success'
    : s === 'rejected' || s === 'cancelled'
      ? 'badge-danger'
      : 'badge-warning'
}

function fmtDate(s: string | null) {
  if (!s) return '—'
  return new Date(s).toLocaleString('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  })
}
</script>

<template>
  <div class="container-wide">
    <div class="page-head">
      <div>
        <div class="breadcrumb"><span>个人中心</span><span>/</span><span>我的管理员申请</span></div>
        <h1 class="page-title">我的管理员申请</h1>
        <p class="page-subtitle">查看申请状态与超管的审批意见</p>
      </div>
      <button class="btn btn-primary" @click="router.push('/register/admin-apply')">
        发起新申请
      </button>
    </div>

    <div v-if="loading" class="card card-pad">
      <span class="skel" style="width: 40%; height: 24px" />
    </div>

    <template v-else-if="rows.length === 0">
      <div class="card card-pad">
        <EmptyState
          title="还没有管理员申请"
          hint="提交申请后，可在此查看审批进度与审批意见"
        />
        <div style="text-align: center; margin-top: var(--space-4)">
          <button class="btn btn-primary" @click="router.push('/register/admin-apply')">前往申请</button>
        </div>
      </div>
    </template>

    <div v-else class="app-list">
      <div v-for="a in rows" :key="a.id" class="card card-pad app-card">
        <div class="app-head">
          <div class="app-school">
            <span class="cell-strong">{{ a.school?.name || (a.proposed_school_name ? '申请新建：' + a.proposed_school_name : '申请新建学校') }}</span>
            <span class="badge" :class="statusCls(a.status)">{{ a.status_display }}</span>
          </div>
          <span class="caption text-tertiary">{{ fmtDate(a.created_at) }}</span>
        </div>

        <div class="app-body">
          <div class="app-row">
            <span class="app-label">申请理由</span>
            <span class="text-secondary">{{ a.reason || '—' }}</span>
          </div>
          <div class="app-row">
            <span class="app-label">联系方式</span>
            <span class="num">{{ a.contact || '—' }}</span>
          </div>
          <div v-if="a.reviewed_at" class="app-row">
            <span class="app-label">审批时间</span>
            <span>{{ fmtDate(a.reviewed_at) }}</span>
          </div>
        </div>

        <div
          v-if="a.review_comment"
          class="review-box"
          :class="a.status === 'approved' ? 'review-ok' : 'review-no'"
        >
          <span class="review-label">超管审批意见</span>
          <p class="review-text">{{ a.review_comment }}</p>
        </div>

        <div v-if="a.status === 'pending'" style="margin-top: var(--space-4)">
          <button
            class="btn btn-ghost btn-sm"
            :disabled="cancelling === a.id"
            @click="onCancel(a)"
          >
            {{ cancelling === a.id ? '撤回中…' : '撤回申请' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.app-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}
.app-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-4);
  flex-wrap: wrap;
  margin-bottom: var(--space-3);
}
.app-school {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}
.app-body {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.app-row {
  display: flex;
  gap: var(--space-3);
  font-size: 14px;
}
.app-label {
  flex-shrink: 0;
  width: 72px;
  color: var(--color-text-tertiary);
}
.review-box {
  margin-top: var(--space-3);
  border-radius: var(--radius-md);
  padding: var(--space-3) var(--space-4);
}
.review-ok {
  background: var(--color-success-subtle, rgba(16, 185, 129, 0.08));
  border: 1px solid rgba(16, 185, 129, 0.3);
}
.review-no {
  background: var(--color-danger-subtle, rgba(239, 68, 68, 0.06));
  border: 1px solid rgba(239, 68, 68, 0.3);
}
.review-label {
  font-size: 12px;
  font-weight: 700;
  color: var(--color-text-tertiary);
  display: block;
  margin-bottom: 4px;
}
.review-text {
  font-size: 14px;
  color: var(--color-text-primary);
  white-space: pre-wrap;
}
</style>
