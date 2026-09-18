<script setup lang="ts">
/**
 * 竞赛日历（阶段 3）。
 *
 * 双视图（参考 LeetCode 一类站点）：
 *  - 月历：整月排期网格，点某天在下方就地展开当日赛事，不跳页；
 *  - 列表：参考 algowiki 的三段式看板（正在进行 / 即将开始 / 已经结束）。
 *
 * 数据来源（阶段 2 已就绪）：
 *  - `GET /contests/` 支持 status / end_after / end_before / series / search / ordering
 *  - `GET /contests/meta/` 提供平台、系列、各状态计数与最近同步时间
 *
 * 筛选分工：时间窗口与状态走**服务端**（避免拉全量），
 * 平台（多选）/ 仅 Rated / 系列 / 关键字走**客户端**（数据量小、响应即时）。
 *
 * 时间口径：一律按**浏览器本地时区**渲染，并在页头显式标注时区；
 * 跨日赛事标注 (+n)，避免"比赛到底哪天"的歧义。
 */
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { fetchContestMeta, listContests } from '@/api'
import type { Contest, ContestMeta, ContestPlatform, PageQuery } from '@/api/types'
import EmptyState from '@/components/ui/EmptyState.vue'
import SegmentedControl from '@/components/ui/SegmentedControl.vue'

type ViewMode = 'month' | 'list'
type StatusKey = 'ongoing' | 'upcoming' | 'finished'

const VIEW_OPTIONS = [
  { label: '月历', value: 'month' as const },
  { label: '列表', value: 'list' as const },
]

const STATUS_META: Record<StatusKey, { label: string; cls: string; hint: string }> = {
  ongoing: { label: '正在进行', cls: 'badge-success', hint: '按结束时间升序' },
  upcoming: { label: '即将开始', cls: 'badge-info', hint: '按开始时间升序' },
  finished: { label: '已经结束', cls: 'badge-muted', hint: '按结束时间倒序' },
}

/** 每段/每视图最多展示的条数（超出走「查看全部」跳比赛列表） */
const SECTION_LIMIT = 30
/** 单次加载最多翻页数，防止异常数据把页面拖死 */
const MAX_PAGES = 3
const PAGE_SIZE = 60
/**
 * 取数上限。**必须显著大于 SECTION_LIMIT**：取数时就卡在 SECTION_LIMIT 的话，
 * 无法判断"是否被截断"（截断提示永远不会出现）。展示时再切到 SECTION_LIMIT。
 */
const FETCH_CAP = MAX_PAGES * PAGE_SIZE

const route = useRoute()
const router = useRouter()

// ---------- 时间工具 ----------
const WEEKDAYS = ['一', '二', '三', '四', '五', '六', '日']

function startOfMonth(d: Date) {
  return new Date(d.getFullYear(), d.getMonth(), 1)
}
function dayKey(d: Date) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
function monthKey(d: Date) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}
function parseMonthKey(s: string) {
  const m = /^(\d{4})-(\d{2})$/.exec(s)
  if (!m) return null
  const y = Number(m[1])
  const mo = Number(m[2]) - 1
  return mo >= 0 && mo <= 11 ? new Date(y, mo, 1) : null
}

// ---------- 实时时钟（对齐分钟边界递归，页面隐藏时暂停） ----------
const now = ref(new Date())
let tickTimer: number | undefined

function scheduleTick() {
  window.clearTimeout(tickTimer)
  const d = new Date()
  const ms = (60 - d.getSeconds()) * 1000 - d.getMilliseconds()
  tickTimer = window.setTimeout(() => {
    now.value = new Date()
    scheduleTick()
  }, Math.max(ms, 1000))
}
function onVisibilityChange() {
  if (document.hidden) {
    window.clearTimeout(tickTimer)
  } else {
    now.value = new Date()
    scheduleTick()
  }
}

// ---------- 筛选状态 ----------
const view = ref<ViewMode>('month')
const platforms = ref<string[]>([])
const ratedOnly = ref(false)
const series = ref('')
const keyword = ref('')
const statusFilter = ref<'all' | StatusKey>('all')
const cursor = ref(startOfMonth(new Date()))
const selectedDay = ref('')

