<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import {
  createExport, downloadExport, listExports, listSchools, revokeExport,
} from '@/api'
import type {
  ExportJob, ExportLayout, ExportRatingWindow, ExportScopeKind, School,
} from '@/api/types'
import { useToast } from '@/composables/useToast'
import DataPagination from '@/components/ui/DataPagination.vue'
import { formatDateTime } from '@/utils/format'

/**
 * 导出学校赛情。
 *
 * 三个与后端约定强相关的点，改前端时不要"顺手优化"掉：
 * 1. 下载**必须**带 Authorization 头（后端刻意不支持 URL 签名），
 *    所以只能取 blob 再本地落盘，不能用 `<a href>` 直链。
 * 2. 学校管理员的范围由后端强制收口：前端把下拉禁用只是体验，
 *    真正拦越权的是后端 403 + 留痕。
 * 3. 异步任务要轮询，但必须能停：任务完成后立刻停表，离开页面清定时器，
 *    否则一个后台标签页会一直打接口。
 */
const auth = useAuthStore()
const toast = useToast()

const schools = ref<School[]>([])
const year = ref<number>(new Date().getFullYear())
const scopeKind = ref<ExportScopeKind>('school')
const singleSchool = ref<number | null>(null)
const multiIds = ref<number[]>([])
const layout = ref<ExportLayout>('per_school')
const ratingWindow = ref<ExportRatingWindow>('season')
const includeZero = ref(false)
const includeGlobalRank = ref(true)

