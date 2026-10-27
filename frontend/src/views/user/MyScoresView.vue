<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { listMyParticipations, listRankings, getMyBestRecord, getRatingHistory } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { useResource } from '@/composables/useResource'
import type { MyParticipation, ContestPlatform, RankSnapshot, UserBestRecord, RatingHistoryPoint } from '@/api/types'
import RatingLineChart from '@/components/RatingLineChart.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import SegmentedControl from '@/components/ui/SegmentedControl.vue'
import CountUp from '@/components/ui/CountUp.vue'
import DataPagination from '@/components/ui/DataPagination.vue'
import { initial } from '@/utils/format'
import { SCORING_PLATFORMS, platformClass, platformLabel } from '@/platforms/meta'

const router = useRouter()
const auth = useAuthStore()

const platform = ref<'' | ContestPlatform>('')
const tablePage = ref(1)
const tablePageSize = 20

const records = useResource(async ({ isCurrent }) => {
  const selectedPlatform = platform.value || undefined
  const allRows: MyParticipation[] = []
  // 分页合同只有 total_pages：逐页收齐后一次性发布，避免把部分页当全量统计
  for (let page = 1; ; page += 1) {
    const res = await listMyParticipations({ platform: selectedPlatform, page, page_size: 100 })
    if (!isCurrent()) return []
    allRows.push(...res.results)
    if (page >= res.total_pages) break
  }
  return allRows
}, {
  initial: [] as MyParticipation[],
  watch: [platform],
  reset: () => { tablePage.value = 1 },
})

const rows = records.data
const loading = records.loading
const error = computed(() => (records.error.value ? '参赛记录加载失败，请重试。' : ''))
const pagedRows = computed(() =>
  rows.value.slice((tablePage.value - 1) * tablePageSize, tablePage.value * tablePageSize),
)

// 成绩维度只对可计分平台有意义（只做日历展示的平台没有榜单）
const platformOptions = computed(() => [
  { label: '全部', value: '' as const },
  ...SCORING_PLATFORMS.map((p) => ({ label: p.label, value: p.key })),
])

onMounted(() => {
  loadRank()
  getMyBestRecord().then((r) => (bestRecord.value = r)).catch(() => {})
  getRatingHistory().then((h) => (history.value = h)).catch(() => {})
})

// 历史最佳纪录（学生榜 period=all：最高名次配对当时总 rating + 历史最高总 rating）
const bestRecord = ref<UserBestRecord | null>(null)

const myRank = ref<RankSnapshot | null>(null)
const rankLoading = ref(false)

function loadRank() {
  const uid = me.value?.id
  if (!uid) return
  rankLoading.value = true
  listRankings({ scope: 'student', period: 'all', user: uid, page_size: 50 })
    .then(({ results }) => {
      myRank.value =
        results.find((r) => r.user === uid && r.period === 'all') ||
        results[0] ||
        null
    })
    .catch(() => {})
    .finally(() => (rankLoading.value = false))
}

const me = computed(() => auth.user)
const avatarFailed = ref(false)
watch(() => me.value?.avatar, () => (avatarFailed.value = false))

const unexcludedCount = computed(() => rows.value.filter((r) => !r.is_excluded).length)
const totalDelta = computed(() => rows.value.reduce((s, r) => s + (r.rating_delta ?? 0), 0))

// 站点 rating 时间线（后端单一事实源，与榜单口径一致；替代旧的前端聚合）
const history = ref<RatingHistoryPoint[]>([])
const currentRating = computed(() => {
  if (platform.value === '') {
    return history.value.length
      ? Math.round(history.value[history.value.length - 1].rating * 10) / 10
      : null
  }
  const rated = rows.value
    .filter((r) => r.new_rating != null && r.contest_start_time)
    .sort((a, b) => new Date(a.contest_start_time!).getTime() - new Date(b.contest_start_time!).getTime())
  return rated.length ? rated[rated.length - 1].new_rating : null
})
const peakRating = computed(() => {
  if (platform.value === '') {
    return history.value.length
      ? Math.round(Math.max(...history.value.map((h) => h.rating)) * 10) / 10
      : null
  }
  const vals = rows.value.map((r) => r.new_rating).filter((v): v is number => v != null)
  return vals.length ? Math.max(...vals) : null
})

