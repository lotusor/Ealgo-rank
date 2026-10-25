<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { getPublicStats, listRankings, listSchools } from '@/api'
import type { PublicStats } from '@/api'
import type { RankSnapshot, School } from '@/api/types'
import { ALL_PLATFORMS, platformMeta } from '@/platforms/meta'
import { fmtScore, fmtCount, medalRowClass, orgShort } from '@/utils/format'
import RankBadge from '@/components/ui/RankBadge.vue'
import OrgLogo from '@/components/ui/OrgLogo.vue'
import SeasonBanner from '@/components/SeasonBanner.vue'
import CountUp from '@/components/ui/CountUp.vue'

const top5 = ref<RankSnapshot[]>([])
const schoolsMap = ref<Record<number, School>>({})
const stats = ref<PublicStats>({
  schools: 0, contests: 0, users: 0, participations: 0, platforms: [],
})
const loading = ref(true)

/** 平台清单只有一份来源（`@/platforms/meta`），这里派生文案 */
const platformCount = ALL_PLATFORMS.length
const platformNames = ALL_PLATFORMS.map((p) => p.label).join('、')

/**
 * 「支持的平台」卡片：文案来自 meta，数字来自 /stats/ 的真实计数。
 * 原先这里是写死的 3 张卡 + `contests: 712 / users: 2103` 一组演示数字 ——
 * 加一个平台就得再编一个数，页面也会永远停在「三大平台」。
 */
const platformCards = computed(() =>
  stats.value.platforms.map((p) => {
    const m = platformMeta(p.key)
    return {
      ...p,
      icon: m?.icon ?? '',
      site: m?.site ?? p.key,
      desc: m?.desc ?? '',
    }
  }),
)

const features = [
  { icon: 'M3 3v18h18M7 14l4-4 4 4 5-5', cls: 'primary', title: '学校积分排名', desc: '按学校维度聚合选手成绩，科学积分模型，实时更新榜单。' },
  { icon: 'M3 3v18h18M7 14l4-4 4 4 5-5', cls: 'cyan', title: '个人成绩追踪', desc: '跨平台 Rating 折线图、参赛历史、积分明细，一目了然。' },
  { icon: 'M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M12 12a3 3 0 1 0 0 0', cls: 'success', title: '自动数据采集', desc: '爬虫定时同步各已接入平台的比赛成绩与赛程排期，零人工录入。' },
  { icon: 'M13 2L3 14h9l-1 8 10-12h-9l1-8z', cls: 'warning', title: '智能积分引擎', desc: '融合难度系数、参赛规模、排名表现，公平量化实力。' },
]

function schoolMeta(id: number | null) {
  if (id == null) return null
  return schoolsMap.value[id] || null
}

onMounted(async () => {
  // 统计数字来自公开端点（/stats/，AllowAny）：对所有用户口径一致
  getPublicStats()
    .then((s) => {
      stats.value = s
    })
    .catch(() => {})
  // 榜单与学校数据仍分别加载（列表渲染需要明细）
  listSchools({ page_size: 100 })
    .then((schools) => {
      schools.results.forEach((s) => (schoolsMap.value[s.id] = s))
    })
    .catch(() => {})
  listRankings({ scope: 'school', period: 'all', page: 1, page_size: 5 })
    .then((rankings) => {
      top5.value = rankings.results
    })
    .catch(() => {})
  loading.value = false
})
</script>

