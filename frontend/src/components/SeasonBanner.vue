<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { getSeason, getPastSeasons } from '@/api'
import type { SeasonInfo, PastSeason } from '@/api/types'
import { fmtCount, fmtScore } from '@/utils/format'

const season = ref<SeasonInfo | null>(null)
const past = ref<PastSeason[]>([])
const loading = ref(true)
const error = ref('')
const showPast = ref(false)

const stageMeta = computed(() => {
  const s = season.value?.stage
  switch (s) {
    case 'active':
      return { cls: 'badge-primary', label: '进行中' }
    case 'upcoming':
      return { cls: 'badge-warning', label: '未开始' }
    case 'settling':
      return { cls: 'badge-warning', label: '结算中' }
    case 'ended':
      return { cls: 'badge-muted', label: '已结束' }
    default:
      return { cls: 'badge-muted', label: '—' }
  }
})

const countdownText = computed(() => {
  const cd = season.value?.settle_countdown_seconds
  if (cd == null) return ''
  const d = Math.floor(cd / 86400)
  const h = Math.floor((cd % 86400) / 3600)
  if (d > 0) return `${d} 天 ${h} 小时`
  if (h > 0) return `${h} 小时`
  return '结算中'
})

const dateRangeText = computed(() => {
  const s = season.value
  if (!s) return ''
  const fmt = (iso: string) =>
    new Date(iso).toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
  return `${fmt(s.start_at)} — ${fmt(s.end_at)}`
})

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    season.value = await getSeason()
  } catch (e: any) {
    error.value = e?.response?.data?.detail || '加载赛季信息失败'
  } finally {
    loading.value = false
  }
}

async function togglePast() {
  showPast.value = !showPast.value
  if (showPast.value && past.value.length === 0) {
    try {
      past.value = await getPastSeasons()
    } catch {
      past.value = []
    }
  }
}

onMounted(load)
</script>

