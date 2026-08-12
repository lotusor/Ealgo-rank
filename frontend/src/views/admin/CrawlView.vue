<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { listCrawlJobs, triggerCrawl, recomputeRanking } from '@/api'
import type { CrawlJob } from '@/api/types'
import { useToast } from '@/composables/useToast'
import SegmentedControl from '@/components/ui/SegmentedControl.vue'
import { fmtDate } from '@/utils/format'

const auth = useAuthStore()
const toast = useToast()

const jobs = ref<CrawlJob[]>([])
const loading = ref(false)
const platform = ref<'codeforces' | 'atcoder' | 'nowcoder'>('codeforces')
const count = ref(20)
const monthsBack = ref(2)
const triggering = ref(false)

const platformOptions = [
  { label: 'Codeforces', value: 'codeforces' as const },
  { label: 'AtCoder', value: 'atcoder' as const },
  { label: '牛客', value: 'nowcoder' as const },
]

async function load() {
  loading.value = true
  try {
    const res = await listCrawlJobs({ page: 1, page_size: 20 })
    jobs.value = res.results
  } finally {
    loading.value = false
  }
}

async function onTrigger() {
  triggering.value = true
  try {
    const payload: any = { platform: platform.value }
    if (platform.value === 'nowcoder') payload.months_back = monthsBack.value
    else payload.count = count.value
    await triggerCrawl(payload)
    toast.success('已派发爬取任务（worker 启动后自动执行）')
    await load()
  } catch (e: any) {
    toast.error(e?.response?.data?.detail || '触发失败')
  } finally {
    triggering.value = false
  }
}

async function onRecompute() {
  try {
    await recomputeRanking()
    toast.success('已触发全量重算（worker 异步执行）')
  } catch (e: any) {
    toast.error(e?.response?.data?.detail || '重算触发失败（需超级管理员）')
  }
}

function statusCls(s: string) {
  return s === 'success'
    ? 'badge-success'
    : s === 'failed' || s === 'partial'
      ? 'badge-danger'
      : s === 'running'
        ? 'badge-primary'
        : 'badge-warning'
}

const showLog = ref(false)
const logText = ref('')
function openLog(r: CrawlJob) {
  logText.value = r.log || r.error_message || '（无日志）'
  showLog.value = true
}

onMounted(load)
</script>

<template>
  <div class="container">
    <div class="page-head">
      <div>
        <div class="breadcrumb"><span>管理后台</span><span>/</span><span>爬虫任务</span></div>
        <h1 class="page-title">爬虫触发与重算</h1>
        <p class="page-subtitle">手动触发数据采集任务，或重新计算积分</p>
      </div>
    </div>

    <div class="grid" style="grid-template-columns: 1fr 1.5fr; gap: var(--space-6)">
      <!-- Trigger panel -->
      <div class="card card-pad">
        <div class="section-title" style="font-size: 16px; margin-bottom: var(--space-4)">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" /></svg>
          触发爬取任务
        </div>
        <div class="field">
          <label class="field-label">选择平台</label>
          <SegmentedControl v-model="platform" :options="platformOptions" />
        </div>
        <div class="field" v-if="platform !== 'nowcoder'">
          <label class="field-label">抓取场数</label>
          <input v-model.number="count" class="input" type="number" min="1" max="200" placeholder="抓取场数" />
        </div>
        <div class="field" v-else>
          <label class="field-label">最近 N 个月</label>
          <input v-model.number="monthsBack" class="input" type="number" min="1" max="12" placeholder="最近 N 个月" />
        </div>
        <button class="btn btn-primary btn-block" style="margin-top: var(--space-2)" :disabled="triggering" @click="onTrigger">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 3l14 9-14 9V3z" /></svg>
          {{ triggering ? '派发中…' : '开始爬取' }}
        </button>

        <div class="divider"></div>

        <div class="section-title" style="font-size: 16px; margin-bottom: var(--space-4)">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8" /><path d="M21 3v5h-5" /></svg>
          积分重算
        </div>
        <p class="body-sm text-tertiary" style="margin-bottom: var(--space-4)">重新计算所有学校与个人积分，适用于积分规则变更后。预计耗时 2-5 分钟。</p>
        <button v-if="auth.isSuperAdmin" class="btn btn-secondary btn-block" @click="onRecompute">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8" /><path d="M21 3v5h-5" /></svg>
          执行积分重算
        </button>
        <p v-else class="text-tertiary body-sm">积分重算仅超级管理员可操作。</p>
      </div>

      <!-- Task history -->
      <div class="card" style="overflow: hidden">
        <div class="card-header">
          <div class="card-title">任务历史</div>
          <span class="caption text-tertiary">最近 20 条</span>
        </div>
        <div class="table-wrap" style="border: none; border-radius: 0">
          <table class="data-table">
            <colgroup>
              <col style="width: 12%" />
              <col style="width: 16%" />
              <col style="width: 14%" />
              <col style="width: 18%" />
              <col style="width: 18%" />
              <col style="width: 14%" />
              <col style="width: 8%" />
            </colgroup>
            <thead>
              <tr><th>任务ID</th><th>平台</th><th>状态</th><th class="num-cell">开始时间</th><th class="num-cell">完成时间</th><th class="num-cell">采集记录</th><th class="center">日志</th></tr>
            </thead>
            <tbody>
              <tr v-for="j in jobs" :key="j.id">
                <td class="num">{{ j.id }}</td>
                <td>{{ j.platform_display }}</td>
                <td><span class="badge" :class="statusCls(j.status)">{{ j.status_display }}</span></td>
                <td class="num-cell">{{ j.started_at ? fmtDate(j.started_at) : '—' }}</td>
                <td class="num-cell">{{ j.finished_at ? fmtDate(j.finished_at) : '—' }}</td>
                <td class="num-cell num">{{ j.participation_count }}</td>
                <td class="center"><button class="btn btn-sm btn-ghost" @click="openLog(j)">查看</button></td>
              </tr>
              <tr v-if="!jobs.length"><td colspan="7" class="empty-cell">暂无任务</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <div v-if="showLog" class="modal-overlay" @click.self="showLog = false">
      <div class="modal" style="width: 640px">
        <div class="modal-header">执行日志</div>
        <div class="modal-body">
          <pre class="log-block">{{ logText }}</pre>
        </div>
        <div class="modal-footer">
          <button class="btn btn-ghost" @click="showLog = false">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.empty-cell { text-align: center; color: var(--color-text-tertiary); padding: var(--space-5); }
.log-block {
  max-height: 50vh;
  overflow: auto;
  background: var(--color-bg-base);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-4);
  font-family: var(--font-mono, monospace);
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
  color: var(--color-text-secondary);
}
@media (max-width: 980px) { .grid { grid-template-columns: 1fr !important; } }
</style>
