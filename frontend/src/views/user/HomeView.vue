<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { listRankings, listSchools, listContests, listUsers, listParticipations } from '@/api'
import type { RankSnapshot, School } from '@/api/types'
import { fmtScore, fmtCount, medalRowClass, orgShort } from '@/utils/format'
import RankBadge from '@/components/ui/RankBadge.vue'
import OrgLogo from '@/components/ui/OrgLogo.vue'

const top5 = ref<RankSnapshot[]>([])
const schoolsMap = ref<Record<number, School>>({})
const stats = ref({ schools: 0, contests: 0, users: 0, participations: 0 })
const loading = ref(true)

const platforms = [
  {
    name: 'Codeforces',
    domain: 'codeforces.com',
    desc: '全球最活跃的算法竞赛平台，Rating 系统权威，高校选手主战场。',
    icon: 'M4.5 7.5L1 9l2 2-1 5 4 6h4l1-2-2-4 3-1 2-3-3-2 1-3-5-1z',
    color: '#f87171',
    contests: 712,
    users: 2103,
  },
  {
    name: 'AtCoder',
    domain: 'atcoder.jp',
    desc: '日本老牌竞赛平台，题目质量高，ABC / ARC 系列深受高校欢迎。',
    icon: 'M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5',
    color: '#e4e4e7',
    contests: 348,
    users: 1247,
  },
  {
    name: '牛客竞赛',
    domain: 'nowcoder.com',
    desc: '国内高校赛事核心阵地，多校训练赛、寒假集训营覆盖面广。',
    icon: 'M12 2a10 10 0 1 0 0 0',
    color: '#4ade80',
    contests: 187,
    users: 1894,
  },
]

const features = [
  { icon: 'M3 3v18h18M7 14l4-4 4 4 5-5', cls: 'primary', title: '学校积分排名', desc: '按学校维度聚合选手成绩，科学积分模型，实时更新榜单。' },
  { icon: 'M3 3v18h18M7 14l4-4 4 4 5-5', cls: 'cyan', title: '个人成绩追踪', desc: '跨平台 Rating 折线图、参赛历史、积分明细，一目了然。' },
  { icon: 'M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M12 12a3 3 0 1 0 0 0', cls: 'success', title: '自动数据采集', desc: '爬虫定时同步三大平台比赛与成绩，零人工录入。' },
  { icon: 'M13 2L3 14h9l-1 8 10-12h-9l1-8z', cls: 'warning', title: '智能积分引擎', desc: '融合难度系数、参赛规模、排名表现，公平量化实力。' },
]

function schoolMeta(id: number | null) {
  if (id == null) return null
  return schoolsMap.value[id] || null
}