<template>
  <div class="season-banner card">
    <!-- 加载中 -->
    <div v-if="loading" class="season-loading">
      <span class="skel" style="width: 40%; height: 24px" />
      <span class="skel" style="width: 70%; height: 14px" />
      <span class="skel" style="width: 60%; height: 14px" />
    </div>

    <!-- 加载失败 -->
    <div v-else-if="error" class="season-error">
      <span>{{ error }}</span>
      <button class="btn btn-sm btn-ghost" @click="load">重试</button>
    </div>

    <!-- 赛季信息 -->
    <template v-else-if="season">
      <div class="season-head">
        <div class="season-title-row">
          <span class="season-badge">{{ season.year }}</span>
          <h2 class="season-name">{{ season.name }}</h2>
          <span class="badge" :class="stageMeta.cls">{{ stageMeta.label }}</span>
          <button class="btn btn-sm btn-ghost season-past-btn" @click="togglePast">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10" /><path d="M12 8v4l3 3" /></svg>
            往期赛季
          </button>
        </div>
        <div class="caption text-tertiary season-range">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2" /><path d="M16 2v4M8 2v4M3 10h18" /></svg>
          {{ dateRangeText }}
        </div>
      </div>

      <div class="season-body">
        <!-- 我的战绩 -->
        <div class="season-stats">
          <div class="season-stat">
            <div class="stat-label">当前排名</div>
            <div class="stat-value num text-cyan">{{ season.me?.rank != null ? '#' + season.me.rank : '—' }}</div>
          </div>
          <div class="season-stat">
            <div class="stat-label">赛季积分</div>
            <div class="stat-value num">{{ season.me ? fmtScore(season.me.total_score) : '—' }}</div>
          </div>
          <div class="season-stat">
            <div class="stat-label">参赛场次</div>
            <div class="stat-value num">{{ season.me ? fmtCount(season.me.contest_count) : '—' }}</div>
          </div>
        </div>

        <!-- 进度 -->
        <div class="season-progress">
          <div class="progress-head">
            <span class="caption text-tertiary">赛季进度</span>
            <span class="caption text-secondary num">{{ season.progress.pct }}%</span>
          </div>
          <div class="progress-track">
            <div class="progress-fill" :style="{ width: season.progress.pct + '%' }" />
          </div>
          <div class="caption text-tertiary progress-sub">
            第 {{ season.progress.elapsed_days }} 天 / 共 {{ season.progress.total_days }} 天
          </div>
        </div>

        <!-- 奖励 + 倒计时 -->
        <div v-if="season.rewards.length || countdownText" class="season-rewards">
          <div v-if="season.rewards.length" class="rewards-list">
            <div v-for="(r, i) in season.rewards" :key="i" class="reward-item">
              <span class="reward-icon">{{ r.icon || '🏆' }}</span>
              <div>
                <div class="reward-title">{{ r.title }}</div>
                <div v-if="r.desc" class="caption text-tertiary">{{ r.desc }}</div>
              </div>
            </div>
          </div>
          <div v-if="countdownText" class="settle-countdown">
            <span class="caption text-tertiary">结算倒计时</span>
            <span class="num settle-time">{{ countdownText }}</span>
          </div>
        </div>
      </div>

      <!-- 往期赛季弹层 -->
      <div v-if="showPast" class="past-panel">
        <div class="past-head">
          <span class="caption">往期赛季</span>
          <button class="btn btn-sm btn-ghost" @click="showPast = false">收起</button>
        </div>
        <div v-if="past.length" class="past-list">
          <div v-for="p in past" :key="p.id" class="past-item">
            <span class="num">{{ p.year }}</span>
            <span class="past-name">{{ p.name }}</span>
            <span class="caption text-tertiary">{{ fmtDate(p.start_at) }} — {{ fmtDate(p.end_at) }}</span>
            <span class="badge badge-muted">{{ p.stage_display }}</span>
          </div>
        </div>
        <div v-else class="caption text-tertiary past-empty">暂无往期赛季</div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.season-banner {
  position: relative;
  margin-bottom: var(--space-8);
  padding: var(--space-6) var(--space-8);
  background:
    radial-gradient(circle at 100% 0%, rgba(139, 92, 246, 0.10), transparent 45%),
    var(--color-bg-surface);
  overflow: hidden;
}
.season-loading {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.season-error {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  color: var(--color-danger);
}
.season-head {
  margin-bottom: var(--space-5);
}
.season-title-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-wrap: wrap;
}
.season-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 10px;
  border-radius: 999px;
  background: var(--gradient-primary);
  color: #fff;
  font-weight: 700;
  font-size: 13px;
  letter-spacing: 0.02em;
}
.season-name {
  font-size: 20px;
  font-weight: 700;
  margin: 0;
}
.season-past-btn {
  margin-left: auto;
}
.season-range {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  margin-top: var(--space-2);
}
.season-body {
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: var(--space-6);
  align-items: start;
}
.season-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-4);
}
.season-stat {
  padding: var(--space-4);
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}
.season-progress {
  grid-column: 1 / -1;
}
.progress-head {
  display: flex;
  justify-content: space-between;
  margin-bottom: var(--space-2);
}
.progress-track {
  height: 8px;
  border-radius: 999px;
  background: var(--color-bg-inset);
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  background: var(--gradient-primary);
  border-radius: 999px;
  transition: width var(--duration-slower) var(--ease-out);
}
.progress-sub {
  margin-top: var(--space-2);
}
.season-rewards {
  grid-column: 1 / -1;
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-5);
  align-items: center;
}
.rewards-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-4);
  flex: 1;
}
.reward-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}
.reward-icon {
  font-size: 20px;
}
.reward-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary);
}
.settle-countdown {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
  padding-left: var(--space-5);
  border-left: 1px solid var(--color-border);
}
.settle-time {
  font-size: 18px;
  font-weight: 700;
  color: var(--color-primary);
}
.past-panel {
  margin-top: var(--space-5);
  padding-top: var(--space-5);
  border-top: 1px solid var(--color-border);
}
.past-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-3);
}
.past-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.past-item {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-3) var(--space-4);
  background: var(--color-bg-elevated);
  border-radius: var(--radius-md);
  font-size: 14px;
}
.past-name {
  font-weight: 600;
  color: var(--color-text-primary);
}
.past-empty {
  padding: var(--space-4);
  text-align: center;
}

@media (max-width: 860px) {
  .season-banner { padding: var(--space-5); }
  .season-body { grid-template-columns: 1fr; }
  .season-past-btn { margin-left: 0; }
  .settle-countdown {
    align-items: flex-start;
    padding-left: 0;
    border-left: none;
  }
}
</style>
