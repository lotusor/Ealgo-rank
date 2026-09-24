<script setup lang="ts">
/**
 * 竞赛日历（阶段 3）。
 *
 * 三块结构：
 *  - 焦点区：全局「下一场开赛」倒计时 + 「正在进行」进度条（不受当前月份影响）；
 *  - 月历：整月排期网格（固定 6×7，切月不跳高），点某天在下方就地展开当日赛事；
 *  - 列表：三段式看板（正在进行 / 即将开始 / 已经结束）。
 *
 * 数据来源：
 *  - `GET /contests/?include_calendar=1` —— 月历与三段列表。**未开赛的场次在站内
 *    只以「日历排期行」存在**（每日 03:00 由 clist.by 聚合排期同步，往后 90 天），
 *    公共比赛列表默认不含它们，所以这里必须显式带上这个参数。
 *  - `GET /contests/meta/` —— 平台、系列、各状态计数与最近同步时间。
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
import type { Contest, ContestMeta, PageQuery } from '@/api/types'
import CalendarHero from '@/components/CalendarHero.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import SegmentedControl from '@/components/ui/SegmentedControl.vue'
import {
  WEEKDAYS,
  contestStatus,
  formatDateTime as fmtDateTime,
  formatDayMonth as fmtDayMonth,
  formatDuration as fmtDuration,
  formatTime as fmtTime,
  platformTagClass,
  rangeLabel,
  relativeLabel,
  rowBadge as rowBadgeOf,
  scheduledRatedTag,
} from '@/utils/format'

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

// ---------- 实时时钟（分钟粒度） ----------
/**
 * 页面级派生（状态徽标、42 格网格、相对时间）按分钟对齐即可，也更便宜：`now`
 * 一变这些全要重算。秒级跳动只属于焦点区，它已拆成独立组件、自带 1s 时钟。
 */
const now = ref(new Date())
let tickTimer: number | undefined
let minuteTicks = 0