const routeQuery = route.query
if (routeQuery.view === 'list') view.value = 'list'
if (typeof routeQuery.platform === 'string' && routeQuery.platform) {
  platforms.value = routeQuery.platform.split(',').filter(Boolean)
}
ratedOnly.value = routeQuery.rated === '1'
if (typeof routeQuery.series === 'string') series.value = routeQuery.series
if (typeof routeQuery.keyword === 'string') keyword.value = routeQuery.keyword
if (
  routeQuery.status === 'ongoing' ||
  routeQuery.status === 'upcoming' ||
  routeQuery.status === 'finished'
) {
  statusFilter.value = routeQuery.status
}
if (typeof routeQuery.month === 'string') {
  const parsed = parseMonthKey(routeQuery.month)
  if (parsed) cursor.value = parsed
}
selectedDay.value =
  monthKey(cursor.value) === monthKey(now.value) ? dayKey(now.value) : dayKey(cursor.value)

let queryTimer: number | undefined
function syncQuery() {
  window.clearTimeout(queryTimer)
  queryTimer = window.setTimeout(() => {
    const q: Record<string, string> = {}
    if (view.value !== 'month') q.view = view.value
    if (platforms.value.length) q.platform = platforms.value.join(',')
    if (ratedOnly.value) q.rated = '1'
    if (series.value) q.series = series.value
    if (keyword.value.trim()) q.keyword = keyword.value.trim()
    if (statusFilter.value !== 'all') q.status = statusFilter.value
    if (monthKey(cursor.value) !== monthKey(now.value)) q.month = monthKey(cursor.value)
    router.replace({ query: q })
  }, 300)
}

watch([view, platforms, ratedOnly, series, keyword, statusFilter, cursor], syncQuery, {
  deep: true,
})

// ---------- 数据加载 ----------
const meta = ref<ContestMeta | null>(null)
const monthRows = ref<Contest[]>([])
const buckets = ref<Record<StatusKey, Contest[]>>({ ongoing: [], upcoming: [], finished: [] })
const loading = ref(false)
const error = ref('')

/** 按查询条件翻页取数（有上限，避免异常数据拖死页面） */
async function fetchAll(params: PageQuery, cap = FETCH_CAP): Promise<Contest[]> {
  const out: Contest[] = []
  let page = 1
  while (page <= MAX_PAGES) {
    const res = await listContests({ ...params, page, page_size: PAGE_SIZE })
    out.push(...res.results)
    if (!res.results.length || out.length >= res.count || page >= res.total_pages) break
    page += 1
  }
  return out.slice(0, cap)
}

async function loadMeta() {
  try {
    meta.value = await fetchContestMeta()
  } catch {
    meta.value = null // 筛选条退化为固定平台列表
  }
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    if (view.value === 'month') {
      const first = cursor.value
      const last = new Date(first.getFullYear(), first.getMonth() + 1, 0, 23, 59, 59)
      // 跨月赛事：开始时间早于月末、且结束时间晚于月初
      monthRows.value = await fetchAll({
        start_before: last.toISOString(),
        end_after: first.toISOString(),
        ordering: 'start_time',
      })
    } else {
      const [ongoing, upcoming, finished] = await Promise.all([
        fetchAll({ status: 'ongoing', ordering: 'end_time' }),
        fetchAll({ status: 'upcoming', ordering: 'start_time' }),
        fetchAll({ status: 'finished', ordering: '-end_time' }),
      ])
      buckets.value = { ongoing, upcoming, finished }
    }
  } catch (e) {
    const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    error.value = detail || '加载失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  scheduleTick()
  document.addEventListener('visibilitychange', onVisibilityChange)
  loadMeta()
  load()
})
onUnmounted(() => {
  window.clearTimeout(tickTimer)
  window.clearTimeout(queryTimer)
  document.removeEventListener('visibilitychange', onVisibilityChange)
})

// 视图 / 月份切换需要重新取数；纯客户端筛选不触发请求
watch([view, cursor], () => load())

// ---------- 客户端筛选 ----------
const platformOptions = computed(() => {
  const fromMeta = meta.value?.platforms
  if (fromMeta?.length) return fromMeta
  return [
    { key: 'codeforces', label: 'Codeforces', count: 0 },
    { key: 'atcoder', label: 'AtCoder', count: 0 },
    { key: 'nowcoder', label: '牛客', count: 0 },
  ]
})

const seriesOptions = computed(() => meta.value?.series ?? [])

