<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getUserPublicProfile, getRatingHistory } from '@/api'
import type { UserPublicProfile, ContestPlatform, RatingHistoryPoint } from '@/api/types'
import EmptyState from '@/components/ui/EmptyState.vue'
import SegmentedControl from '@/components/ui/SegmentedControl.vue'
import RatingLineChart from '@/components/RatingLineChart.vue'
import CountUp from '@/components/ui/CountUp.vue'
import { SCORING_PLATFORMS, platformClass, platformLabel } from '@/platforms/meta'

const route = useRoute()
const router = useRouter()

const profile = ref<UserPublicProfile | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const chartPlatform = ref<'' | ContestPlatform>('')
const avatarFailed = ref(false)
watch(() => profile.value?.avatar, () => (avatarFailed.value = false))

/** 有入口的平台 = 已绑定平台 ∪ 有参赛记录的平台（后端未升级时靠后者兜底） */
const chartPlatformOptions = computed(() => {
  const plats = new Set<string>([
    ...(profile.value?.platforms || []),
    ...(profile.value?.participations || []).map((p) => p.contest_platform),
  ])
  const opts: { label: string; value: '' | ContestPlatform }[] = [{ label: '全部', value: '' }]
  for (const p of SCORING_PLATFORMS.map((x) => x.key)) {
    if (plats.has(p)) opts.push({ label: platformLabel(p), value: p })
  }
  return opts
})

// 折线图数据：「全部」= 后端站点 rating 时间线（与榜单同口径，窗口已在后端裁剪）；
// 单平台 = 该平台原始 new_rating 序列
const history = ref<RatingHistoryPoint[]>([])
const CHART_WINDOW_DAYS = 365

/** 当前所选平台全部可画的官方 rating 行（时间升序，未截展示窗口） */
const platformRatingRows = computed(() =>
  (profile.value?.participations || [])
    .filter(
      (r) =>
        r.new_rating != null &&
        r.contest_start_time != null &&
        r.contest_platform === chartPlatform.value,
    )
    .sort(
      (a, b) =>
        new Date(a.contest_start_time!).getTime() -
        new Date(b.contest_start_time!).getTime(),
    ),
)

function withinWindow(iso: string) {
  return new Date(iso).getTime() >= Date.now() - CHART_WINDOW_DAYS * 86400000
}

