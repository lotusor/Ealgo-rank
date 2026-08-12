<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { listApplications, listCrawlJobs, listParticipations, listUsers } from '@/api'
import type { Application, CrawlJob, Participation } from '@/api/types'
import { fmtCount, fmtDate } from '@/utils/format'

const router = useRouter()
const auth = useAuthStore()

const pendingApps = ref(0)
const crawlToday = ref(0)
const partsTotal = ref(0)
const schoolUsers = ref(0)
const recentApps = ref<Application[]>([])
const recentJobs = ref<CrawlJob[]>([])
const recentParts = ref<Participation[]>([])

function statusCls(s: string) {
  return s === 'approved' ? 'badge-success' : s === 'rejected' || s === 'cancelled' ? 'badge-danger' : 'badge-warning'
}

onMounted(async () => {
  try {
    const [apps, jobs, parts, users] = await Promise.all([
      listApplications({ page_size: 5 }),
      listCrawlJobs({ page_size: 5 }),
      listParticipations({ page_size: 5, is_excluded: 'false' }),
      listUsers({ school: auth.user?.school?.id, page_size: 1 }),
    ])
    pendingApps.value = apps.results.filter((a) => a.status === 'pending').length
    crawlToday.value = jobs.results.filter((j) => j.created_at.startsWith(new Date().toISOString().slice(0, 10))).length
    partsTotal.value = parts.count
    schoolUsers.value = users.count
    recentApps.value = apps.results
    recentJobs.value = jobs.results
    recentParts.value = parts.results
  } catch {
    /* 忽略 */
  }
})

function fmtDateTime(s: string | null) {
  if (!s) return '—'
  return new Date(s).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}
</script>

<template>
  <div class="container">
    <div class="page-head">
      <div>
        <div class="breadcrumb"><span>管理后台</span><span>/</span><span>仪表盘</span></div>
        <h1 class="page-title">仪表盘</h1>
        <p class="page-subtitle">系统运营概览与待处理事项</p>
      </div>
      <button class="btn btn-primary" @click="router.push({ name: 'crawl' })">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M12 12a3 3 0 1 0 0 0" /></svg>
        触发爬取任务
      </button>
    </div>

    <div class="grid grid-4 stats-row">
      <div class="stat-card"><div class="stat-label">待审批申请</div><div class="stat-value num text-warning">{{ fmtCount(pendingApps) }}</div><div class="stat-sub">需尽快处理</div></div>
      <div class="stat-card"><div class="stat-label">今日爬取任务</div><div class="stat-value num">{{ fmtCount(crawlToday) }}</div><div class="stat-sub">新触发</div></div>
      <div class="stat-card"><div class="stat-label">参赛记录总数</div><div class="stat-value num">{{ fmtCount(partsTotal) }}</div><div class="stat-sub">累计</div></div>
      <div class="stat-card"><div class="stat-label">本校学生数</div><div class="stat-value num">{{ fmtCount(schoolUsers) }}</div><div class="stat-sub">已注册</div></div>
    </div>

    <div class="dash-grid">
      <div class="card" style="overflow: hidden">
        <div class="card-header"><div class="card-title">最新申请 · 待审批</div><a class="link caption" @click="router.push({ name: 'applications' })">查看全部</a></div>
        <div class="table-wrap" style="border: none; border-radius: 0">
          <table class="data-table">
            <thead><tr><th>申请人</th><th>学校</th><th class="num-cell">申请时间</th><th class="center">操作</th></tr></thead>
            <tbody>
              <tr v-for="a in recentApps" :key="a.id">
                <td>{{ a.applicant.real_name || a.applicant.username }}</td>
                <td class="text-secondary">{{ a.school?.name || '—' }}</td>
                <td class="num-cell">{{ fmtDate(a.created_at) }}</td>
                <td class="center"><span class="badge" :class="statusCls(a.status)">{{ a.status_display }}</span></td>
              </tr>
              <tr v-if="!recentApps.length"><td colspan="4" class="empty-cell">暂无申请</td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="card" style="overflow: hidden">
        <div class="card-header"><div class="card-title">最新爬取任务</div><a class="link caption" @click="router.push({ name: 'crawl' })">查看全部</a></div>
        <div class="table-wrap" style="border: none; border-radius: 0">
          <table class="data-table">
            <thead><tr><th>任务ID</th><th>平台</th><th>状态</th><th class="num-cell">记录数</th></tr></thead>
            <tbody>
              <tr v-for="j in recentJobs" :key="j.id">
                <td class="num">{{ j.id }}</td>
                <td>{{ j.platform_display }}</td>
                <td><span class="badge" :class="statusCls(j.status)">{{ j.status_display }}</span></td>
                <td class="num-cell">{{ fmtCount(j.participation_count) }}</td>
              </tr>
              <tr v-if="!recentJobs.length"><td colspan="4" class="empty-cell">暂无任务</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <div class="card" style="overflow: hidden; margin-top: var(--space-6)">
      <div class="card-header"><div class="card-title">最新参赛记录</div><a class="link caption" @click="router.push({ name: 'participations' })">查看全部</a></div>
      <div class="table-wrap" style="border: none; border-radius: 0">
        <table class="data-table">
            <thead><tr><th>学生</th><th>比赛</th><th>平台</th><th class="num-cell">排名</th><th class="num-cell">积分</th><th class="num-cell">时间</th></tr></thead>
            <tbody>
              <tr v-for="p in recentParts" :key="p.id">
                <td>{{ p.user_real_name || p.user_username }}</td>
                <td class="cell-ellipsis">{{ p.contest_name }}</td>
              <td>{{ p.contest_platform_display }}</td>
              <td class="num-cell">{{ p.rank != null ? '#' + p.rank : '—' }}</td>
              <td class="num-cell">{{ p.total_score != null ? p.total_score : '—' }}</td>
              <td class="num-cell">{{ fmtDateTime(p.contest_start_time) }}</td>
            </tr>
            <tr v-if="!recentParts.length"><td colspan="6" class="empty-cell">暂无记录</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<style scoped>
.stats-row { margin-bottom: var(--space-6); }
.dash-grid { display: grid; grid-template-columns: 1.2fr 1fr; gap: var(--space-6); }
.empty-cell { text-align: center; color: var(--color-text-tertiary); padding: var(--space-5); }
@media (max-width: 980px) { .dash-grid { grid-template-columns: 1fr; } }
</style>