function scheduleTick() {
  window.clearTimeout(tickTimer)
  const d = new Date()
  const ms = (60 - d.getSeconds()) * 1000 - d.getMilliseconds()
  tickTimer = window.setTimeout(() => {
    now.value = new Date()
    minuteTicks += 1
    // 焦点区每 5 分钟重取一次：排期本身变化不频繁，而这是匿名落地页，每分钟
    // 打两个请求纯属浪费。「开赛 / 结束」的切换不依赖这次请求，由上面的分钟
    // 时钟本地派生即可。
    if (minuteTicks % 5 === 0) loadFocus()
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

// ---------- 焦点区（下一场 / 正在进行 / 赛程总览） ----------
/**
 * 独立于当前月窗口的全局「最近要赛的」：月历翻到 11 月时，焦点区仍要显示下周
 * 那场，否则这一栏在最该有内容的月份反而是空的。渲染与秒级时钟都在 CalendarHero
 * 内部，这里只负责取数。
 */
const liveRows = ref<Contest[]>([])
const soonRows = ref<Contest[]>([])

async function loadFocus() {
  try {
    const [ongoing, upcoming] = await Promise.all([
      listContests({
        include_calendar: 1,
        status: 'ongoing',
        ordering: 'end_time',
        page_size: 5,
      }),
      listContests({
        include_calendar: 1,
        status: 'upcoming',
        ordering: 'start_time',
        page_size: 8,
      }),
    ])
    liveRows.value = ongoing.results
    soonRows.value = upcoming.results
  } catch {
    // 一次网络抖动不该把已经显示出来的焦点区整块抹掉（那会重放入场动画）
  }
}

const nextUpcoming = computed(() => soonRows.value[0] ?? null)
const liveContest = computed(() => liveRows.value[0] ?? null)

/** 页面级派生统一按分钟粒度的 `now` 计算（秒级只属于焦点区） */
const statusOf = (c: Contest) => contestStatus(c, now.value.getTime())
const relLabel = (c: Contest) => relativeLabel(c, now.value.getTime())
/** 行徽标组：状态 + 未结束赛事的计分预判。合成一个数组，模板里只算一次。 */
const rowBadges = (c: Contest): { text: string; cls: string }[] => {
  const at = now.value.getTime()
  const tags = [rowBadgeOf(c, at)]
  const rated = scheduledRatedTag(c, at)
  if (rated) tags.push(rated)
  return tags
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
        include_calendar: 1, // 未开赛的官方排期只有日历页看，别的页面默认不含
        start_before: last.toISOString(),
        end_after: first.toISOString(),
        ordering: 'start_time',
      })
    } else {
      const [ongoing, upcoming, finished] = await Promise.all([
        fetchAll({ include_calendar: 1, status: 'ongoing', ordering: 'end_time' }),
        fetchAll({ include_calendar: 1, status: 'upcoming', ordering: 'start_time' }),
        // 已结束也要带排期行：一场比赛刚结束到被正常爬取转正之间有最长约 24h
        // 的窗口，不带的话它会从「正在进行」凭空消失一整天
        fetchAll({ include_calendar: 1, status: 'finished', ordering: '-end_time' }),
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
  loadFocus()
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

/**
 * 单元格的可访问名称：号数 + 是否今天 + 场次与平台。
 * 窄屏下格内文字会退化成圆点（只靠颜色区分平台），读屏用户改由这条标签获取
 * 同样的信息，A9「颜色不作唯一通道」由此成立。
 */
function cellAriaLabel(cell: DayCell): string {
  const head = `${cell.date.getMonth() + 1} 月 ${cell.date.getDate()} 日${cell.isToday ? '（今天）' : ''}`
  if (!cell.items.length) return `${head}，无赛事`
  const plats = cell.items.map((c) => c.platform_display).join('、')
  return `${head}，${cell.items.length} 场：${plats}`
}

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
            &nbsp;·&nbsp; 已收录 {{ meta.catalog }} 场 &nbsp;·&nbsp; 最近同步
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

    <!-- ============ 焦点区：下一场开赛 / 正在进行 / 赛程总览 ============ -->
    <CalendarHero
      :next="nextUpcoming"
      :live="liveContest"
      :live-count="liveRows.length"
      :meta="meta"
    />

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
          title="只看平台计分场次；未开赛的按各源公布的计分区间/命名预判，赛后以平台真实结算为准"
          @click="ratedOnly = !ratedOnly"
        >
          仅 Rated
          <span v-if="meta?.rated" class="cal-chip-count">{{ meta.rated }}</span>
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
        <select
          v-if="seriesOptions.length"
          v-model="series"
          class="input cal-series"
          aria-label="按系列筛选"
        >
          <option value="">全部系列</option>
          <option v-for="s in seriesOptions" :key="s" :value="s">{{ s }}</option>
        </select>
        <div class="input-group cal-search">
          <svg class="input-icon" aria-hidden="true" focusable="false" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" /></svg>
          <input
            v-model="keyword"
            class="input"
            type="search"
            aria-label="按比赛名称搜索"
            placeholder="搜索比赛名称…"
          />
        </div>
        <button v-if="hasFilter" class="btn btn-ghost btn-sm" @click="clearFilters">
          清空筛选
        </button>
      </div>
    </div>

    <div v-if="error" class="alert alert-error cal-alert" role="alert">
      {{ error }}
    </div>

    <!-- 加载骨架：aria-busy 让辅助技术知道这块正在取数 -->
    <div v-if="loading" class="card card-pad" aria-busy="true">
      <span class="skel cal-skel" aria-hidden="true" />
    </div>

    <template v-else>
      <!-- ============ 月历视图 ============ -->
      <template v-if="view === 'month'">
        <section class="card cal-month" aria-labelledby="cal-month-title">
          <div class="cal-month-head">
            <button
              class="btn btn-ghost btn-icon cal-nav-btn"
              type="button"
              aria-label="上一月"
              title="上一月"
              @click="shiftMonth(-1)"
            >
              <svg aria-hidden="true" focusable="false" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 18l-6-6 6-6" /></svg>
            </button>
            <h2 id="cal-month-title" class="cal-month-label">{{ monthLabel }}</h2>
            <button
              class="btn btn-ghost btn-icon cal-nav-btn"
              type="button"
              aria-label="下一月"
              title="下一月"
              @click="shiftMonth(1)"
            >
              <svg aria-hidden="true" focusable="false" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18l6-6-6-6" /></svg>
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
              :aria-label="cellAriaLabel(cell)"
              :aria-pressed="cell.key === selectedDay"
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
                  :class="[platformTagClass(c.platform), { 'is-unrated': !c.is_rated }]"
                  :title="c.name"
                >{{ c.name }}</span>
                <span v-if="cell.items.length > 2" class="cal-more">
                  +{{ cell.items.length - 2 }}
                </span>
              </span>
              <!-- 圆点仅供 sighted 用户快速分辨（形状已按平台区分，不只靠颜色）；
                   读屏由单元格自身的 aria-label 承载同一信息 -->
              <span class="cal-cell-dots" aria-hidden="true">
                <i
                  v-for="c in cell.items.slice(0, 4)"
                  :key="c.id"
                  :class="platformTagClass(c.platform)"
                />
              </span>
            </button>
          </div>
        </section>

        <section class="card card-pad cal-day" aria-labelledby="cal-day-title">
          <div class="cal-day-head">
            <h2 id="cal-day-title" class="cal-day-title">{{ selectedDayLabel }}</h2>
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
              <span v-if="relLabel(c)" class="cal-rel num">{{ relLabel(c) }}</span>
              <span
                v-for="b in rowBadges(c)"
                :key="b.text"
                class="badge"
                :class="b.cls"
              >{{ b.text }}</span>
              <a
                v-if="c.url"
                :href="c.url"
                target="_blank"
                rel="noopener"
                class="cal-day-link"
              >前往比赛</a>
            </li>
          </ul>
          <EmptyState
            v-else
            title="当天没有赛事"
            hint="赛程来自 clist.by 聚合排期，每日 03:00 同步、往后看 90 天；换一天看看，或切到列表视图浏览近期赛程"
          />
        </section>
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
                <span v-if="relLabel(c)" class="cal-rel num">{{ relLabel(c) }}</span>
                <span v-else class="caption text-tertiary">{{ fmtDuration(c.duration_minutes) }}</span>
              </div>
              <span
                v-for="b in rowBadges(c)"
                :key="b.text"
                class="badge"
                :class="b.cls"
              >{{ b.text }}</span>
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

/* 相对时间（3 天后开赛 / 40 分后结束） */
.cal-rel {
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--color-accent-cyan);
  white-space: nowrap;
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
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--color-text-tertiary);
  min-width: 28px;
}
.cal-chip {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-full);
  border: 1px solid var(--color-border);
  background: var(--color-bg-elevated);
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
  font-weight: 500;
  cursor: pointer;
  /* P5：只补间 paint 属性；`all` 会把 box-shadow 与尺寸一起拉进逐帧动画 */
  transition:
    color var(--duration-fast) var(--ease-standard),
    background-color var(--duration-fast) var(--ease-standard),
    border-color var(--duration-fast) var(--ease-standard);
}
/* A3：项目全局没有 :focus-visible，这类自绘按钮先就地补上焦点环 */
.cal-chip:focus-visible {
  outline: 2px solid var(--color-primary-text);
  outline-offset: 2px;
}
.cal-chip.active {
  background: var(--color-primary-subtle);
  border-color: var(--color-primary);
  color: var(--color-primary-text);
}
.cal-chip-count {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  font-size: var(--text-2xs);
  /* 原本用 opacity .75 压暗，会把 11px 计数打到 4.5:1 以下；换成真正的层级色 */
  color: var(--color-text-tertiary);
}
.cal-series {
  width: auto;
  min-width: 130px;
}
.cal-search {
  /* 基准（窄屏）独占一行；≥768px 才靠右收回行尾 */
  width: 100%;
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
  margin: 0; /* <h2> 化之后去掉 UA 默认外边距，保持面板头部行高不变 */
  font-size: var(--text-lg);
  font-weight: 700;
  color: var(--color-text-primary);
  min-width: 118px;
  text-align: center;
}
/* R4：月份切换是移动端唯一的翻页手段，命中区抬到 44px 一档 */
.cal-nav-btn {
  min-width: var(--control-height-lg);
  min-height: var(--control-height-lg);
}
.cal-month-hint {
  margin-left: auto;
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}
.cal-weekdays {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: var(--space-1);
  margin-bottom: var(--space-1);
}
.cal-weekdays span {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  text-align: center;
}
.cal-grid {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: var(--space-1);
}
.cal-cell {
  /* 基准服务窄屏（R1 移动优先）：矮格 + 圆点，≥768px 再长高换文字 */
  min-width: 0;
  min-height: 52px;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding: var(--space-1);
  text-align: left;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg-surface);
  cursor: pointer;
  /* P5：显式列属性，`all` 会把 box-shadow 拉成逐帧动画 */
  transition:
    background-color var(--duration-fast) var(--ease-standard),
    border-color var(--duration-fast) var(--ease-standard),
    transform var(--duration-fast) var(--ease-standard),
    box-shadow var(--duration-fast) var(--ease-standard);
}
.cal-cell:focus-visible {
  outline: 2px solid var(--color-primary-text);
  outline-offset: 2px;
}
.cal-cell.is-out {
  /* 非本月靠更深的底与更弱的层级色退到背景后，不用整层 opacity——那会把
     格内文字压到 4.5:1 以下（A4），且连同圆点一起失去可辨识度 */
  background: var(--color-bg-inset);
  border-color: transparent;
}
.cal-cell.is-out .cal-cell-day {
  color: var(--color-text-tertiary);
}
.cal-cell.is-today {
  border-color: var(--color-primary);
  /* 今日环标：42 格里第一眼要落在它上面，靠外发光而不是靠加粗 */
  box-shadow: var(--shadow-glow);
}
.cal-cell.is-selected {
  border-color: var(--color-primary);
  background: var(--color-primary-subtle);
}
.cal-cell-day {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
}
.cal-cell.is-today .cal-cell-day {
  color: var(--color-primary-text);
  font-weight: 700;
}
.cal-cell-events {
  /* 基准（窄屏）隐藏：7 列放不下文字，只留圆点；≥768px 换回文字 */
  display: none;
  flex-direction: column;
  gap: var(--space-05);
  min-width: 0;
}
.cal-event {
  font-size: var(--text-2xs);
  line-height: 1.5;
  padding: var(--space-05) var(--space-1);
  border-radius: var(--radius-sm);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}