onMounted(async () => {
  try {
    const [schools, rankings, contests, users, parts] = await Promise.all([
      listSchools({ page_size: 100 }),
      listRankings({ scope: 'school', period: 'all', page: 1, page_size: 5 }),
      listContests({ page_size: 1 }),
      listUsers({ page_size: 1 }),
      listParticipations({ page_size: 1 }),
    ])
    schools.results.forEach((s) => (schoolsMap.value[s.id] = s))
    top5.value = rankings.results
    stats.value = {
      schools: schools.count,
      contests: contests.count,
      users: users.count,
      participations: parts.count,
    }
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="container-wide">
    <!-- Hero -->
    <div class="hero">
      <div class="hero-glow" />
      <div class="hero-orb" />
      <div class="hero-inner">
        <span class="badge badge-primary"><span class="dot dot-pulse" />已覆盖 {{ fmtCount(stats.schools) }} 所高校 · 实时同步三大平台</span>
        <h1 class="display">高校算法竞赛，<span class="gradient-text">谁与争锋</span></h1>
        <p class="body text-secondary hero-sub">
          自动采集 Codeforces、AtCoder、牛客三大平台比赛数据，按学校维度智能积分排名。让每一行代码的实力，被看见、被衡量、被铭记。
        </p>
        <div class="hero-actions">
          <router-link to="/u/rankings" class="btn btn-primary btn-lg">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 3v18h18" /><path d="M7 14l4-4 4 4 5-5" /></svg>
            查看排名
          </router-link>
          <router-link to="/u/contests" class="btn btn-secondary btn-lg">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4" /><path d="M10 17l5-5-5-5M15 12H3" /></svg>
            比赛列表
          </router-link>
        </div>
      </div>
    </div>

    <!-- Stats -->
    <div class="grid grid-4 stats-row">
      <div class="stat-card">
        <div style="display: flex; justify-content: space-between; align-items: flex-start">
          <div>
            <div class="stat-label">覆盖学校</div>
            <div class="stat-value num">{{ fmtCount(stats.schools) }}</div>
            <div class="stat-sub">所高校</div>
          </div>
          <div class="stat-icon primary"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 10v6M2 10l10-5 10 5-10 5z" /></svg></div>
        </div>
      </div>
      <div class="stat-card">
        <div style="display: flex; justify-content: space-between; align-items: flex-start">
          <div>
            <div class="stat-label">收录比赛</div>
            <div class="stat-value num">{{ fmtCount(stats.contests) }}</div>
            <div class="stat-sub">场赛事</div>
          </div>
          <div class="stat-icon cyan"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6M18 9h1.5a2.5 2.5 0 0 0 0-5H18M4 22h16M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22M18 2H6v7a6 6 0 0 0 12 0V2z" /></svg></div>
        </div>
      </div>
      <div class="stat-card">
        <div style="display: flex; justify-content: space-between; align-items: flex-start">
          <div>
            <div class="stat-label">在册学生</div>
            <div class="stat-value num">{{ fmtCount(stats.users) }}</div>
            <div class="stat-sub">名选手</div>
          </div>
          <div class="stat-icon success"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /></svg></div>
        </div>
      </div>
      <div class="stat-card">
        <div style="display: flex; justify-content: space-between; align-items: flex-start">
          <div>
            <div class="stat-label">参赛记录</div>
            <div class="stat-value num">{{ fmtCount(stats.participations) }}</div>
            <div class="stat-sub">条记录</div>
          </div>
          <div class="stat-icon warning"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6M8 13h8M8 17h5" /></svg></div>
        </div>
      </div>
    </div>

    <!-- Platforms -->
    <div class="section-block">
      <div class="section-title"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10" /><path d="M2 12h20M12 2a15 15 0 0 1 4 10 15 15 0 0 1-4 10 15 15 0 0 1-4-10 15 15 0 0 1 4-10z" /></svg>支持的平台</div>
      <div class="grid grid-3">
        <div v-for="p in platforms" :key="p.name" class="card card-hover card-pad">
          <div style="display: flex; align-items: center; gap: var(--space-4); margin-bottom: var(--space-4)">
            <div class="platform-logo" :style="{ background: p.color + '1f' }">
              <svg width="26" height="26" viewBox="0 0 24 24" :fill="p.color"><path :d="p.icon" /></svg>
            </div>
            <div>
              <div class="h4">{{ p.name }}</div>
              <div class="caption text-tertiary">{{ p.domain }}</div>
            </div>
          </div>
          <p class="body-sm text-secondary" style="margin-bottom: var(--space-4)">{{ p.desc }}</p>
          <div style="display: flex; gap: var(--space-4)">
            <div><div class="caption text-tertiary">收录比赛</div><div class="num" style="font-weight: 600; font-size: 15px">{{ p.contests }}</div></div>
            <div><div class="caption text-tertiary">活跃选手</div><div class="num" style="font-weight: 600; font-size: 15px">{{ p.users }}</div></div>
          </div>
        </div>
      </div>
    </div>

    <!-- Features -->
    <div class="section-block">
      <div class="section-title"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" /></svg>核心功能</div>
      <div class="grid grid-4">
        <div v-for="f in features" :key="f.title" class="card card-hover card-pad">
          <div class="stat-icon" :class="f.cls" style="margin-bottom: var(--space-4)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path :d="f.icon" /></svg></div>
          <div class="h4" style="margin-bottom: var(--space-2)">{{ f.title }}</div>
          <p class="body-sm text-secondary">{{ f.desc }}</p>
        </div>
      </div>
    </div>

    <!-- Top 5 -->
    <div class="section-block">
      <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-5)">
        <div class="section-title" style="margin-bottom: 0"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6M18 9h1.5a2.5 2.5 0 0 0 0-5H18M4 22h16M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22M18 2H6v7a6 6 0 0 0 12 0V2z" /></svg>学校榜 Top 5</div>
        <router-link to="/u/rankings" class="btn btn-ghost btn-sm">查看完整榜单 <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M12 5l7 7-7 7" /></svg></router-link>
      </div>
      <div class="card" style="overflow: hidden">
        <div class="table-wrap" style="border: none; border-radius: 0">
          <table class="data-table">
            <colgroup>
              <col style="width: 80px" />
              <col />
              <col style="width: 120px" />
              <col style="width: 130px" />
            </colgroup>
            <thead>
              <tr><th class="center">排名</th><th>学校</th><th class="num-cell">积分</th><th class="num-cell hide-mobile">参赛人数</th></tr>
            </thead>
            <tbody>
              <tr v-for="r in top5" :key="r.id" :class="medalRowClass(r.rank)">
                <td class="center"><RankBadge :rank="r.rank" /></td>
                <td>
                  <div class="cell-org">
                    <OrgLogo :name="schoolMeta(r.school)?.name || r.school_name" :short-name="schoolMeta(r.school)?.short_name || null" />
                    <span class="cell-ellipsis">{{ r.school_name }}</span>
                  </div>
                </td>
                <td class="score num-cell">{{ fmtScore(r.total_score) }}</td>
                <td class="num-cell center hide-mobile">{{ fmtCount(r.member_count) }}</td>
              </tr>
              <tr v-if="!loading && top5.length === 0"><td colspan="4" class="empty-cell">暂无榜单数据</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.hero {
  position: relative;
  border-radius: var(--radius-2xl);
  overflow: hidden;
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  margin-bottom: var(--space-12);
}
.hero-glow {
  position: absolute;
  inset: 0;
  background: var(--gradient-hero-glow);
  pointer-events: none;
}
.hero-orb {
  position: absolute;
  top: -40%;
  right: -10%;
  width: 500px;
  height: 500px;
  background: radial-gradient(circle, rgba(139, 92, 246, 0.12), transparent 70%);
  pointer-events: none;
}
.hero-inner {
  position: relative;
  padding: var(--space-20) var(--space-12) var(--space-16);
  text-align: center;
}
.hero-sub {
  max-width: 640px;
  margin: 0 auto var(--space-8);
  font-size: 18px;
}
.hero-actions {
  display: flex;
  gap: var(--space-4);
  justify-content: center;
  flex-wrap: wrap;
}
.section-block {
  margin-bottom: var(--space-12);
}
.platform-logo {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.data-table td.score {
  color: var(--color-primary);
  font-weight: 700;
  font-size: 15px;
}
.empty-cell {
  text-align: center;
  color: var(--color-text-tertiary);
  padding: var(--space-6);
}
@media (max-width: 860px) {
  .hero-inner { padding: var(--space-12) var(--space-5) var(--space-10); }
  .hero-sub { font-size: 16px; }
}
</style>