const kw = computed(() => keyword.value.trim().toLowerCase())

function matches(c: Contest): boolean {
  if (platforms.value.length && !platforms.value.includes(c.platform)) return false
  if (ratedOnly.value && !c.is_rated) return false
  if (series.value && c.series !== series.value) return false
  if (kw.value) {
    const hay = `${c.name} ${c.series ?? ''}`.toLowerCase()
    if (!hay.includes(kw.value)) return false
  }
  if (statusFilter.value !== 'all' && statusOf(c) !== statusFilter.value) return false
  return true
}

function togglePlatform(key: string) {
  const i = platforms.value.indexOf(key)
  if (i >= 0) platforms.value.splice(i, 1)
  else platforms.value.push(key)
}

function clearFilters() {
  platforms.value = []
  ratedOnly.value = false
  series.value = ''
  keyword.value = ''
  statusFilter.value = 'all'
}

const hasFilter = computed(
  () =>
    platforms.value.length > 0 ||
    ratedOnly.value ||
    !!series.value ||
    !!kw.value ||
    statusFilter.value !== 'all',
)

// ---------- 状态派生（不落库，按当前时间计算） ----------
function statusOf(c: Contest): StatusKey {
  const t = now.value.getTime()
  const s = c.start_time ? new Date(c.start_time).getTime() : null
  const e = c.end_time ? new Date(c.end_time).getTime() : null
  if (e !== null && e <= t) return 'finished'
  if (s !== null && s > t) return 'upcoming'
  if (s !== null && e !== null && s <= t && e > t) return 'ongoing'
  return 'finished'
}

// ---------- 月历视图 ----------
const filteredMonthRows = computed(() => monthRows.value.filter(matches))

const byDay = computed(() => {
  const map = new Map<string, Contest[]>()
  for (const c of filteredMonthRows.value) {
    if (!c.start_time) continue
    const k = dayKey(new Date(c.start_time))
    const arr = map.get(k)
    if (arr) arr.push(c)
    else map.set(k, [c])
  }
  for (const arr of map.values()) {
    arr.sort((a, b) => (a.start_time ?? '').localeCompare(b.start_time ?? ''))
  }
  return map
})

interface DayCell {
  date: Date
  key: string
  inMonth: boolean
  isToday: boolean
  items: Contest[]
}

/** 固定 6 周 × 7 天，周一起始，保证月切换时网格高度不跳动 */
const monthGrid = computed<DayCell[]>(() => {
  const first = cursor.value
  const offset = (first.getDay() + 6) % 7
  const gridStart = new Date(first)
  gridStart.setDate(first.getDate() - offset)
  const todayKey = dayKey(now.value)
  const cells: DayCell[] = []
  for (let i = 0; i < 42; i += 1) {
    const d = new Date(gridStart)
    d.setDate(gridStart.getDate() + i)
    const key = dayKey(d)
    cells.push({
      date: d,
      key,
      inMonth: d.getMonth() === first.getMonth(),
      isToday: key === todayKey,
      items: byDay.value.get(key) ?? [],
    })
  }
  return cells
})

const monthLabel = computed(
  () => `${cursor.value.getFullYear()} 年 ${cursor.value.getMonth() + 1} 月`,
)

const dayItems = computed(() => byDay.value.get(selectedDay.value) ?? [])

const selectedDayLabel = computed(() => {
  const d = new Date(`${selectedDay.value}T00:00:00`)
  if (Number.isNaN(d.getTime())) return '当日赛事'
  const wd = WEEKDAYS[(d.getDay() + 6) % 7]
  return `${d.getMonth() + 1} 月 ${d.getDate()} 日 周${wd}`
})

function shiftMonth(delta: number) {
  const d = cursor.value
  cursor.value = new Date(d.getFullYear(), d.getMonth() + delta, 1)
  selectedDay.value = dayKey(cursor.value)
}

function goToday() {
  cursor.value = startOfMonth(now.value)
  selectedDay.value = dayKey(now.value)
  syncQuery()
}

// ---------- 列表视图 ----------
/**
 * 三段式看板。
 *
 * 三个 bucket 是按加载时刻的状态拉取的，但**分组在客户端按当前时间重算**
 * （配合实时时钟）：否则一场 20:00 开始的比赛会一直停在「即将开始」，
 * 直到用户手动刷新。跨 bucket 的重复项按 id 去重。
 */