const CHART_WINDOW_DAYS = 365

/** 当前平台全部可画的官方 rating 行（时间升序，未截展示窗口） */
const platformRatingRows = computed(() =>
  rows.value
    .filter((r) => r.new_rating != null && r.contest_start_time != null)
    .sort(
      (a, b) =>
        new Date(a.contest_start_time!).getTime() - new Date(b.contest_start_time!).getTime(),
    ),
)

function withinWindow(iso: string) {
  return new Date(iso).getTime() >= Date.now() - CHART_WINDOW_DAYS * 86400000
}

const chartPoints = computed(() => {
  // 「全部」tab：站点 rating 时间线（后端 /rating-history/，含新号先验与滑动
  // 窗口，与榜单完全同口径）；单平台 tab：该平台官方原始 new_rating 序列。
  if (platform.value === '') {
    return history.value.map((h, i) => ({
      label: h.contest_time,
      value: Math.round(h.rating * 10) / 10,
      meta: {
        contest: h.contest_name,
        platform: h.platform,
        delta: i > 0
          ? Math.round((h.rating - history.value[i - 1].rating) * 10) / 10
          : null,
        rank: h.rank ?? null,
      },
    }))
  }
  // 折线图只展示最近一年的波动（2026-09-13，与「全部」tab 口径一致）
  const pts = platformRatingRows.value.filter((r) =>
    withinWindow(r.contest_start_time!),
  )
  return pts.map((r) => ({
    label: r.contest_start_time as string,
    value: r.new_rating as number,
    meta: {
      contest: r.contest_name,
      platform: r.contest_platform,
      delta: r.rating_delta,
      rank: r.rank ?? null,
    },
  }))
})

const chartKicker = computed(() =>
  platform.value === ''
    ? 'SITE TOTAL / 站内总积分'
    : `${platformClass(platform.value).toUpperCase()} / 官方 RATING`,
)
const chartTitle = computed(() =>
  platform.value === ''
    ? '站内总积分走势'
    : `${platformLabel(platform.value)} 官方 Rating`,
)
const chartIntro = computed(() =>
  platform.value === ''
    ? '「全部」只画后端 /rating-history/ 的站内总积分单线，不合并平台曲线；每场赛后按榜单同口径重算。'
    : '线条颜色随该平台官方段位变化，分段参考线标出段位边界；平台 Rating 与站内总积分分开呈现。',
)
const currentPrecision = computed(() =>
  currentRating.value != null && !Number.isInteger(currentRating.value) ? 1 : 0,
)
const peakPrecision = computed(() =>
  peakRating.value != null && !Number.isInteger(peakRating.value) ? 1 : 0,
)

/** 曲线为空时的说明：区分「近一年无赛」与「该平台暂无 rated 记录」 */
const emptyChartHint = computed(() => {
  if (chartPoints.value.length) return null
  if (platform.value === '') {
    return { title: '最近一年无 rating 变化', hint: '近一年内没有计入排名的比赛记录' }
  }
  const name = platformLabel(platform.value)
  const all = platformRatingRows.value
  if (!all.length) {
    return {
      title: `${name} 最近一年无参赛记录`,
      hint: '该绑定账号暂无 rated 比赛成绩，同步后将自动出现在此曲线中',
    }
  }
  const last = all[all.length - 1]
  return {
    title: `${name} 最近一年无参赛记录`,
    hint: `共 ${all.length} 场 rated 比赛落在一年展示窗口外，最近一场：${last.contest_name} · ${fmtDate(last.contest_start_time)}`,
  }
})

const accounts = computed(() => (me.value?.platform_accounts || []) as any[])

