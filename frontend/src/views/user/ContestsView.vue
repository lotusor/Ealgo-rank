<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { listContests } from '@/api'
import type { Contest, ContestPlatform } from '@/api/types'
import DataPagination from '@/components/ui/DataPagination.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import SegmentedControl from '@/components/ui/SegmentedControl.vue'
import { SCORING_PLATFORMS, platformClass } from '@/platforms/meta'

const platform = ref<'' | ContestPlatform>('')
const rated = ref<'all' | 'yes' | 'no'>('all')
const keyword = ref('')
const sort = ref<'time' | 'difficulty' | 'participants'>('time')
const page = ref(1)
const pageSize = 12

const rows = ref<Contest[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
let requestSeq = 0
let resettingPage = false
let searchTimer: ReturnType<typeof setTimeout> | undefined
const SEARCH_DEBOUNCE_MS = 300

// 比赛目录列的是「有榜单的真实赛次」，所以只给可计分平台；
// 只做日历展示的平台（洛谷）在 /calendar 里出现，这里点了必然是空列表
const platformOptions = computed(() => [
  { label: '全部', value: '' as const },
  ...SCORING_PLATFORMS.map((p) => ({ label: p.label, value: p.key })),
])
const ratedOptions = [
  { label: '全部', value: 'all' as const },
  { label: '仅 Rated', value: 'yes' as const },
  { label: '非 Rated', value: 'no' as const },
]
const sortOptions = [
  { label: '本页按时间倒序', value: 'time' as const },
  { label: '本页按难度', value: 'difficulty' as const },
  { label: '本页按参与人数', value: 'participants' as const },
]

async function load() {
  clearTimeout(searchTimer)
  searchTimer = undefined
  const seq = ++requestSeq
  loading.value = true
  error.value = ''
  try {
    const { count, results } = await listContests({
      platform: platform.value || undefined,
      is_rated: rated.value === 'all' ? undefined : rated.value === 'yes',
      name: keyword.value.trim() || undefined,
      page: page.value,
      page_size: pageSize,
    })
    if (seq !== requestSeq) return
    rows.value = results
    total.value = count
  } catch {
    if (seq !== requestSeq) return
    rows.value = []
    total.value = 0
    error.value = '比赛列表加载失败，请重试。'
  } finally {
    if (seq === requestSeq) loading.value = false
  }
}

onMounted(load)
watch([platform, rated, keyword], (values, previous) => {
  // 输入时立即作废旧请求，不能等防抖结束才阻止旧响应写入。
  requestSeq += 1
  clearTimeout(searchTimer)
  searchTimer = undefined
  resettingPage = true
  page.value = 1
  resettingPage = false
  rows.value = []
  total.value = 0
  error.value = ''
  loading.value = true
  if (values[2] !== previous[2]) {
    searchTimer = setTimeout(load, SEARCH_DEBOUNCE_MS)
  } else {
    load()
  }
}, { flush: 'sync' })
watch(page, () => {
  // 筛选归首页由上面的 watcher 加载，避免重复请求。
  if (!resettingPage) load()
}, { flush: 'sync' })
onBeforeUnmount(() => {
  clearTimeout(searchTimer)
  requestSeq += 1
})

const sortedRows = computed(() => {
  const arr = [...rows.value]
  if (sort.value === 'difficulty')
    arr.sort((a, b) => Number(b.difficulty_factor) - Number(a.difficulty_factor))
  else if (sort.value === 'participants')
    arr.sort((a, b) => (b.participant_count || 0) - (a.participant_count || 0))
  else arr.sort((a, b) => (b.start_time || '').localeCompare(a.start_time || ''))
  return arr
})

function fmtDate(s: string | null) {
  if (!s) return '—'
  return new Date(s).toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
}
</script>

<template>
  <div class="container-wide">
    <div class="page-head">
      <div>
        <div class="breadcrumb"><span>比赛列表</span></div>
        <h1 class="page-title">比赛列表</h1>
        <p class="page-subtitle">已收录的各平台算法竞赛，按时间倒序排列</p>
      </div>
    </div>

    <div class="filter-bar">
      <SegmentedControl v-model="platform" :options="platformOptions" />
      <SegmentedControl v-model="rated" :options="ratedOptions" />
      <div class="input-group" style="margin-left: auto">
        <svg class="input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" /></svg>
        <input class="input" type="text" v-model="keyword" placeholder="搜索比赛名称…" />
      </div>
      <select class="input" style="width: auto" v-model="sort">
        <option v-for="o in sortOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
      </select>
    </div>

    <div v-if="loading" class="grid grid-2 contest-grid" role="status" aria-label="正在加载比赛列表">
      <div v-for="n in 4" :key="n" class="card card-pad"><span class="skel" style="width: 100%; height: 96px" /></div>
    </div>

    <div v-else-if="error" class="card card-pad" role="alert">
      <p>{{ error }}</p>
      <button type="button" class="btn btn-secondary" @click="load">重试</button>
    </div>

    <div v-else-if="sortedRows.length" class="grid grid-2 contest-grid">
      <div v-for="c in sortedRows" :key="c.id" class="card card-hover card-pad contest-card">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-3)">
          <span class="platform-tag" :class="platformClass(c.platform)">{{ c.platform_display }}</span>
          <span v-if="c.is_rated" class="badge badge-success">Rated</span>
          <span v-else-if="c.is_paid" class="badge badge-warning">付费</span>
          <span v-else class="badge badge-muted">非 Rated</span>
        </div>
        <a v-if="c.url" :href="c.url" target="_blank" rel="noopener" class="contest-name">{{ c.name }}</a>
        <div v-else class="contest-name">{{ c.name }}</div>
        <div class="caption text-tertiary" style="margin: 4px 0 var(--space-3)">{{ c.series || '—' }}</div>
        <div class="contest-meta">
          <span><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2" /><path d="M16 2v4M8 2v4M3 10h18" /></svg>{{ fmtDate(c.start_time) }}</span>
          <span class="num">难度 {{ c.difficulty_factor }}</span>
          <span class="num">有效 {{ c.valid_participant_count ?? '—' }} 人</span>
        </div>
      </div>
    </div>

    <EmptyState v-else title="暂无比赛" hint="换个筛选条件试试" />

    <DataPagination v-if="!error && total > 0" v-model:page="page" :page-size="pageSize" :total="total" />
  </div>
</template>

<style scoped>
.contest-grid {
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  margin-bottom: var(--space-6);
}
.contest-card {
  display: flex;
  flex-direction: column;
}
.contest-name {
  font-family: var(--font-display);
  font-size: 17px;
  font-weight: 600;
  color: var(--ink);
  line-height: 1.4;
}
.contest-name:hover {
  color: var(--color-primary);
}
.contest-meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-4);
  font-size: 13px;
  color: var(--color-text-secondary);
}
.contest-meta span {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
</style>