const bucketUnion = computed(() => {
  const seen = new Map<number, Contest>()
  for (const key of ['ongoing', 'upcoming', 'finished'] as StatusKey[]) {
    for (const c of buckets.value[key]) seen.set(c.id, c)
  }
  return [...seen.values()]
})

const SORTERS: Record<StatusKey, (a: Contest, b: Contest) => number> = {
  ongoing: (a, b) => (a.end_time ?? '').localeCompare(b.end_time ?? ''),
  upcoming: (a, b) => (a.start_time ?? '').localeCompare(b.start_time ?? ''),
  finished: (a, b) => (b.end_time ?? '').localeCompare(a.end_time ?? ''),
}

const listSections = computed(() => {
  // 选定具体状态时只渲染该段，避免另两段顶着空态占版面
  const keys: StatusKey[] =
    statusFilter.value === 'all'
      ? ['ongoing', 'upcoming', 'finished']
      : [statusFilter.value]
  return keys.map((key) => {
    const matched = bucketUnion.value
      .filter((c) => statusOf(c) === key && matches(c))
      .sort(SORTERS[key])
    return {
      key,
      ...STATUS_META[key],
      items: matched.slice(0, SECTION_LIMIT),
      /** 是否因条数上限被截断 */
      truncated: matched.length > SECTION_LIMIT,
    }
  })
})

// ---------- 展示辅助 ----------
const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone

function fmtTime(iso: string | null) {
  if (!iso) return '—'
  return new Date(iso).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}
function fmtDayMonth(iso: string | null) {
  if (!iso) return '—'
  const d = new Date(iso)
  return `${d.getMonth() + 1}/${d.getDate()}`
}
function fmtDuration(min: number | null) {
  if (!min || min <= 0) return '—'
  const h = Math.floor(min / 60)
  const m = min % 60
  if (h && m) return `${h}h ${String(m).padStart(2, '0')}m`
  return h ? `${h}h` : `${m}m`
}
/** 跨了几个自然日（按本地时区） */
function crossDays(c: Contest) {
  if (!c.start_time || !c.end_time) return 0
  const a = new Date(c.start_time)
  const b = new Date(c.end_time)
  const da = new Date(a.getFullYear(), a.getMonth(), a.getDate()).getTime()
  const db = new Date(b.getFullYear(), b.getMonth(), b.getDate()).getTime()
  return Math.max(0, Math.round((db - da) / 86400000))
}
function rangeLabel(c: Contest) {
  if (!c.start_time) return '时间待定'
  if (!c.end_time) return `${fmtDayMonth(c.start_time)} ${fmtTime(c.start_time)} 起`
  const n = crossDays(c)
  const base = `${fmtDayMonth(c.start_time)} ${fmtTime(c.start_time)} – ${fmtTime(c.end_time)}`
  return n > 0 ? `${base}（+${n}）` : base
}
function platformTagClass(p: ContestPlatform) {
  return p === 'codeforces' ? 'cf' : p === 'atcoder' ? 'atcoder' : 'nowcoder'
}
function fmtSyncTime(iso: string | null) {
  if (!iso) return '未知'
  return new Date(iso).toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}
</script>

