<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { listMyParticipations } from '@/api'
import { useAuthStore } from '@/stores/auth'
import type { MyParticipation, ContestPlatform } from '@/api/types'
import RatingLineChart from '@/components/RatingLineChart.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import SegmentedControl from '@/components/ui/SegmentedControl.vue'
import { fmtCount, initial, platformTag } from '@/utils/format'

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
onMounted(load)
watch(platform, () => load())

const me = computed(() => auth.user)

const countedCount = computed(() => rows.value.filter((r) => !r.is_excluded).length)
const totalDelta = computed(() => rows.value.reduce((s, r) => s + (r.rating_delta ?? 0), 0))
const currentRating = computed(() => {
  const rated = rows.value
    .filter((r) => r.new_rating != null && r.contest_start_time)
    .sort((a, b) => new Date(a.contest_start_time!).getTime() - new Date(b.contest_start_time!).getTime())
  return rated.length ? rated[rated.length - 1].new_rating : null
})
const peakRating = computed(() => {
  const vals = rows.value.map((r) => r.new_rating).filter((v): v is number => v != null)
  return vals.length ? Math.max(...vals) : null
})
const bestRank = computed(() => {
  const ranks = rows.value.map((r) => r.rank).filter((r): r is number => r != null)
  return ranks.length ? Math.min(...ranks) : null
})

const chartPoints = computed(() =>
  rows.value
    .filter((r) => r.new_rating != null && r.contest_start_time)
    .map((r) => ({
      label: r.contest_start_time as string,
      value: r.new_rating as number,
      meta: { contest: r.contest_name, delta: r.rating_delta },
    })),
)

const accounts = computed(() => (me.value?.platform_accounts || []) as any[])

function fmtDate(s: string | null) {
  if (!s) return '—'
  return new Date(s).toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
}
function fmtDelta(v: number) {
  return v > 0 ? `+${v}` : `${v}`
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
      <button class="btn btn-secondary btn-sm" @click="router.push('/register/info')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" /><path d="M18.5 2.5a2.12 2.12 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" /></svg>
        编辑资料
      </button>
    </div>

    <!-- Profile info card -->
    <div class="card card-pad profile-card">
      <div class="profile-glow" />
      <div class="profile-head">
        <div class="avatar lg">{{ initial(me?.real_name || me?.username || '?') }}</div>
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
            <span class="platform-tag" :class="accountTag(a.platform)">{{ platformTag(a.platform) }}</span>
            <span class="num" style="font-size: 13px; color: var(--color-text-primary)">{{ a.handle || a.display_name || '—' }}</span>
          </div>
          <div v-if="!accounts.length" class="caption text-tertiary">尚未绑定平台账号</div>
        </div>
      </div>
    </div>

    <!-- Summary metrics -->
    <div class="grid grid-4 metrics-row">
      <div class="stat-card"><div class="stat-label">总积分</div><div class="stat-value num">{{ fmtCount(rows.length) }}</div><div class="stat-sub">参赛记录</div></div>
      <div class="stat-card"><div class="stat-label">计入积分场数</div><div class="stat-value num">{{ countedCount }}</div><div class="stat-sub">未排除</div></div>
      <div class="stat-card"><div class="stat-label">平均排名</div><div class="stat-value num">{{ bestRank != null ? '#' + bestRank : '—' }}</div><div class="stat-sub">历史最佳</div></div>
      <div class="stat-card"><div class="stat-label text-accent">最高 Rating</div><div class="stat-value num text-cyan">{{ currentRating ?? '—' }}</div><div class="stat-sub">峰值 {{ peakRating ?? '—' }}</div></div>
    </div>

    <EmptyState v-if="!loading && rows.length === 0" title="暂无参赛记录" hint="绑定平台账号并触发爬虫后将自动同步" />

    <template v-else>
      <!-- Rating chart -->
      <div class="card" style="margin-bottom: var(--space-6)">
        <div class="card-header">
          <div class="card-title">Rating 趋势</div>
          <SegmentedControl v-model="platform" :options="platformOptions" />
        </div>
        <div class="card-body">
          <RatingLineChart :points="chartPoints" :height="240" />
          <div style="display: flex; gap: var(--space-6); margin-top: var(--space-4); flex-wrap: wrap" class="caption text-tertiary">
            <span>当前 Rating: <b class="num text-cyan">{{ currentRating ?? '—' }}</b></span>
            <span>峰值 Rating: <b class="num">{{ peakRating ?? '—' }}</b></span>
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
        <div class="table-wrap" style="border: none; border-radius: 0">
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
                <td><span class="platform-tag" :class="accountTag(r.contest_platform)">{{ platformTag(r.contest_platform) }}</span></td>
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
</style>