<template>
  <div class="container-wide home-page">
    <section class="home-masthead">
      <div class="home-masthead__copy">
        <p class="kicker kicker--accent">SEASON 2026 / 高校算法竞赛积分年鉴</p>
        <h1 class="home-title">每一行代码，<br />都该被<span class="stop">排名</span>看见。</h1>
        <p class="home-lede">
          自动汇聚 {{ platformNames }} 的比赛成绩与赛程排期，按学校与个人维度统一积分。让每一场竞赛，都有可追溯的名次。
        </p>
        <div class="home-actions">
          <router-link to="/u/rankings" class="btn btn-primary btn-lg">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 3v18h18" /><path d="M7 14l4-4 4 4 5-5" /></svg>
            查看排名
          </router-link>
          <router-link to="/u/contests" class="btn btn-secondary btn-lg">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4" /><path d="M10 17l5-5-5-5M15 12H3" /></svg>
            比赛列表
          </router-link>
          <router-link to="/calendar" class="btn btn-ghost btn-lg">竞赛日历 →</router-link>
        </div>
        <p class="home-meta">
          覆盖 <b>{{ fmtCount(stats.schools) }}</b> 所高校
          <span>·</span>
          同步 <b>{{ platformCount }}</b> 个赛事平台
          <span>·</span>
          数据来自公开赛果
        </p>
      </div>

      <aside v-sheen class="glass-lens home-ledger" aria-label="赛季数据快照">
        <div class="ledger__head">
          <span class="kicker">SEASON LEDGER</span>
          <span class="ledger__live"><i />LIVE</span>
        </div>
        <div class="ledger__grid">
          <div class="ledger__item">
            <span class="ledger__label">收录比赛</span>
            <strong class="ledger__value"><CountUp :value="stats.contests" /></strong>
            <small>场赛事</small>
          </div>
          <div class="ledger__item">
            <span class="ledger__label">在册学生</span>
            <strong class="ledger__value"><CountUp :value="stats.users" /></strong>
            <small>名选手</small>
          </div>
          <div class="ledger__item">
            <span class="ledger__label">覆盖学校</span>
            <strong class="ledger__value"><CountUp :value="stats.schools" /></strong>
            <small>所高校</small>
          </div>
          <div class="ledger__item">
            <span class="ledger__label">参赛记录</span>
            <strong class="ledger__value"><CountUp :value="stats.participations" /></strong>
            <small>条记录</small>
          </div>
        </div>
        <router-link to="/calendar" class="ledger__foot">
          <span>下一场开赛与完整赛程</span>
          <b>竞赛日历 →</b>
        </router-link>
      </aside>
    </section>

    <!-- Season banner -->
    <SeasonBanner />

    <!-- Platforms -->
    <section class="home-section">
      <div class="section-head">
        <div>
          <p class="kicker">PLATFORMS / 数据源</p>
          <h2 class="section-title">已接入的比赛平台</h2>
        </div>
        <span class="section-index">{{ String(platformCards.length).padStart(2, '0') }} SOURCES</span>
      </div>
      <div class="platform-grid">
        <article v-for="(p, index) in platformCards" :key="p.key" class="card platform-card">
          <div class="platform-card__top">
            <span class="platform-card__index">{{ String(index + 1).padStart(2, '0') }}</span>
            <span v-if="p.scoring" class="badge badge-muted">计分</span>
            <span v-else class="badge badge-muted">仅排期</span>
          </div>
          <div class="platform-card__brand">
            <div class="platform-logo" :class="p.key">
              <img
                :src="p.icon"
                :alt="p.label"
                width="26"
                height="26"
                loading="lazy"
                referrerpolicy="no-referrer"
                @error="(e) => ((e.target as HTMLImageElement).style.display = 'none')"
              />
            </div>
            <div>
              <h3 class="platform-card__name">{{ p.label }}</h3>
              <p class="platform-card__site">{{ p.site }}</p>
            </div>
          </div>
          <p class="platform-card__desc">{{ p.desc }}</p>
          <div v-if="p.scoring" class="platform-card__stats">
            <div><span>收录比赛</span><b><CountUp :value="p.contests" /></b></div>
            <div><span>活跃选手</span><b><CountUp :value="p.accounts" /></b></div>
          </div>
          <p v-else class="platform-card__note">赛程已接入，成绩待同步</p>
        </article>
      </div>
    </section>

    <!-- Features -->
    <section class="home-section">
      <div class="section-head">
        <div>
          <p class="kicker">METHOD / 方法</p>
          <h2 class="section-title">从赛果到积分</h2>
        </div>
        <span class="section-index">04 STEPS</span>
      </div>
      <div class="method-grid">
        <article v-for="(f, index) in features" :key="f.title" class="method">
          <span class="method__index">{{ String(index + 1).padStart(2, '0') }}</span>
          <h3 class="method__title">{{ f.title }}</h3>
          <p class="method__desc">{{ f.desc }}</p>
        </article>
      </div>
    </section>

    <!-- Top 5 -->
    <section class="home-section home-section--last">
      <div class="section-head">
        <div>
          <p class="kicker">LEADERBOARD / 学校榜</p>
          <h2 class="section-title">学校榜 Top 5</h2>
        </div>
        <router-link to="/u/rankings" class="btn btn-ghost btn-sm">查看完整榜单 <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M12 5l7 7-7 7" /></svg></router-link>
      </div>
      <div class="card" style="overflow: hidden">
        <div class="table-wrap" style="border: none; border-radius: 0">
          <table class="data-table">
            <colgroup>
              <col style="width: 64px" />
              <col />
              <col style="width: 110px" />
              <col style="width: 120px" />
            </colgroup>
            <thead>
              <tr><th class="center">排名</th><th>学校</th><th class="num-cell">积分</th><th class="center hide-mobile">参赛人数</th></tr>
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
                <td class="num center hide-mobile">{{ fmtCount(r.member_count) }}</td>
              </tr>
              <tr v-if="!loading && top5.length === 0"><td colspan="4" class="empty-cell">暂无榜单数据</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.home-page {
  padding-bottom: var(--space-6);
}
.home-masthead {
  display: grid;
  grid-template-columns: minmax(0, 1.12fr) minmax(320px, 0.78fr);
  gap: clamp(20px, 3vw, 40px);
  align-items: stretch;
  padding: var(--space-4) 0 var(--space-8);
  border-bottom: 1px solid var(--rule);
  margin-bottom: var(--space-6);
}
.home-masthead__copy {
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-width: 0;
}
.home-title {
  margin: var(--space-2) 0 var(--space-4);
  font-family: var(--font-display);
  font-size: clamp(2.4rem, 1.8rem + 2.6vw, 3.6rem);
  font-weight: 600;
  line-height: 1.06;
  letter-spacing: 0.005em;
}
.home-title .stop {
  color: var(--accent);
}
.home-lede {
  max-width: 60ch;
  margin: 0 0 var(--space-5);
  font-size: var(--text-base);
  line-height: 1.7;
  color: var(--ink-2);
}
.home-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
}
.home-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: var(--space-4);
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.06em;
  color: var(--ink-3);
}
.home-meta b {
  font-weight: 500;
  color: var(--ink);
}
.home-ledger {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  min-height: 260px;
  padding: 16px 18px 14px;
  overflow: hidden;
}
.ledger__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding-bottom: 10px;
  border-bottom: 1px solid var(--rule);
}
.ledger__live {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.14em;
  color: var(--accent);
}
.ledger__live i {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--accent);
  box-shadow: 0 0 0 3px var(--color-primary-subtle);
  animation: ledger-pulse 2.4s ease-in-out infinite;
}
.ledger__grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}
.ledger__item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 14px 12px 12px 0;
  border-bottom: 1px solid var(--rule);
}
.ledger__item:nth-child(odd) {
  border-right: 1px solid var(--rule);
}
.ledger__item:nth-child(even) {
  padding-left: 14px;
}
.ledger__item:nth-last-child(-n + 2) {
  border-bottom: 0;
}
.ledger__label {
  font-family: var(--font-mono);
  font-size: 9.5px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--ink-3);
}
.ledger__value {
  font-family: var(--font-mono);
  font-size: clamp(1.55rem, 1.3rem + 0.9vw, 1.95rem);
  font-weight: 400;
  line-height: 1.15;
  letter-spacing: -0.04em;
  color: var(--ink);
}
.ledger__item small {
  font-size: 10.5px;
  color: var(--ink-3);
}
.ledger__foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  margin-top: auto;
  padding-top: 12px;
  border-top: 1px solid var(--rule);
  font-size: 11px;
  color: var(--ink-3);
}
.ledger__foot b {
  font-weight: 500;
  color: var(--accent);
}
.home-section {
  margin-top: var(--space-8);
}
.home-section--last {
  margin-bottom: var(--space-5);
}
.section-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--space-3);
  flex-wrap: wrap;
  padding-bottom: 10px;
  margin-bottom: var(--space-4);
  border-bottom: 1px solid var(--rule);
}
.section-head .section-title {
  margin: 3px 0 0;
}
.section-index {
  font-family: var(--font-mono);
  font-size: 9.5px;
  letter-spacing: 0.12em;
  color: var(--ink-3);
}
.platform-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--space-4);
}
.platform-card {
  display: flex;
  flex-direction: column;
  min-width: 0;
  padding: 16px;
  background: var(--paper-2);
}
.platform-card__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  padding-bottom: 10px;
  border-bottom: 1px solid var(--rule);
}
.platform-card__index {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.08em;
  color: var(--accent);
}
.platform-card__brand {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin: 12px 0 10px;
}
.platform-logo {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  overflow: hidden;
  border: 1px solid var(--rule);
}
.platform-logo img {
  object-fit: contain;
  border-radius: 0;
}
.platform-logo.codeforces { background: color-mix(in srgb, var(--platform-codeforces) 10%, transparent); }
.platform-logo.atcoder { background: color-mix(in srgb, var(--platform-atcoder) 10%, transparent); }
.platform-logo.nowcoder { background: color-mix(in srgb, var(--platform-nowcoder) 10%, transparent); }
.platform-logo.luogu { background: color-mix(in srgb, var(--platform-luogu) 10%, transparent); }
.platform-card__name {
  margin: 0;
  font-family: var(--font-display);
  font-size: 1rem;
  font-weight: 600;
  line-height: 1.25;
}
.platform-card__site {
  margin: 1px 0 0;
  font-family: var(--font-mono);
  font-size: 9.5px;
  color: var(--ink-3);
}
.platform-card__desc {
  flex: 1;
  margin: 0 0 var(--space-3);
  font-size: 12px;
  line-height: 1.6;
  color: var(--ink-2);
}
.platform-card__stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-3);
  padding-top: 10px;
  border-top: 1px solid var(--rule);
}
.platform-card__stats span {
  display: block;
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.06em;
  color: var(--ink-3);
}
.platform-card__stats b {
  display: block;
  margin-top: 2px;
  font-family: var(--font-mono);
  font-size: 16px;
  font-weight: 500;
  letter-spacing: -0.03em;
  color: var(--ink);
}
.platform-card__note {
  margin: 0;
  padding-top: 12px;
  border-top: 1px solid var(--rule);
  font-size: 11px;
  color: var(--ink-3);
}
.method-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--space-5);
}
.method {
  padding-top: 12px;
  border-top: 1px solid var(--rule);
}
.method__index {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.08em;
  color: var(--accent);
}
.method__title {
  margin: 10px 0 6px;
  font-family: var(--font-display);
  font-size: 1.05rem;
  font-weight: 600;
}
.method__desc {
  margin: 0;
  font-size: 12px;
  line-height: 1.65;
  color: var(--ink-2);
}
.data-table td.score {
  color: var(--accent);
  font-weight: 600;
  font-size: 13.5px;
}
.empty-cell {
  text-align: center;
  color: var(--ink-3);
  padding: var(--space-6);
}
@keyframes ledger-pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.35;
  }
}
@media (max-width: 1023px) {
  .home-masthead {
    grid-template-columns: 1fr;
  }
  .home-ledger {
    min-height: 0;
  }
  .platform-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 767px) {
  .home-title {
    font-size: clamp(1.9rem, 1.35rem + 2.4vw, 2.35rem);
    line-height: 1.12;
  }
  .home-actions .btn {
    flex: 1;
  }
  .method-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: var(--space-4);
  }
}
@media (max-width: 559px) {
  .platform-grid,
  .method-grid {
    grid-template-columns: 1fr;
  }
  .ledger__item {
    padding-right: 8px;
  }
}
@media (prefers-reduced-motion: reduce) {
  .ledger__live i {
    animation: none;
  }
}
</style>