<template>
  <div class="container-wide">
    <div class="page-head">
      <div>
        <div class="breadcrumb"><span>竞赛日历</span></div>
        <h1 class="page-title">竞赛日历</h1>
        <p class="page-subtitle">
          Codeforces · AtCoder · 牛客 三平台赛程
          <template v-if="meta">
            &nbsp;·&nbsp; 共 {{ meta.total }} 场 &nbsp;·&nbsp; 最近同步
            {{ fmtSyncTime(meta.latest_sync_at) }}
          </template>
          &nbsp;·&nbsp; 时间按本地时区 {{ timeZone }} 显示
        </p>
      </div>
      <div class="cal-head-actions">
        <SegmentedControl v-model="view" :options="VIEW_OPTIONS" />
        <button v-if="view === 'month'" class="btn btn-secondary btn-sm" @click="goToday">
          回到今天
        </button>
      </div>
    </div>

    <!-- 筛选条 -->
    <div class="cal-filters">
      <div class="cal-filter-row">
        <span class="cal-filter-label">平台</span>
        <button
          v-for="p in platformOptions"
          :key="p.key"
          type="button"
          class="cal-chip"
          :class="{ active: platforms.includes(p.key) }"
          @click="togglePlatform(p.key)"
        >
          {{ p.label }}
          <span v-if="p.count" class="cal-chip-count">{{ p.count }}</span>
        </button>
        <button
          type="button"
          class="cal-chip"
          :class="{ active: ratedOnly }"
          @click="ratedOnly = !ratedOnly"
        >
          仅 Rated
        </button>
      </div>
      <div class="cal-filter-row">
        <span class="cal-filter-label">状态</span>
        <button
          type="button"
          class="cal-chip"
          :class="{ active: statusFilter === 'all' }"
          @click="statusFilter = 'all'"
        >
          全部
        </button>
        <button
          v-for="(m, k) in STATUS_META"
          :key="k"
          type="button"
          class="cal-chip"
          :class="{ active: statusFilter === k }"
          @click="statusFilter = k"
        >
          {{ m.label }}
        </button>
        <select v-if="seriesOptions.length" v-model="series" class="input cal-series">
          <option value="">全部系列</option>
          <option v-for="s in seriesOptions" :key="s" :value="s">{{ s }}</option>
        </select>
        <div class="input-group cal-search">
          <svg class="input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" /></svg>
          <input v-model="keyword" class="input" type="text" placeholder="搜索比赛名称…" />
        </div>
        <button v-if="hasFilter" class="btn btn-ghost btn-sm" @click="clearFilters">
          清空筛选
        </button>
      </div>
    </div>

    <div v-if="error" class="alert alert-error" style="margin-bottom: var(--space-5)">
      {{ error }}
    </div>

    <!-- 加载骨架 -->
    <div v-if="loading" class="card card-pad">
      <span class="skel" style="width: 100%; height: 320px" />
    </div>

    <template v-else>
      <!-- ============ 月历视图 ============ -->
      <template v-if="view === 'month'">
        <div class="card cal-month">
          <div class="cal-month-head">
            <button class="btn btn-ghost btn-icon" title="上一月" @click="shiftMonth(-1)">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 18l-6-6 6-6" /></svg>
            </button>
            <span class="cal-month-label">{{ monthLabel }}</span>
            <button class="btn btn-ghost btn-icon" title="下一月" @click="shiftMonth(1)">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18l6-6-6-6" /></svg>
            </button>
            <span class="cal-month-hint">点击日期查看当日赛事</span>
          </div>

          <div class="cal-weekdays">
            <span v-for="w in WEEKDAYS" :key="w">{{ w }}</span>
          </div>
          <div class="cal-grid">
            <button
              v-for="cell in monthGrid"
              :key="cell.key"
              type="button"
              class="cal-cell"
              :class="{
                'is-out': !cell.inMonth,
                'is-today': cell.isToday,
                'is-selected': cell.key === selectedDay,
                'has-items': cell.items.length > 0,
              }"
              @click="selectedDay = cell.key"
            >
              <span class="cal-cell-day">{{ cell.date.getDate() }}</span>
              <span class="cal-cell-events">
                <span
                  v-for="c in cell.items.slice(0, 2)"
                  :key="c.id"
                  class="cal-event"
                  :class="platformTagClass(c.platform)"
                  :title="c.name"
                >{{ c.name }}</span>
                <span v-if="cell.items.length > 2" class="cal-more">
                  +{{ cell.items.length - 2 }}
                </span>
              </span>
              <span class="cal-cell-dots">
                <i
                  v-for="c in cell.items.slice(0, 4)"
                  :key="c.id"
                  :class="platformTagClass(c.platform)"
                />
              </span>
            </button>
          </div>
        </div>

        <div class="card card-pad cal-day">
          <div class="cal-day-head">
            <span class="cal-day-title">{{ selectedDayLabel }}</span>
            <span class="caption text-tertiary">
              {{ dayItems.length ? `${dayItems.length} 场` : '无赛事' }}
            </span>
          </div>
          <ul v-if="dayItems.length" class="cal-day-list">
            <li v-for="c in dayItems" :key="c.id" class="cal-day-item">
              <span class="platform-tag" :class="platformTagClass(c.platform)">
                {{ c.platform_display }}
              </span>
              <div class="cal-day-main">
                <div class="cal-day-name">{{ c.name }}</div>
                <div class="caption text-tertiary">
                  {{ rangeLabel(c) }} · {{ fmtDuration(c.duration_minutes) }}
                  <template v-if="c.series"> · {{ c.series }}</template>
                </div>
              </div>
              <span class="badge" :class="STATUS_META[statusOf(c)].cls">
                {{ STATUS_META[statusOf(c)].label }}
              </span>
              <span v-if="c.is_rated" class="badge badge-success">Rated</span>
              <a
                v-if="c.url"
                :href="c.url"
                target="_blank"
                rel="noopener"
                class="cal-day-link"
              >前往比赛</a>
            </li>
          </ul>
          <EmptyState v-else title="当天没有赛事" hint="换一天看看，或切到列表视图浏览近期赛程" />
        </div>
      </template>

      <!-- ============ 列表视图（三段式） ============ -->
      <template v-else>
        <section v-for="sec in listSections" :key="sec.key" class="cal-section">
          <div class="cal-section-head">
            <span class="badge" :class="sec.cls">{{ sec.label }}</span>
            <span class="cal-section-count">{{ sec.items.length }}</span>
            <span class="caption text-tertiary">{{ sec.hint }}</span>
          </div>

          <ul v-if="sec.items.length" class="cal-list">
            <li v-for="c in sec.items" :key="c.id" class="cal-list-item">
              <span class="platform-tag" :class="platformTagClass(c.platform)">
                {{ c.platform_display }}
              </span>
              <div class="cal-list-main">
                <a
                  v-if="c.url"
                  :href="c.url"
                  target="_blank"
                  rel="noopener"
                  class="cal-list-name"
                >{{ c.name }}</a>
                <span v-else class="cal-list-name">{{ c.name }}</span>
                <div class="caption text-tertiary">
                  {{ c.series || '—' }}
                  <template v-if="c.participant_count">
                    · 参赛 {{ c.participant_count }} 人
                  </template>
                </div>
              </div>
              <div class="cal-list-time">
                <span class="num">{{ rangeLabel(c) }}</span>
                <span class="caption text-tertiary">{{ fmtDuration(c.duration_minutes) }}</span>
              </div>
              <span v-if="c.is_rated" class="badge badge-success">Rated</span>
              <span v-else class="badge badge-muted">非 Rated</span>
            </li>
          </ul>
          <div v-else class="cal-empty">
            {{
              hasFilter
                ? '没有符合筛选条件的赛事，试试放宽条件'
                : `暂无${sec.label}的赛事`
            }}
          </div>

          <div v-if="sec.truncated" class="cal-section-foot">
            <span class="caption text-tertiary">仅展示前 {{ SECTION_LIMIT }} 场</span>
            <RouterLink v-if="sec.key === 'finished'" class="link" to="/u/contests">
              在比赛列表中查看全部 →
            </RouterLink>
          </div>
        </section>
      </template>
    </template>
  </div>