const submitting = ref(false)
const jobs = ref<ExportJob[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = 20
const total = ref(0)
const statusFilter = ref('')
const downloadingId = ref<number | null>(null)

let pollTimer: ReturnType<typeof setTimeout> | undefined

const yearOptions = computed(() => {
  const now = new Date().getFullYear()
  return [now + 1, now, now - 1, now - 2].filter((y) => y >= 2025)
})

const mySchoolName = computed(() => auth.user?.school?.name || '未归属学校')
const activeJobs = computed(() =>
  jobs.value.filter((j) => j.status === 'pending' || j.status === 'running'),
)
const canSubmit = computed(() => {
  if (submitting.value) return false
  if (scopeKind.value === 'all') return true
  if (scopeKind.value === 'multi') return multiIds.value.length > 0
  return singleSchool.value !== null
})

function statusBadge(status: ExportJob['status']): string {
  if (status === 'succeeded') return 'badge badge-success'
  if (status === 'failed') return 'badge badge-danger'
  if (status === 'running' || status === 'pending') return 'badge badge-info'
  return 'badge badge-muted'
}

function fmtSize(bytes: number): string {
  if (!bytes) return '—'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function scopeLabel(job: ExportJob): string {
  if (job.scope_kind === 'all') return `全站（${job.scope_school_ids.length} 校）`
  if (job.scope_kind === 'multi') return `${job.scope_school_ids.length} 所学校`
  const id = job.scope_school_ids[0]
  const hit = schools.value.find((s) => s.id === id)
  return hit?.name || '本校'
}

async function loadSchools() {
  try {
    const data = await listSchools({ page_size: 200 })
    schools.value = data.results
    if (!auth.isSuperAdmin) {
      // 后端会强制收口，这里只是让下拉显示成本校，避免"看起来能选"
      singleSchool.value = auth.user?.school?.id ?? null
    } else {
      // 超管默认落在自己归属的学校；没有归属才退回列表第一项
      singleSchool.value = auth.user?.school?.id ?? schools.value[0]?.id ?? null
    }
  } catch {
    toast.error('学校列表加载失败')
  }
}

async function load() {
  loading.value = true
  try {
    const params: Record<string, string | number> = { page: page.value, page_size: pageSize }
    if (statusFilter.value) params.status = statusFilter.value
    const data = await listExports(params)
    jobs.value = data.results
    total.value = data.count
    if (activeJobs.value.length) schedulePoll()
  } catch (e: any) {
    toast.error(e?.response?.data?.detail || '任务列表加载失败')
  } finally {
    loading.value = false
  }
}

function schedulePoll() {
  clearPoll()
  pollTimer = setTimeout(async () => {
    await load()
  }, 3000)
}

function clearPoll() {
  if (pollTimer) {
    clearTimeout(pollTimer)
    pollTimer = undefined
  }
}

function resetPage() {
  page.value = 1
  load()
}

function toggleMulti(id: number) {
  const idx = multiIds.value.indexOf(id)
  if (idx >= 0) multiIds.value.splice(idx, 1)
  else multiIds.value.push(id)
}

async function submit() {
  if (!canSubmit.value) return
  submitting.value = true
  try {
    const payload = {
      scope_kind: scopeKind.value,
      school_ids:
        scopeKind.value === 'all'
          ? []
          : scopeKind.value === 'multi'
            ? [...multiIds.value]
            : singleSchool.value
              ? [singleSchool.value]
              : [],
      year: year.value,
      layout: layout.value,
      include_zero_participation: includeZero.value,
      include_global_rank: includeGlobalRank.value,
      rating_window: ratingWindow.value,
    }
    const job = await createExport(payload)
    page.value = 1
    await load()
    if (job.status === 'succeeded') {
      // 下载由脚本触发（blob + a[download]），部分浏览器的下载拦截策略会静默
      // 丢弃且不报错，所以文案要留一个兜底入口，不能只说「开始下载」。
      toast.success(`已生成 ${job.row_count} 行，正在下载…若未出现保存，请点列表中的「下载」`)
      await download(job)
    } else if (job.status === 'failed') {
      toast.error(job.error_message || '生成失败')
    } else {
      toast.info('已提交，正在后台生成，完成后会在列表里出现「下载」')
    }
  } catch (e: any) {
    toast.error(e?.response?.data?.detail || '提交失败')
  } finally {
    submitting.value = false
  }
}

async function download(job: ExportJob) {
  downloadingId.value = job.id
  let url = ''
  try {
    const { blob, filename } = await downloadExport(job.id)
    url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    a.remove()
    job.download_count += 1
  } catch (e: any) {
    // 410/409 的响应体是 blob，detail 读不出来，只能给通用文案
    if (e?.response?.status === 410) toast.error('文件已过期，请重新生成')
    else if (e?.response?.status === 403) toast.error('权限已变更，无法下载')
    else toast.error('下载失败，请稍后重试')
  } finally {
    // 必须配对释放，否则长会话一直占着内存
    if (url) URL.revokeObjectURL(url)
    downloadingId.value = null
  }
}

async function revoke(job: ExportJob) {
  if (!window.confirm(`撤销后文件立即删除且不可恢复，确定撤销 #${job.id}？`)) return
  try {
    await revokeExport(job.id)
    toast.success('已撤销')
    await load()
  } catch (e: any) {
    toast.error(e?.response?.data?.detail || '撤销失败')
  }
}

onMounted(async () => {
  await loadSchools()
  await load()
})

onUnmounted(clearPoll)
</script>

<template>
  <div class="container">
    <div class="page-head">
      <div>
        <div class="breadcrumb"><span>管理后台</span><span>/</span><span>导出赛情</span></div>
        <h1 class="page-title">导出学校赛情</h1>
        <p class="page-subtitle">
          按赛季导出学生参赛汇总表（姓名 / 学号 / 参赛与异常次数 / 各平台 rating / 总rating / 校排）
        </p>
      </div>
    </div>

    <div class="card export-form">
      <div class="export-grid">
        <div class="field">
          <label class="field-label">导出范围</label>
          <select v-model="scopeKind" class="input" :disabled="!auth.isSuperAdmin">
            <option value="school">单校</option>
            <option v-if="auth.isSuperAdmin" value="multi">多校</option>
            <option v-if="auth.isSuperAdmin" value="all">全站</option>
          </select>
          <p v-if="!auth.isSuperAdmin" class="field-hint">学校管理员仅可导出本校</p>
        </div>

        <div v-if="scopeKind === 'school'" class="field">
          <label class="field-label">学校</label>
          <select v-model.number="singleSchool" class="input" :disabled="!auth.isSuperAdmin">
            <template v-if="auth.isSuperAdmin">
              <option v-for="s in schools" :key="s.id" :value="s.id">{{ s.name }}</option>
            </template>
            <template v-else>
              <option :value="auth.user?.school?.id ?? null">{{ mySchoolName }}</option>
            </template>
          </select>
        </div>

        <div class="field">
          <label class="field-label">赛季</label>
          <select v-model.number="year" class="input">
            <option v-for="y in yearOptions" :key="y" :value="y">{{ y }} 赛季</option>
          </select>
        </div>

        <div class="field">
          <label class="field-label">输出形态</label>
          <select v-model="layout" class="input">
            <option value="per_school">按校拆分（每校一个工作表）</option>
            <option value="merged">合并单表（可跨校比较）</option>
          </select>
        </div>

        <div class="field">
          <label class="field-label">平台 rating 口径</label>
          <select v-model="ratingWindow" class="input">
            <option value="season">赛季末值（可复现，推荐）</option>
            <option value="latest">当前最新（随抓取变动）</option>
          </select>
          <p class="field-hint">报表要对账，默认取赛季末值</p>
        </div>
      </div>

      <div v-if="scopeKind === 'multi'" class="school-picker">
        <p class="field-label">选择学校（已选 {{ multiIds.length }} 所）</p>
        <div class="school-picker-list">
          <label v-for="s in schools" :key="s.id" class="school-chip" :class="{ on: multiIds.includes(s.id) }">
            <input type="checkbox" :checked="multiIds.includes(s.id)" @change="toggleMulti(s.id)" />
            {{ s.name }}
          </label>
        </div>
      </div>

      <div class="export-options">
        <label class="check"><input v-model="includeZero" type="checkbox" /> 含零参赛学生（默认不列）</label>
        <label v-if="layout === 'merged'" class="check">
          <input v-model="includeGlobalRank" type="checkbox" /> 含「全站排名」列
        </label>
      </div>

      <div class="export-actions">
        <button class="btn btn-primary" :disabled="!canSubmit" @click="submit">
          {{ submitting ? '生成中…' : '生成文件' }}
        </button>
        <span class="caption text-tertiary">
          单校通常 1 秒内出文件；数据量大时转后台生成，完成后在下方列表下载
        </span>
      </div>
    </div>

    <div class="filter-bar">
      <select v-model="statusFilter" class="input" style="width: auto" @change="resetPage">
        <option value="">全部状态</option>
        <option value="succeeded">已完成</option>
        <option value="pending">排队中</option>
        <option value="running">生成中</option>
        <option value="failed">失败</option>
        <option value="expired">已过期</option>
        <option value="revoked">已撤销</option>
      </select>
      <button class="btn btn-ghost" @click="load">刷新</button>
      <span class="caption text-tertiary" style="margin-left: auto">
        共 <b class="num">{{ total }}</b> 条
        <template v-if="activeJobs.length"> · <b class="num">{{ activeJobs.length }}</b> 条生成中</template>
      </span>
    </div>

    <div class="card" style="overflow: hidden">
      <div class="table-wrap" style="border: none; border-radius: 0">
        <table class="data-table">
          <colgroup>
            <col style="width: 8%" />
            <col style="width: 20%" />
            <col style="width: 8%" />
            <col style="width: 12%" />
            <col style="width: 8%" />
            <col style="width: 9%" />
            <col style="width: 9%" />
            <col style="width: 13%" />
            <col style="width: 13%" />
          </colgroup>
          <thead>
            <tr>
              <th>#</th>
              <th>范围</th>
              <th>赛季</th>
              <th>形态</th>
              <th>行数</th>
              <th>大小</th>
              <th>下载</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!jobs.length && !loading">
              <td class="empty-cell" colspan="9">暂无导出记录</td>
            </tr>
            <tr v-for="job in jobs" :key="job.id">
              <td class="num-cell">{{ job.id }}</td>
              <td>
                {{ scopeLabel(job) }}
                <span v-if="job.suspicious" class="badge badge-warning" style="margin-left: 6px">异常下载</span>
              </td>
              <td class="num-cell">{{ job.year }}</td>
              <td>{{ job.layout_display }}</td>
              <td class="num-cell">{{ job.row_count || '—' }}</td>
              <td class="num-cell">{{ fmtSize(job.file_size) }}</td>
              <td class="num-cell">{{ job.download_count }}</td>
              <td>
                <span :class="statusBadge(job.status)">{{ job.status_display }}</span>
                <div v-if="job.error_message" class="caption text-tertiary" :title="job.error_message">
                  {{ job.error_message.slice(0, 24) }}
                </div>
              </td>
              <td>
                <button
                  v-if="job.status === 'succeeded' && !job.is_expired"
                  class="btn btn-ghost btn-sm"
                  :disabled="downloadingId === job.id"
                  @click="download(job)"
                >
                  {{ downloadingId === job.id ? '下载中…' : '下载' }}
                </button>
                <span v-else-if="job.is_expired" class="caption text-tertiary">已过期</span>
                <button
                  v-if="job.status === 'succeeded' || job.status === 'failed'"
                  class="btn btn-ghost btn-sm"
                  @click="revoke(job)"
                >
                  撤销
                </button>
                <span class="caption text-tertiary" style="margin-left: 6px">
                  {{ formatDateTime(job.created_at) }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <DataPagination v-model:page="page" :page-size="pageSize" :total="total" @update:page="load" />
  </div>
</template>

<style scoped>
.export-form {
  padding: var(--space-6);
  margin-bottom: var(--space-5);
}

.export-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: var(--space-4);
}

.export-options {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-5);
  margin-top: var(--space-4);
}

.check {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  cursor: pointer;
}

.export-actions {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  margin-top: var(--space-5);
  padding-top: var(--space-4);
  border-top: 1px solid var(--color-divider);
}

.school-picker {
  margin-top: var(--space-4);
}

.school-picker-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  max-height: 160px;
  overflow-y: auto;
  margin-top: var(--space-2);
}

.school-chip {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: 4px 10px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  cursor: pointer;
}

.school-chip.on {
  border-color: var(--color-primary-border);
  background: var(--color-primary-subtle);
  color: var(--color-primary-text);
}

.school-chip input {
  display: none;
}

@media (max-width: 1024px) {
  .export-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 560px) {
  .export-grid {
    grid-template-columns: minmax(0, 1fr);
  }
  .export-actions {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
