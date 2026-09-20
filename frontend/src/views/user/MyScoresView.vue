<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { listMyParticipations, listRankings, getMyBestRecord, getRatingHistory } from '@/api'
import { useAuthStore } from '@/stores/auth'
import type { MyParticipation, ContestPlatform, RankSnapshot, UserBestRecord, RatingHistoryPoint } from '@/api/types'
import RatingLineChart from '@/components/RatingLineChart.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import SegmentedControl from '@/components/ui/SegmentedControl.vue'
import { fmtCount, initial, platformName } from '@/utils/format'

const router = useRouter()
const auth = useAuthStore()

const platform = ref<'' | ContestPlatform>('')
const rows = ref<MyParticipation[]>([])
const loading = ref(false)

const platformOptions = [
  { label: '全部', value: '' as const },
  { label: 'Codeforces', value: 'codeforces' as const },
  { label: 'AtCoder', value: 'atcoder' as const },
  { label: '牛客', value: 'nowcoder' as const },
]

function load() {
  loading.value = true
  listMyParticipations({ platform: platform.value || undefined, page_size: 100 })
    .then(({ results }) => (rows.value = results))
    .catch(() => {})
    .finally(() => (loading.value = false))
}
onMounted(() => {
  load()
  loadRank()
  getMyBestRecord().then((r) => (bestRecord.value = r)).catch(() => {})
  getRatingHistory().then((h) => (history.value = h)).catch(() => {})
})
watch(platform, () => load())

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

const countedCount = computed(() => rows.value.filter((r) => !r.is_excluded).length)
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