</template>

<style scoped>
.cal-head-actions {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-wrap: wrap;
}

/* ---------- 筛选条 ---------- */
.cal-filters {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  margin-bottom: var(--space-5);
}
.cal-filter-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
}
.cal-filter-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-tertiary);
  min-width: 28px;
}
.cal-chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 12px;
  border-radius: var(--radius-full);
  border: 1px solid var(--color-border);
  background: var(--color-bg-elevated);
  color: var(--color-text-secondary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-standard);
}
.cal-chip:hover {
  border-color: var(--color-border-focus);
  color: var(--color-text-primary);
}
.cal-chip.active {
  background: var(--color-primary-subtle);
  border-color: var(--color-primary);
  color: var(--color-primary);
}
.cal-chip-count {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  font-size: 11px;
  opacity: 0.75;
}
.cal-series {
  width: auto;
  min-width: 130px;
}
.cal-search {
  margin-left: auto;
  min-width: 180px;
}

/* ---------- 月历 ---------- */
.cal-month {
  padding: var(--space-4) var(--space-5) var(--space-5);
  margin-bottom: var(--space-5);
}
.cal-month-head {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
}
.cal-month-label {
  font-size: 16px;
  font-weight: 700;
  color: var(--color-text-primary);
  min-width: 118px;
  text-align: center;
}
.cal-month-hint {
  margin-left: auto;
  font-size: 12px;
  color: var(--color-text-tertiary);
}
.cal-weekdays {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 4px;
  margin-bottom: 4px;
}
.cal-weekdays span {
  font-size: 12px;
  color: var(--color-text-tertiary);
  text-align: center;
}
.cal-grid {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 4px;
}
.cal-cell {
  min-width: 0;
  min-height: 78px;
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 5px 6px;
  text-align: left;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg-surface);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-standard);
}
.cal-cell:hover {
  border-color: var(--color-border-focus);
  background: var(--color-bg-elevated);
}
.cal-cell.is-out {
  opacity: 0.42;
}
.cal-cell.is-today {
  border-color: var(--color-primary);
}
.cal-cell.is-selected {
  border-color: var(--color-primary);
  background: var(--color-primary-subtle);
}
.cal-cell-day {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  font-size: 12px;
  color: var(--color-text-secondary);
}
.cal-cell.is-today .cal-cell-day {
  color: var(--color-primary);
  font-weight: 700;
}
.cal-cell-events {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.cal-event {
  font-size: 11px;
  line-height: 1.5;
  padding: 1px 5px;
  border-radius: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}
.cal-event.cf {
  background: color-mix(in srgb, var(--color-info) 18%, transparent);
  color: var(--color-info);
}
.cal-event.atcoder {
  background: color-mix(in srgb, var(--color-warning) 18%, transparent);
  color: var(--color-warning);
}
.cal-event.nowcoder {
  background: color-mix(in srgb, var(--color-success) 18%, transparent);
  color: var(--color-success);
}
.cal-more {
  font-size: 11px;
  color: var(--color-text-tertiary);
}
/* 窄屏只留圆点，避免格内文字挤爆 */
.cal-cell-dots {
  display: none;
  gap: 3px;
  flex-wrap: wrap;
}
.cal-cell-dots i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}
.cal-cell-dots i.cf {
  background: var(--color-info);
}
.cal-cell-dots i.atcoder {
  background: var(--color-warning);
}
.cal-cell-dots i.nowcoder {
  background: var(--color-success);
}

