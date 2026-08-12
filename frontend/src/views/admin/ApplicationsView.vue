<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { listApplications, approveApplication, rejectApplication, cancelApplication } from '@/api'
import type { Application, ApplicationStatus } from '@/api/types'
import { useToast } from '@/composables/useToast'
import PageTabs from '@/components/ui/PageTabs.vue'
import { fmtDate } from '@/utils/format'

const auth = useAuthStore()
const toast = useToast()

const all = ref<Application[]>([])
const loading = ref(false)
const keyword = ref('')
const status = ref<ApplicationStatus | 'all'>('pending')

const counts = computed(() => ({
  pending: all.value.filter((a) => a.status === 'pending').length,
  approved: all.value.filter((a) => a.status === 'approved').length,
  rejected: all.value.filter((a) => a.status === 'rejected').length,
  all: all.value.length,
}))

const rows = computed(() => {
  const k = keyword.value.trim().toLowerCase()
  return all.value.filter((a) => {
    if (status.value !== 'all' && a.status !== status.value) return false
    if (!k) return true
    return (
      a.applicant.username.toLowerCase().includes(k) ||
      a.applicant.real_name.toLowerCase().includes(k) ||
      (a.reason || '').toLowerCase().includes(k) ||
      (a.contact || '').toLowerCase().includes(k)
    )
  })
})

async function load() {
  loading.value = true
  try {
    const res = await listApplications({ page: 1, page_size: 200 })
    all.value = res.results
  } finally {
    loading.value = false
  }
}

function statusCls(s: string) {
  return s === 'approved' ? 'badge-success' : s === 'rejected' || s === 'cancelled' ? 'badge-danger' : 'badge-warning'
}

const showReview = ref(false)
const reviewTarget = ref<Application | null>(null)
const reviewAction = ref<'approve' | 'reject'>('approve')
const reviewComment = ref('')

function openReview(a: Application, action: 'approve' | 'reject') {
  reviewTarget.value = a
  reviewAction.value = action
  reviewComment.value = ''
  showReview.value = true
}
async function submitReview() {
  if (!reviewTarget.value) return
  try {
    if (reviewAction.value === 'approve') {
      await approveApplication(reviewTarget.value.id, reviewComment.value)
      toast.success('已通过，申请人角色与学校已同步')
    } else {
      await rejectApplication(reviewTarget.value.id, reviewComment.value)
      toast.info('已驳回')
    }
    showReview.value = false
    await load()
  } catch (e: any) {
    toast.error(e?.response?.data?.detail || '操作失败')
  }
}
async function cancel(a: Application) {
  try {
    await cancelApplication(a.id)
    toast.info('已撤回')
    await load()
  } catch (e: any) {
    toast.error(e?.response?.data?.detail || '撤回失败')
  }
}

onMounted(load)
</script>

<template>
  <div class="container">
    <div class="page-head">
      <div>
        <div class="breadcrumb"><span>管理后台</span><span>/</span><span>申请审批</span></div>
        <h1 class="page-title">管理员申请审批</h1>
        <p class="page-subtitle">处理学生申请成为学校管理员的请求</p>
      </div>
    </div>

    <PageTabs
      v-model="status"
      :options="[
        { label: '待审批', value: 'pending', count: counts.pending },
        { label: '已通过', value: 'approved', count: counts.approved },
        { label: '已驳回', value: 'rejected', count: counts.rejected },
        { label: '全部', value: 'all', count: counts.all },
      ]"
    />

    <div class="filter-bar" style="margin-top: var(--space-4)">
      <div class="input-group" style="flex: 1; max-width: 360px">
        <svg class="input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" /></svg>
        <input v-model="keyword" class="input" type="text" placeholder="搜索用户名 / 姓名 / 理由 / 联系方式…" />
      </div>
    </div>

    <div class="card" style="overflow: hidden">
      <div class="table-wrap" style="border: none; border-radius: 0">
        <table class="data-table">
          <colgroup>
            <col style="width: 16%" />
            <col style="width: 14%" />
            <col style="width: 14%" />
            <col style="width: 20%" />
            <col style="width: 14%" />
            <col style="width: 10%" />
            <col style="width: 12%" />
          </colgroup>
          <thead>
            <tr><th>申请人</th><th>真实姓名</th><th>申请学校</th><th>申请理由</th><th class="num-cell">申请时间</th><th class="center">状态</th><th class="center">操作</th></tr>
          </thead>
          <tbody>
            <tr v-for="a in rows" :key="a.id">
              <td class="cell-strong">{{ a.applicant.username }}</td>
              <td>{{ a.applicant.real_name || '—' }}</td>
              <td class="cell-ellipsis">{{ a.school?.name || '—' }}</td>
              <td class="cell-ellipsis text-secondary">{{ a.reason || '—' }}</td>
              <td class="num-cell">{{ fmtDate(a.created_at) }}</td>
              <td class="center"><span class="badge" :class="statusCls(a.status)">{{ a.status_display }}</span></td>
              <td class="center">
                <div class="row-actions">
                  <button
                    v-if="auth.isSuperAdmin && a.status === 'pending'"
                    class="btn btn-sm btn-primary"
                    @click="openReview(a, 'approve')"
                  >通过</button>
                  <button
                    v-if="auth.isSuperAdmin && a.status === 'pending'"
                    class="btn btn-sm btn-danger"
                    @click="openReview(a, 'reject')"
                  >驳回</button>
                  <button
                    v-if="a.status === 'pending' && a.applicant.id === auth.user?.id"
                    class="btn btn-sm btn-ghost"
                    @click="cancel(a)"
                  >撤回</button>
                </div>
              </td>
            </tr>
            <tr v-if="!rows.length"><td colspan="7" class="empty-cell">暂无申请</td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="showReview" class="modal-overlay" @click.self="showReview = false">
      <div class="modal" style="width: 480px">
        <div class="modal-header">审批意见</div>
        <div class="modal-body">
          <p class="text-secondary" style="margin-bottom: var(--space-4)">
            对「<b>{{ reviewTarget?.school?.name }}</b>」的申请执行
            <b :class="reviewAction === 'approve' ? 'text-success' : 'text-danger'">{{ reviewAction === 'approve' ? '通过' : '驳回' }}</b>。
          </p>
          <div class="field">
            <label class="field-label">审批意见（可选）</label>
            <textarea v-model="reviewComment" class="input" rows="3" placeholder="填写审批意见…" />
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-ghost" @click="showReview = false">取消</button>
          <button class="btn" :class="reviewAction === 'approve' ? 'btn-primary' : 'btn-danger'" @click="submitReview">
            确认{{ reviewAction === 'approve' ? '通过' : '驳回' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.empty-cell { text-align: center; color: var(--color-text-tertiary); padding: var(--space-5); }
.row-actions { display: flex; gap: var(--space-2); justify-content: center; flex-wrap: wrap; }
</style>