const chartPoints = computed(() => {
  if (chartPlatform.value === '') {
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
  const rows = platformRatingRows.value.filter((r) =>
    withinWindow(r.contest_start_time!),
  )
  return rows.map((r) => ({
    label: r.contest_start_time as string,
    value: r.new_rating as number,
    meta: { contest: r.contest_name, platform: r.contest_platform, delta: r.rating_delta, rank: r.rank ?? null },
  }))
})

/** 曲线为空时的说明：区分「近一年无赛」与「该平台暂无 rated 记录」 */
const emptyChartHint = computed(() => {
  if (chartPoints.value.length) return null
  if (chartPlatform.value === '') {
    return { title: '最近一年无 rating 变化', hint: '该用户近一年内没有计入排名的比赛记录' }
  }
  const name = platformLabel(chartPlatform.value)
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

/** 只要有任何平台入口就保留卡片与选项卡——不再随曲线为空整块消失 */
const showRatingCard = computed(() => chartPlatformOptions.value.length > 1)
const chartKicker = computed(() =>
  chartPlatform.value === ''
    ? 'SITE TOTAL / 站内总积分'
    : `${platformClass(chartPlatform.value).toUpperCase()} / 官方 RATING`,
)
const chartTitle = computed(() =>
  chartPlatform.value === ''
    ? '站内总积分走势'
    : `${platformLabel(chartPlatform.value)} 官方 Rating`,
)
const chartIntro = computed(() =>
  chartPlatform.value === ''
    ? '「全部」只画后端站内总积分单线，不合并平台曲线。'
    : '线条颜色随该平台官方段位变化；平台 Rating 与站内总积分分开呈现。',
)

onMounted(async () => {
  const id = Number(route.params.id)
  if (!id) {
    error.value = '无效的用户'
    loading.value = false
    return
  }
  try {
    profile.value = await getUserPublicProfile(id)
    getRatingHistory(id).then((h) => (history.value = h)).catch(() => {})
  } catch (e: any) {
    error.value = e?.response?.data?.detail || '加载用户信息失败'
  } finally {
    loading.value = false
  }
})

function fmtDate(s: string | null) {
  if (!s) return '—'
  return new Date(s).toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
}
function fmtDelta(v: number) {
  return v > 0 ? `+${v}` : `${v}`
}
</script>

<template>
  <div class="container-wide profile-page">
    <div class="breadcrumb">
      <a @click="router.push('/u/rankings')">排名榜</a><span>/</span><span>用户信息</span>
    </div>

    <div v-if="error" class="alert">
      <span>{{ error }}</span>
      <button class="btn btn-sm btn-ghost" @click="router.back()">返回</button>
    </div>

    <div v-else-if="loading" class="card card-pad">
      <span class="skel" style="width: 40%; height: 24px" />
    </div>

    <template v-else-if="profile">
      <header class="profile-hero">
        <img
          v-if="profile.avatar && !avatarFailed"
          class="profile-seal"
          :src="profile.avatar"
          alt=""
          @error="avatarFailed = true"
        />
        <div v-else class="profile-seal profile-seal--letter">{{ (profile.real_name || profile.username || '?').slice(0, 1) }}</div>
        <div class="profile-copy">
          <p class="kicker">PUBLIC PROFILE / 公开主页</p>
          <h1 class="profile-name">{{ profile.real_name || profile.username }}</h1>
          <p class="profile-meta">
            @{{ profile.username }}
            <span>·</span>
            {{ profile.school_name || '未绑定学校' }}
            <span>·</span>
            {{ profile.role_display }}
          </p>
          <p v-if="profile.bio" class="profile-bio">{{ profile.bio }}</p>
          <p v-else class="profile-bio profile-bio--empty">这个人还没写个性签名。</p>
        </div>
      </header>

      <!-- Rating 趋势折线图：曲线可空，但已绑定平台的选项卡不能消失 -->
      <section v-if="showRatingCard" class="chart-stage profile-chart">
        <div class="chart-stage__head">
          <div class="chart-stage__intro">
            <p class="kicker">{{ chartKicker }}</p>
            <h2 class="card-title">{{ chartTitle }}</h2>
            <p>{{ chartIntro }}</p>
          </div>
          <SegmentedControl v-model="chartPlatform" :options="chartPlatformOptions" />
        </div>
        <div v-sheen class="glass-lens chart-lens">
          <RatingLineChart v-if="chartPoints.length" :points="chartPoints" :height="250" :platform="chartPlatform" />
          <EmptyState v-else :title="emptyChartHint?.title" :hint="emptyChartHint?.hint" />
        </div>
        <div class="chart-stage__foot">
          <span>{{ chartPlatform === '' ? '站内总积分' : '平台官方 Rating' }}</span>
          <span>悬停 / 轻触查看比赛</span>
        </div>
      </section>

      <!-- 各平台 rating（平台官方口径，非站点评分） -->
      <section v-if="profile.platform_ratings.length" class="platform-ledger">
        <div class="platform-ledger__head">
          <div>
            <p class="kicker">OFFICIAL RATINGS</p>
            <h2 class="card-title">各平台官方 Rating</h2>
          </div>
          <span class="caption text-tertiary">平台口径，非站内总积分</span>
        </div>
        <div class="platform-ledger__grid">
          <div v-for="pr in profile.platform_ratings" :key="pr.platform" class="platform-cell">
            <div class="platform-cell__head">
              <span class="platform-tag" :class="platformClass(pr.platform)">{{ platformLabel(pr.platform) }}</span>
              <span class="platform-cell__handle">{{ pr.handle }}</span>
            </div>
            <strong class="platform-cell__value num"><CountUp :value="pr.rating" /></strong>
            <span class="platform-cell__delta">
              <template v-if="pr.delta == null">—</template>
              <span v-else :class="pr.delta >= 0 ? 'up' : 'down'">{{ pr.delta >= 0 ? '▲' : '▼' }} {{ fmtDelta(pr.delta) }}</span>
            </span>
          </div>
        </div>
      </section>

      <!-- 参赛记录 -->
      <div class="card" style="overflow: hidden">
        <div class="card-header">
          <div class="card-title">参赛记录</div>
          <span class="caption text-tertiary">共 {{ profile.participations.length }} 场</span>
        </div>
        <div class="table-wrap" style="border: none; border-radius: 0">
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
              <tr>
                <th>比赛名称</th>
                <th>平台</th>
                <th class="num-cell">时间</th>
                <th class="num-cell">排名</th>
                <th class="num-cell hide-mobile">解题数</th>
                <th class="num-cell">Rating 变化</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="p in profile.participations" :key="p.id">
                <td>
                  <a v-if="p.contest_url" :href="p.contest_url" target="_blank" rel="noopener" class="title-link">{{ p.contest_name }}</a>
                  <span v-else class="title-link">{{ p.contest_name }}</span>
                </td>
                <td><span class="platform-tag" :class="platformClass(p.contest_platform)">{{ platformLabel(p.contest_platform) }}</span></td>
                <td class="num-cell">{{ fmtDate(p.contest_start_time) }}</td>
                <td class="num-cell">{{ p.rank != null ? '#' + p.rank : '—' }}</td>
                <td class="num-cell hide-mobile">{{ p.solved_count != null ? p.solved_count : '—' }}</td>
                <td class="num-cell">
                  <template v-if="p.rating_delta == null">
                    <span v-if="p.rating_note" class="caption text-tertiary">{{ p.rating_note }}</span>
                    <span v-else-if="!p.contest_is_rated" class="caption text-tertiary">不计 Rating</span>
                    <template v-else>—</template>
                  </template>
                  <span v-else :class="p.rating_delta >= 0 ? 'up' : 'down'">
                    {{ p.rating_delta >= 0 ? '▲' : '▼' }} {{ fmtDelta(p.rating_delta) }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
          <EmptyState v-if="profile.participations.length === 0" title="暂无参赛记录" hint="该用户暂无计入排行的比赛" />
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.profile-page {
  padding-bottom: var(--space-6);
}
.profile-hero {
  display: flex;
  align-items: center;
  gap: var(--space-5);
  flex-wrap: wrap;
  padding: var(--space-2) 0 var(--space-5);
  margin-bottom: var(--space-5);
  border-bottom: 1px solid var(--rule);
}
.profile-seal {
  width: 64px;
  height: 64px;
  flex-shrink: 0;
  object-fit: cover;
  border: 1px solid var(--rule);
  background: var(--paper-3);
}
.profile-seal--letter {
  display: grid;
  place-items: center;
  background: var(--accent);
  color: var(--paper-2);
  border-color: var(--accent);
  font-family: var(--font-display);
  font-size: 28px;
  line-height: 1;
}
.profile-copy {
  flex: 1;
  min-width: 240px;
}
.profile-name {
  margin: 3px 0 7px;
  font-family: var(--font-display);
  font-size: clamp(1.75rem, 1.35rem + 1.5vw, 2.35rem);
  font-weight: 600;
  line-height: 1.06;
}
.profile-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin: 0;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--ink-3);
}
.profile-bio {
  max-width: 72ch;
  margin: 10px 0 0;
  font-size: 13px;
  color: var(--ink-2);
}
.profile-bio--empty {
  color: var(--ink-3);
  font-style: italic;
}
.profile-chart {
  margin-bottom: var(--space-6);
}
.profile-chart :deep(.segmented) {
  flex-wrap: wrap;
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
.platform-cell__head {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
}
.platform-cell__handle {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--ink-3);
}
.platform-cell__value {
  font-size: clamp(1.5rem, 1.3rem + 0.5vw, 1.85rem);
  font-weight: 500;
  line-height: 1.1;
}
.platform-cell__delta {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--ink-3);
}
.alert {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  background: var(--color-danger-subtle);
  border: 1px solid color-mix(in srgb, var(--color-danger) 30%, var(--rule));
  color: var(--color-danger);
  border-radius: 0;
  padding: var(--space-3) var(--space-4);
  margin-bottom: var(--space-5);
}
.title-link {
  font-weight: 600;
  color: var(--ink);
}
.title-link:hover {
  color: var(--accent);
}
.up {
  color: var(--color-success);
  font-weight: 600;
}
.down {
  color: var(--color-danger);
  font-weight: 600;
}
@media (max-width: 767px) {
  .profile-seal {
    width: 56px;
    height: 56px;
    font-size: 24px;
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
}
</style>