/* ---------- 当日赛事 ---------- */
.cal-day {
  margin-bottom: var(--space-6);
}
.cal-day-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}
.cal-day-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary);
}
.cal-day-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
}
.cal-day-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) 0;
  border-bottom: 1px solid var(--color-divider);
  flex-wrap: wrap;
}
.cal-day-item:last-child {
  border-bottom: none;
}
.cal-day-main {
  flex: 1;
  min-width: 0;
}
.cal-day-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
}
.cal-day-link {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-primary);
  white-space: nowrap;
}

/* ---------- 列表视图 ---------- */
.cal-section {
  margin-bottom: var(--space-6);
}
.cal-section-head {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-3);
}
.cal-section-count {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  font-size: 13px;
  font-weight: 700;
  color: var(--color-text-primary);
}
.cal-list {
  list-style: none;
  margin: 0;
  padding: 0;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  background: var(--color-bg-surface);
}
.cal-list-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--color-divider);
}
.cal-list-item:last-child {
  border-bottom: none;
}
.cal-list-item:hover {
  background: var(--color-bg-overlay);
}
.cal-list-main {
  flex: 1;
  min-width: 0;
}
.cal-list-name {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
a.cal-list-name:hover {
  color: var(--color-primary);
}
.cal-list-time {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 1px;
  white-space: nowrap;
}
.cal-section-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  margin-top: var(--space-3);
  flex-wrap: wrap;
}
/* 段级空态用紧凑单行：整块 EmptyState 会让「正在进行/即将开始」为空时
   占掉大半屏，反而把真正有内容的「已经结束」挤出视野 */
.cal-empty {
  padding: var(--space-4) var(--space-4);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-lg);
  font-size: 13px;
  color: var(--color-text-tertiary);
}

/* ---------- 响应式 ---------- */
@media (max-width: 768px) {
  .cal-search {
    margin-left: 0;
    width: 100%;
  }
  .cal-cell {
    min-height: 52px;
    padding: 4px;
  }
  /* 窄屏用圆点代替格内文字，避免 7 列被挤爆 */
  .cal-cell-events {
    display: none;
  }
  .cal-cell-dots {
    display: flex;
  }
  .cal-month-hint {
    display: none;
  }
  .cal-list-time {
    align-items: flex-start;
  }
}
</style>