// 各平台当前 rating（取该平台最新一场的 new_rating）
const platformRatings = computed(() => {
  const byPlat = new Map<ContestPlatform, MyParticipation[]>()
  for (const r of rows.value) {
    if (r.new_rating == null || !r.contest_start_time) continue
    if (!byPlat.has(r.contest_platform)) byPlat.set(r.contest_platform, [])
    byPlat.get(r.contest_platform)!.push(r)
  }
  const result: { platform: ContestPlatform; rating: number; delta: number | null }[] = []
  for (const [plat, list] of byPlat) {
    list.sort(
      (a, b) =>
        new Date(a.contest_start_time!).getTime() - new Date(b.contest_start_time!).getTime(),
    )
    const latest = list[list.length - 1]
    result.push({ platform: plat, rating: latest.new_rating!, delta: latest.rating_delta })
  }
  const order = new Map(SCORING_PLATFORMS.map((p, i) => [p.key, i]))
  return result.sort(
    (a, b) => (order.get(a.platform) ?? 99) - (order.get(b.platform) ?? 99),
  )
})

function fmtDate(s: string | null) {
  if (!s) return '—'
  return new Date(s).toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
}
function fmtDelta(v: number) {
  return v > 0 ? `+${v}` : `${v}`
}
// 最佳纪录数值精度（best_rank_score/best_score 为原始 float，需截断显示）
function fmtBest(v: number | null | undefined) {
  return v == null ? '—' : (Math.round(v * 10) / 10).toString()
}
</script>