/* A4：色块上的文字一律用「文本安全色」档（实测 ≥ 4.5:1），语义原色只做填充 */
.cal-event.cf {
  background: color-mix(in srgb, var(--color-info) 18%, transparent);
  color: var(--color-info-text);
}
.cal-event.atcoder {
  background: color-mix(in srgb, var(--color-warning) 18%, transparent);
  color: var(--color-warning-text);
}
.cal-event.nowcoder {
  background: color-mix(in srgb, var(--color-success) 18%, transparent);
  color: var(--color-success-text);
}
.cal-event.is-unrated {
  /* 官方已宣布不计分的排期：去填充 + 空心描边，与同格里的计分场次一眼区分。
     原先用整层 opacity .55 做降级，实测把文字对比打到 1.88:1（A4 违规），
     描边本身已经足够表意，不再压透明度 */
  background: transparent;
  box-shadow: inset 0 0 0 1px color-mix(in srgb, currentColor 45%, transparent);
}
.cal-more {
  font-size: var(--text-2xs);
  color: var(--color-text-tertiary);
}
/* 窄屏只留圆点，避免格内文字挤爆 */
.cal-cell-dots {
  display: flex;
  gap: var(--space-05);
  flex-wrap: wrap;
}
.cal-cell-dots i {
  width: 6px;
  height: 6px;
}
/* A9：三种平台给三种形状（方/菱/环），色觉障碍或灰度屏下也分得出来 */
.cal-cell-dots i.cf {
  background: var(--color-info);
  border-radius: 0;
}
.cal-cell-dots i.atcoder {
  background: var(--color-warning);
  border-radius: 0;
  transform: rotate(45deg);
}
.cal-cell-dots i.nowcoder {
  background: transparent;
  border: 1px solid var(--color-success);
  border-radius: 50%;
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
  margin: 0; /* 现在它是 <h2>，去掉 UA 默认外边距，交给 flex 的 gap */
  font-size: var(--text-md);
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
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--color-text-primary);
}
.cal-day-link {
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--color-primary-text);
  white-space: nowrap;
  /* R4：行内文字链接靠上下 padding 把命中区撑到 44px 一档 */
  padding: var(--space-2) 0;
}
.cal-day-link:focus-visible {
  outline: 2px solid var(--color-primary-text);
  outline-offset: 2px;
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
  font-size: var(--text-sm);
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
/* R5：触屏没有 hover，悬停增强一律包进 (hover: hover) */
@media (hover: hover) {
  .cal-list-item:hover {
    background: var(--color-bg-overlay);
  }
  .cal-chip:hover {
    border-color: var(--color-border-focus);
    color: var(--color-text-primary);
  }
  .cal-cell:hover {
    border-color: var(--color-border-focus);
    background: var(--color-bg-elevated);
    /* 一次性浮起：告诉用户「这格可以点」，与 .card-hover 同一套手感 */
    transform: translateY(-2px);
    box-shadow: var(--shadow-md);
  }
  a.cal-list-name:hover {
    color: var(--color-primary-text);
  }
}
.cal-list-main {
  flex: 1;
  min-width: 0;
}
.cal-list-name {
  display: block;
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.cal-list-time {
  display: flex;
  flex-direction: column;
  align-items: flex-start; /* 窄屏靠左排，≥768px 再收到右侧 */
  gap: var(--space-05);
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
  padding: var(--space-4);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-lg);
  font-size: var(--text-sm);
  color: var(--color-text-tertiary);
}

/* 错误条与骨架的尺寸原先写在模板内联 style 里，挪回样式表（M7） */
.cal-alert {
  margin-bottom: var(--space-5);
}
.cal-skel {
  display: block;
  width: 100%;
  height: 320px;
}

/* ---------- 入场（板块级错峰，不给每行铺动画） ---------- */
/* 与 components.css 的 .card-rise 同一套手感，但数据异步到达后「板块依次浮起」
   才贴合这张页的节奏：月历/当日列表/三段看板各差 40ms，一次性、不循环。 */
@keyframes cal-rise {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
.cal-month,
.cal-day,
.cal-section {
  animation: cal-rise var(--duration-slower) var(--ease-out) backwards;
}
.cal-day {
  animation-delay: var(--stagger-2);
}
.cal-section:nth-of-type(2) {
  animation-delay: var(--stagger-1);
}
.cal-section:nth-of-type(3) {
  animation-delay: var(--stagger-3);
}

/* ---------- 触屏命中区（R4） ---------- */
@media (pointer: coarse) {
  .cal-chip {
    min-height: var(--control-height-lg);
  }
}

/* ---------- 响应式（R1 移动优先：基准 = 360px 形态，下面只做增强） ----------
   断点唯一事实源见 tokens.css --bp-md，改值得同步改这里 */
@media (min-width: 768px) {
  .cal-cell {
    min-height: 78px;
  }
  /* 宽屏格内放得下文字，圆点让位 */
  .cal-cell-events {
    display: flex;
  }
  .cal-cell-dots {
    display: none;
  }
  .cal-month-hint {
    display: block;
  }
  .cal-search {
    width: auto;
    min-width: 180px;
    margin-left: auto;
  }
  .cal-list-time {
    align-items: flex-end;
  }
}
</style>