/** 曲线为空时的说明：区分「近一年无赛」与「该平台暂无 rated 记录」 */
const emptyChartHint = computed(() => {
  if (chartPoints.value.length) return null
  if (platform.value === '') {
    return { title: '最近一年无 rating 变化', hint: '近一年内没有计入排名的比赛记录' }
  }
  const name = platformName(platform.value)
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
  return result
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
function accountTag(p: string) {
  return p === 'codeforces' ? 'cf' : p === 'atcoder' ? 'atcoder' : p === 'nowcoder' ? 'nowcoder' : ''
}
</script>

<template>
  <div class="container-wide">
    <div class="page-head">
      <div>
        <div class="breadcrumb"><a @click="router.push('/u')">首页</a><span>/</span><span>个人中心</span></div>
        <h1 class="page-title">个人成绩</h1>
      </div>
      <button class="btn btn-ghost" @click="router.push('/u/my-application')">我的管理员申请</button>
      <button class="btn btn-secondary btn-sm" @click="router.push('/u/profile')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" /><path d="M18.5 2.5a2.12 2.12 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" /></svg>
        编辑资料
      </button>
    </div>

    <!-- Profile info card -->
    <div class="card card-pad profile-card">
      <div class="profile-glow" />
      <div class="profile-head">
        <img v-if="me?.avatar" :src="me.avatar" class="avatar lg avatar-photo" alt="头像" />
        <div v-else class="avatar lg">{{ initial(me?.real_name || me?.username || '?') }}</div>
        <div class="profile-id">
          <div style="display: flex; align-items: center; gap: var(--space-3); flex-wrap: wrap">
            <h2 class="h2" style="margin: 0">{{ me?.real_name || me?.username || '—' }}</h2>
            <span class="badge badge-primary"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" /><path d="M22 4L12 14.01l-3-3" /></svg>已认证</span>
          </div>
          <div style="display: flex; gap: var(--space-6); margin-top: var(--space-3); flex-wrap: wrap" class="body-sm text-secondary">
            <span style="display: flex; align-items: center; gap: var(--space-2)"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 10v6M2 10l10-5 10 5-10 5z" /></svg>{{ me?.school?.name || '未绑定学校' }}</span>
            <span v-if="me?.student_no" style="display: flex; align-items: center; gap: var(--space-2)"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2" /><path d="M16 2v4M8 2v4M3 10h18" /></svg>学号 {{ me.student_no }}</span>
          </div>
        </div>
        <div class="profile-accounts">
          <div v-for="a in accounts" :key="a.id" class="badge badge-muted account-badge">
            <span class="platform-tag" :class="accountTag(a.platform)">{{ platformName(a.platform) }}</span>
            <span class="num" style="font-size: 13px; color: var(--color-text-primary)">{{ a.handle || a.display_name || '—' }}</span>
          </div>
          <div v-if="!accounts.length" class="caption text-tertiary">尚未绑定平台账号</div>
        </div>
      </div>
    </div>

    <!-- My ranking on student leaderboard -->
    <div v-if="myRank" class="card card-pad rank-card">
      <div class="rank-card-head">
        <span class="card-title">我的学生榜排名</span>
        <router-link :to="{ name: 'rankings', query: { scope: 'student' } }" class="caption link">查看完整榜单 →</router-link>
      </div>
      <div class="grid grid-3 rank-metrics">
        <div><div class="stat-label">学生榜名次</div><div class="stat-value num text-cyan">#{{ myRank.rank }}</div></div>
        <div><div class="stat-label">总积分</div><div class="stat-value num">{{ fmtCount(myRank.total_score) }}</div></div>
        <div><div class="stat-label">计入场次</div><div class="stat-value num">{{ myRank.contest_count }}</div></div>
      </div>
    </div>
    <div v-else-if="!rankLoading" class="card card-pad rank-card rank-empty">
      <span class="caption text-tertiary">你还没有进入学生榜（需有计入积分的参赛记录）。</span>
    </div>

    <!-- Summary metrics -->
    <div class="grid grid-4 metrics-row">
      <div class="stat-card"><div class="stat-label text-accent">站点 Rating</div><div class="stat-value num text-cyan">{{ myRank ? fmtCount(myRank.total_score) : '—' }}</div><div class="stat-sub">表现分口径</div></div>
      <div class="stat-card"><div class="stat-label">计入积分场数</div><div class="stat-value num">{{ countedCount }}</div><div class="stat-sub">未排除</div></div>
      <div class="stat-card"><div class="stat-label">参赛记录</div><div class="stat-value num">{{ rows.length }}</div><div class="stat-sub">全部场次</div></div>
      <div class="stat-card"><div class="stat-label">历史最佳排名</div><div class="stat-value num">{{ bestRecord?.best_rank != null ? '#' + bestRecord.best_rank : '—' }}</div><div class="stat-sub">当时站点 rating {{ fmtBest(bestRecord?.best_rank_score) }}</div></div>
    </div>

    <!-- 各平台 Rating 分开展示（平台官方口径，非站点评分） -->
    <div v-if="platformRatings.length" class="card card-pad" style="margin-bottom: var(--space-6)">
      <div class="card-title" style="margin-bottom: var(--space-4)">各平台官方 Rating</div>
      <div class="grid grid-3" style="gap: var(--space-4)">
        <div v-for="pr in platformRatings" :key="pr.platform" class="stat-card">
          <div class="stat-label"><span class="platform-tag" :class="accountTag(pr.platform)">{{ platformName(pr.platform) }}</span></div>
          <div class="stat-value num">{{ pr.rating }}</div>
          <div class="stat-sub">
            <template v-if="pr.delta == null">—</template>
            <span v-else :class="pr.delta >= 0 ? 'up' : 'down'">{{ pr.delta >= 0 ? '▲' : '▼' }} {{ fmtDelta(pr.delta) }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 只有「未绑定任何平台」才整页收空态；绑定过账号时选项卡与曲线卡片必须在场 -->
    <EmptyState v-if="!loading && accounts.length === 0" title="暂无参赛记录" hint="绑定平台账号并触发爬虫后将自动同步" />

    <template v-else>
      <!-- Rating chart -->
      <div class="card" style="margin-bottom: var(--space-6)">
        <div class="card-header">
          <div class="card-title">Rating 趋势</div>
          <SegmentedControl v-model="platform" :options="platformOptions" />
        </div>
        <div class="card-body">
          <RatingLineChart v-if="chartPoints.length" :points="chartPoints" :height="240" :platform="platform" />
          <EmptyState v-else :title="emptyChartHint?.title" :hint="emptyChartHint?.hint" />
          <div v-if="chartPoints.length" style="display: flex; gap: var(--space-6); margin-top: var(--space-4); flex-wrap: wrap" class="caption text-tertiary">
            <span>当前 Rating: <b class="num text-cyan">{{ currentRating ?? '—' }}</b></span>
            <template v-if="platform === ''">
              <span>历史最佳排名: <b class="num">#{{ bestRecord?.best_rank ?? '—' }}</b><template v-if="bestRecord?.best_rank != null"> <span class="text-tertiary">（当时站点 rating {{ fmtBest(bestRecord.best_rank_score) }}）</span></template></span>
              <span>历史最高站点 rating: <b class="num">{{ fmtBest(bestRecord?.best_score) }}</b></span>
            </template>
            <template v-else>
              <span>峰值 Rating: <b class="num">{{ peakRating ?? '—' }}</b></span>
            </template>
            <span>参赛场次: <b class="num">{{ chartPoints.length }}</b></span>
          </div>
        </div>
      </div>

      <!-- Contest history -->
      <div class="card" style="overflow: hidden">
        <div class="card-header">
          <div class="card-title">参赛历史</div>
          <span class="caption text-tertiary">共 {{ rows.length }} 场</span>
        </div>
        <EmptyState v-if="!rows.length" title="该平台暂无 rated 参赛记录"
                    hint="绑定账号后由爬虫按调度同步，未及时出现可等待下一轮爬取" />
        <div v-else class="table-wrap" style="border: none; border-radius: 0">
          <table class="data-table">
            <colgroup>
              <col />
              <col style="width: 110px" />
              <col style="width: 120px" />
              <col style="width: 90px" />
              <col style="width: 90px" />
              <col style="width: 160px" />
            </colgroup>
            <thead>
              <tr><th>比赛名称</th><th>平台</th><th class="num-cell">时间</th><th class="num-cell">排名</th><th class="num-cell hide-mobile">解题数</th><th class="num-cell">Rating 变化</th></tr>
            </thead>
            <tbody>
              <tr v-for="r in rows" :key="r.id" :class="{ 'excluded-row': r.is_excluded }">
                <td>
                  <a v-if="r.contest_url" :href="r.contest_url" target="_blank" rel="noopener" class="title-link">{{ r.contest_name }}</a>
                  <span v-else class="title-link">{{ r.contest_name }}</span>
                </td>
                <td><span class="platform-tag" :class="accountTag(r.contest_platform)">{{ platformName(r.contest_platform) }}</span></td>
                <td class="num-cell">{{ fmtDate(r.contest_start_time) }}</td>
                <td class="num-cell">{{ r.rank != null ? '#' + r.rank : '—' }}</td>
                <td class="num-cell hide-mobile">{{ r.solved_count != null ? r.solved_count : '—' }}</td>
                <td class="num-cell">
                  <template v-if="r.rating_delta == null">—</template>
                  <span v-else :class="r.rating_delta >= 0 ? 'up' : 'down'">
                    {{ r.rating_delta >= 0 ? '▲' : '▼' }} {{ fmtDelta(r.rating_delta) }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.profile-card {
  position: relative;
  overflow: hidden;
  margin-bottom: var(--space-6);
}
.profile-glow {
  position: absolute;
  top: 0;
  right: 0;
  width: 300px;
  height: 100%;
  background: var(--gradient-primary-soft);
  opacity: 0.5;
  pointer-events: none;
}
.profile-head {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--space-6);
  flex-wrap: wrap;
}
.avatar.lg {
  width: 72px;
  height: 72px;
  border-radius: var(--radius-xl);
  background: var(--gradient-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  font-weight: 700;
  color: #fff;
  box-shadow: var(--shadow-glow);
  flex-shrink: 0;
}
.avatar.lg.avatar-photo {
  object-fit: cover;
  background: var(--color-surface-raised, #22304a);
}
.profile-id { flex: 1; min-width: 200px; }
.profile-accounts {
  display: flex;
  gap: var(--space-3);
  flex-wrap: wrap;
}
.account-badge {
  padding: var(--space-2) var(--space-3);
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  border-color: var(--color-border);
}
.title-link {
  font-weight: 700;
  color: var(--color-text-primary);
}
.title-link:hover { color: var(--color-primary); }
.up { color: var(--color-success); font-weight: 600; }
.down { color: var(--color-danger); font-weight: 600; }
.excluded-row { opacity: 0.5; }
.metrics-row { margin-bottom: var(--space-6); }
.rank-card { margin-bottom: var(--space-6); }
.rank-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-4);
}
.link { color: var(--color-primary); cursor: pointer; }
.link:hover { text-decoration: underline; }
.rank-metrics { gap: var(--space-4); }
.rank-empty { text-align: center; }
</style>