<template>
  <div class="container-wide account-page">
    <div class="breadcrumb"><a @click="router.push('/u')">首页</a><span>/</span><span>个人成绩</span></div>

    <header class="account-hero">
      <img
        v-if="me?.avatar && !avatarFailed"
        :src="me.avatar"
        class="account-seal account-seal--photo"
        alt=""
        @error="avatarFailed = true"
      />
      <div v-else class="account-seal" aria-hidden="true">{{ initial(me?.real_name || me?.username || '?') }}</div>
      <div class="account-copy">
        <p class="kicker">ACCOUNT / 个人成绩</p>
        <h1 class="account-name">{{ me?.real_name || me?.username || '—' }}</h1>
        <p class="account-sub">
          @{{ me?.username || '—' }}
          <span>·</span>
          {{ me?.school?.name || '未绑定学校' }}
          <template v-if="me?.student_no"><span>·</span>学号 {{ me.student_no }}</template>
        </p>
        <div class="account-badges">
          <span class="badge badge-primary">已认证</span>
          <span v-for="a in accounts" :key="a.id" class="badge badge-muted account-badge">
            <span class="platform-tag" :class="platformClass(a.platform)">{{ platformLabel(a.platform) }}</span>
            <span class="account-handle">{{ a.handle || a.display_name || '—' }}</span>
          </span>
          <span v-if="!accounts.length" class="caption text-tertiary">尚未绑定平台账号</span>
        </div>
      </div>
      <div class="account-actions">
        <button class="btn btn-ghost btn-sm" @click="router.push('/u/my-application')">我的管理员申请</button>
        <button class="btn btn-secondary btn-sm" @click="router.push('/u/profile')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" /><path d="M18.5 2.5a2.12 2.12 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" /></svg>
          编辑资料
        </button>
      </div>
    </header>

    <div v-if="myRank" class="rank-strip">
      <div class="rank-strip__main">
        <span class="kicker">STUDENT RANK / 学生榜</span>
        <strong class="rank-strip__value num">#{{ myRank.rank }}</strong>
        <span class="rank-strip__meta">全部时间 · 计入 {{ myRank.contest_count }} 场</span>
      </div>
      <router-link :to="{ name: 'rankings', query: { scope: 'student' } }" class="caption link">查看完整榜单 →</router-link>
    </div>
    <div v-else-if="!rankLoading" class="rank-strip rank-strip--muted">
      <span class="caption text-tertiary">你还没有进入学生榜（需有计入积分的参赛记录）。</span>
    </div>

    <section class="account-metrics" aria-label="个人成绩摘要">
      <div class="metric">
        <span class="metric__label">站内总积分</span>
        <strong class="metric__value num"><CountUp :value="myRank?.total_score" :precision="1" /></strong>
        <span class="metric__meta">与榜单同口径</span>
      </div>
      <div class="metric">
        <span class="metric__label">未排除记录</span>
        <strong class="metric__value num"><CountUp :value="loading || error ? null : unexcludedCount" /></strong>
        <span class="metric__meta">不等同于计分场数</span>
      </div>
      <div class="metric">
        <span class="metric__label">参赛记录</span>
        <strong class="metric__value num"><CountUp :value="loading || error ? null : rows.length" /></strong>
        <span class="metric__meta">当前筛选的全部记录</span>
      </div>
      <div class="metric">
        <span class="metric__label">历史最佳排名</span>
        <strong class="metric__value num"><CountUp :value="bestRecord?.best_rank" prefix="#" /></strong>
        <span class="metric__meta">当时站内总积分 {{ fmtBest(bestRecord?.best_rank_score) }}</span>
      </div>
    </section>

    <!-- 各平台官方 rating 分开展示；与站内总积分不混用 -->
    <section v-if="platformRatings.length" class="platform-ledger" aria-label="各平台官方 Rating">
      <div class="platform-ledger__head">
        <div>
          <p class="kicker">OFFICIAL RATINGS</p>
          <h2 class="card-title">各平台官方 Rating</h2>
        </div>
        <span class="caption text-tertiary">平台口径，非站内总积分</span>
      </div>
      <div class="platform-ledger__grid">
        <div v-for="pr in platformRatings" :key="pr.platform" class="platform-cell">
          <span class="platform-tag" :class="platformClass(pr.platform)">{{ platformLabel(pr.platform) }}</span>
          <strong class="platform-cell__value num"><CountUp :value="pr.rating" /></strong>
          <span class="platform-cell__delta">
            <template v-if="pr.delta == null">—</template>
            <span v-else :class="pr.delta >= 0 ? 'up' : 'down'">{{ pr.delta >= 0 ? '▲' : '▼' }} {{ fmtDelta(pr.delta) }}</span>
          </span>
        </div>
      </div>
    </section>

    <div v-if="loading" class="card card-pad" role="status">正在加载全部参赛记录…</div>
    <div v-else-if="error" class="card card-pad" role="alert">
      <p>{{ error }}</p>
      <button type="button" class="btn btn-secondary" @click="records.reload()">重试</button>
    </div>

    <!-- 只有「未绑定任何平台」才整页收空态；绑定过账号时选项卡与曲线卡片必须在场 -->
    <EmptyState v-if="!loading && !error && accounts.length === 0" title="暂无参赛记录" hint="绑定平台账号并触发爬虫后将自动同步" />

    <template v-else>
      <!-- Rating chart：镜头内只呈现一条语义明确的曲线 -->
      <section class="chart-stage account-chart">
        <div class="chart-stage__head">
          <div class="chart-stage__intro">
            <p class="kicker">{{ chartKicker }}</p>
            <h2 class="card-title">{{ chartTitle }}</h2>
            <p>{{ chartIntro }}</p>
          </div>
          <SegmentedControl v-model="platform" :options="platformOptions" />
        </div>
        <div v-if="!loading && !error" v-sheen class="glass-lens chart-lens">
          <RatingLineChart
            v-if="chartPoints.length"
            :points="chartPoints"
            :height="280"
            :platform="platform"
          />
          <EmptyState v-else :title="emptyChartHint?.title" :hint="emptyChartHint?.hint" />
        </div>
        <div v-if="!loading && !error" class="chart-stage__foot">
          <span>
            当前{{ platform === '' ? '站内总积分' : '平台 Rating' }}:
            <b><CountUp :value="currentRating" :precision="currentPrecision" /></b>
          </span>
          <template v-if="platform === ''">
            <span>历史最佳排名: <b>#{{ bestRecord?.best_rank ?? '—' }}</b><template v-if="bestRecord?.best_rank != null">（当时站内总积分 {{ fmtBest(bestRecord.best_rank_score) }}）</template></span>
            <span>历史最高站内总积分: <b>{{ fmtBest(bestRecord?.best_score) }}</b></span>
          </template>
          <template v-else>
            <span>峰值 Rating: <b><CountUp :value="peakRating" :precision="peakPrecision" /></b></span>
          </template>
          <span>参赛场次: <b><CountUp :value="chartPoints.length" /></b></span>
        </div>
      </section>

      <!-- Contest history -->
      <div v-if="!loading && !error" class="card" style="overflow: hidden">
        <div class="card-header">
          <div class="card-title">参赛历史</div>
          <span class="caption text-tertiary">共 {{ rows.length }} 场</span>
        </div>
        <EmptyState v-if="!rows.length" title="当前筛选暂无参赛记录"
                    hint="绑定账号后由爬虫按调度同步，未及时出现可等待下一轮爬取" />
        <div v-else class="table-wrap" style="border: none; border-radius: 0">
          <table class="data-table">
            <colgroup>
              <col />
              <col style="width: 100px" />
              <col style="width: 110px" />
              <col style="width: 80px" />
              <col style="width: 80px" />
              <col style="width: 140px" />
            </colgroup>
            <thead>
              <tr><th>比赛名称</th><th>平台</th><th class="num-cell">时间</th><th class="num-cell">排名</th><th class="num-cell hide-mobile">解题数</th><th class="num-cell">Rating 变化</th></tr>
            </thead>
            <tbody>
              <tr v-for="r in pagedRows" :key="r.id" :class="{ 'excluded-row': r.is_excluded }">
                <td>
                  <a v-if="r.contest_url" :href="r.contest_url" target="_blank" rel="noopener" class="title-link">{{ r.contest_name }}</a>
                  <span v-else class="title-link">{{ r.contest_name }}</span>
                </td>
                <td><span class="platform-tag" :class="platformClass(r.contest_platform)">{{ platformLabel(r.contest_platform) }}</span></td>
                <td class="num-cell">{{ fmtDate(r.contest_start_time) }}</td>
                <td class="num-cell">{{ r.rank != null ? '#' + r.rank : '—' }}</td>
                <td class="num-cell hide-mobile">{{ r.solved_count != null ? r.solved_count : '—' }}</td>
                <td class="num-cell">
                  <template v-if="r.rating_delta == null">
                    <span v-if="r.rating_note" class="caption text-tertiary">{{ r.rating_note }}</span>
                    <template v-else>—</template>
                  </template>
                  <span v-else :class="r.rating_delta >= 0 ? 'up' : 'down'">
                    {{ r.rating_delta >= 0 ? '▲' : '▼' }} {{ fmtDelta(r.rating_delta) }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <DataPagination v-if="rows.length" v-model:page="tablePage" :page-size="tablePageSize" :total="rows.length" />
      </div>
    </template>
  </div>
</template>

<style scoped>
.account-page {
  padding-bottom: var(--space-6);
}
.account-hero {
  display: flex;
  align-items: center;
  gap: var(--space-5);
  flex-wrap: wrap;
  padding: var(--space-2) 0 var(--space-5);
  border-bottom: 1px solid var(--rule);
}
.account-seal {
  width: 64px;
  height: 64px;
  flex-shrink: 0;
  display: grid;
  place-items: center;
  background: var(--accent);
  color: var(--paper-2);
  font-family: var(--font-display);
  font-size: 28px;
  line-height: 1;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.25);
}
.account-seal--photo {
  object-fit: cover;
  background: var(--paper-3);
  border: 1px solid var(--rule);
  box-shadow: none;
}
.account-copy {
  flex: 1;
  min-width: 240px;
}
.account-name {
  margin: 3px 0 7px;
  font-family: var(--font-display);
  font-size: clamp(1.75rem, 1.35rem + 1.5vw, 2.35rem);
  font-weight: 600;
  line-height: 1.06;
}
.account-sub {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.02em;
  color: var(--ink-3);
}
.account-badges {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 10px;
}
.account-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 2px 8px;
}
.account-handle {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--ink-2);
}
.account-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
}
.rank-strip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  flex-wrap: wrap;
  padding: 12px 0;
  border-bottom: 1px solid var(--rule);
}
.rank-strip__main {
  display: flex;
  align-items: baseline;
  gap: var(--space-3);
  flex-wrap: wrap;
}
.rank-strip__value {
  font-size: 24px;
  color: var(--accent);
}
.rank-strip__meta {
  font-size: 12px;
  color: var(--ink-3);
}
.rank-strip--muted {
  justify-content: flex-start;
}
.link {
  color: var(--accent);
  cursor: pointer;
}
.link:hover {
  text-decoration: underline;
}
.account-metrics {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  margin: var(--space-5) 0 var(--space-6);
  border: 1px solid var(--rule);
  background: var(--paper-2);
  box-shadow: var(--shadow-md);
}
.metric {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
  padding: 14px var(--space-4);
  border-right: 1px solid var(--rule);
}
.metric:last-child {
  border-right: 0;
}
.metric__label {
  font-family: var(--font-mono);
  font-size: 9.5px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--ink-3);
}
.metric__value {
  font-size: clamp(1.4rem, 1.2rem + 0.5vw, 1.75rem);
  font-weight: 500;
  line-height: 1.12;
  color: var(--ink);
}
.metric__meta {
  font-size: 11px;
  color: var(--ink-3);
  line-height: 1.45;
}
.platform-ledger {
  margin-bottom: var(--space-6);
}
.platform-ledger__head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--space-4);
  flex-wrap: wrap;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--rule);
}
.platform-ledger__head .card-title {
  margin-top: 4px;
}
.platform-ledger__grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  border: 1px solid var(--rule);
  border-top: 0;
  background: var(--paper-2);
}
.platform-cell {
  display: flex;
  flex-direction: column;
  gap: 5px;
  min-width: 0;
  padding: 14px var(--space-4);
  border-right: 1px solid var(--rule);
}
.platform-cell:last-child {
  border-right: 0;
}
.platform-cell .platform-tag {
  align-self: flex-start;
}
.platform-cell__value {
  font-size: clamp(1.5rem, 1.3rem + 0.5vw, 1.85rem);
  font-weight: 500;
  line-height: 1.1;
  color: var(--ink);
}
.platform-cell__delta {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--ink-3);
}
.account-chart {
  margin-bottom: var(--space-6);
}
.account-chart :deep(.segmented) {
  flex-wrap: wrap;
}
.account-chart .chart-stage__foot b {
  font-weight: 500;
  color: var(--ink);
}
.up {
  color: var(--color-success);
  font-weight: 600;
}
.down {
  color: var(--color-danger);
  font-weight: 600;
}
.title-link {
  font-weight: 700;
  color: var(--ink);
}
.title-link:hover {
  color: var(--accent);
}
.excluded-row {
  opacity: 0.5;
}

@media (max-width: 767px) {
  .account-hero {
    align-items: flex-start;
    gap: var(--space-4);
  }
  .account-seal {
    width: 56px;
    height: 56px;
    font-size: 24px;
  }
  .account-actions {
    width: 100%;
  }
  .account-metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .metric:nth-child(2n) {
    border-right: 0;
  }
  .metric:nth-child(-n + 2) {
    border-bottom: 1px solid var(--rule);
  }
  .platform-ledger__grid {
    grid-template-columns: 1fr;
  }
  .platform-cell {
    padding: 12px 14px;
    border-right: 0;
    border-bottom: 1px solid var(--rule);
  }
  .platform-cell:last-child {
    border-bottom: 0;
  }
  .platform-cell__value {
    font-size: 20px;
  }
  .rank-strip__main {
    gap: var(--space-2);
  }
}
</style>
