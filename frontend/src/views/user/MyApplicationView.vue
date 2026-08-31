<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
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
    const list = data.results
    // 待审优先，其余按时间倒序
    list.sort((x, y) => {
      if ((x.status === 'pending') !== (y.status === 'pending')) {
        return x.status === 'pending' ? -1 : 1
      }
      return y.created_at.localeCompare(x.created_at)
    })
    rows.value = list
  } catch {
    /* 保持空态 */
  } finally {
    loading.value = false
  }
}
onMounted(load)

// 待审期间禁止再次申请（后端同有校验）
const hasPending = computed(() => rows.value.some((a) => a.status === 'pending'))

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
      <button v-if="!hasPending" class="btn btn-primary" @click="router.push('/register/admin-apply')">
        发起新申请
      </button>
    </div>

    <div v-if="hasPending" class="pending-tip">
      您有申请正在等待审批，审批完成（通过/驳回/撤回）后即可再次申请。
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
      <div v-for="a in rows" :key="a.id" class="app-card">
        <div class="app-row1">
          <div class="app-school">
            <span class="cell-strong">{{ a.school?.name || (a.proposed_school_name ? '申请新建：' + a.proposed_school_name : '申请新建学校') }}</span>
            <span class="badge" :class="statusCls(a.status)">{{ a.status_display }}</span>
          </div>
          <span class="caption text-tertiary">{{ fmtDate(a.created_at) }}</span>
        </div>
        <div class="app-row2">
          <span class="cell-ellipsis text-secondary" :title="a.reason">{{ a.reason || '—' }}</span>
          <span class="caption text-tertiary" v-if="a.contact">联系：{{ a.contact }}</span>
          <span class="caption text-tertiary" v-if="a.reviewed_at">审批：{{ fmtDate(a.reviewed_at) }}</span>
        </div>
        <div
          v-if="a.review_comment"
          class="review-box"
          :class="a.status === 'approved' ? 'review-ok' : 'review-no'"
        >
          <span class="review-label">审批意见</span>
          <span class="review-text">{{ a.review_comment }}</span>
        </div>
        <div class="app-foot" v-if="a.status === 'pending'">
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
.pending-tip {
  background: rgba(245, 158, 11, 0.08);
  border: 1px solid rgba(245, 158, 11, 0.3);
  color: var(--color-text-secondary);
  border-radius: var(--radius-md);
  padding: var(--space-3) var(--space-4);
  font-size: 13px;
  margin-bottom: var(--space-5);
}
.app-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.app-card {
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 14px 16px;
}
.app-row1 {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-3);
  flex-wrap: wrap;
}
.app-school {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}
.app-row2 {
  display: flex;
  gap: var(--space-4);
  flex-wrap: wrap;
  margin-top: 6px;
  font-size: 13px;
  min-width: 0;
}
.app-row2 > .cell-ellipsis {
  max-width: 100%;
}
.review-box {
  margin-top: 8px;
  border-radius: var(--radius-md);
  padding: 8px 12px;
  font-size: 13px;
}
.review-ok {
  background: rgba(16, 185, 129, 0.08);
  border: 1px solid rgba(16, 185, 129, 0.3);
}
.review-no {
  background: rgba(239, 68, 68, 0.06);
  border: 1px solid rgba(239, 68, 68, 0.3);
}
.review-label {
  font-weight: 700;
  color: var(--color-text-tertiary);
  margin-right: 8px;
  font-size: 12px;
}
.review-text {
  color: var(--color-text-primary);
  white-space: pre-wrap;
}
.app-foot {
  margin-top: 8px;
  display: flex;
  justify-content: flex-end;
}
</style>
