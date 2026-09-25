<script setup lang="ts">
/**
 * 日历焦点区：下一场开赛倒计时 + 正在进行进度 + 赛程总览。
 *
 * 为什么单独成一个组件：倒计时要秒级跳动，而月历的 42 格与列表几十行都按分钟
 * 派生状态。放在同一个组件里会让每秒都重渲染整页（并连带重算 statusOf/relLabel），
 * 拆出来后这个 1s 定时器只影响这一小块 DOM。
 */
import { computed, onUnmounted, ref } from 'vue'
import type { Contest, ContestMeta } from '@/api/types'
import { platformClass } from '@/platforms/meta'
import {
  countdownParts,
  formatDateTime,
  formatDuration,
  progressPct,
  rangeLabel,
  relativeLabel,
} from '@/utils/format'

const props = defineProps<{
  next: Contest | null
  live: Contest | null
  liveCount: number
  meta: ContestMeta | null
}>()

/** 每秒只推这一个 ref；页面隐藏时不空转 */
const at = ref(Date.now())
let timer: number | undefined

function start() {
  window.clearInterval(timer)
  timer = window.setInterval(() => {
    at.value = Date.now()
  }, 1000)
}
function onStop() {
  if (document.hidden) window.clearInterval(timer)
  else start()
}
document.addEventListener('visibilitychange', onStop)
start()

onUnmounted(() => {
  window.clearInterval(timer)
  document.removeEventListener('visibilitychange', onStop)
})

const cdParts = computed(() => countdownParts(props.next?.start_time ?? null, at.value))
const livePct = computed(() => progressPct(props.live, at.value))
const liveLeft = computed(() =>
  props.live ? relativeLabel(props.live, at.value) : '',
)
const visible = computed(() => Boolean(props.next || props.live))
const scheduleSyncLabel = computed(() => {
  const iso = props.meta?.schedule_synced_at
  if (!iso) return '未知'
  return new Date(iso).toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
})
</script>

<template>
  <div v-if="visible" class="cal-hero">
    <div v-if="next" class="cal-hero-cell">
      <div class="cal-hero-kicker">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3.5 2" /></svg>
        下一场开赛
      </div>
      <div class="cal-hero-name">
        <span class="platform-tag" :class="platformClass(next.platform)">
          {{ next.platform_display }}
        </span>
        <span class="cal-hero-title">{{ next.name }}</span>
      </div>
      <div class="cal-hero-sub">
        {{ formatDateTime(next.start_time) }} · {{ formatDuration(next.duration_minutes) }}
        <template v-if="next.series"> · {{ next.series }}</template>
      </div>
      <div v-if="cdParts.length" class="cal-countdown">
        <span v-for="seg in cdParts" :key="seg.k" class="cal-cd">
          <b class="num">{{ seg.v }}</b>
          <i>{{ seg.k }}</i>
        </span>
      </div>
      <div v-else class="cal-hero-sub">正在开赛，稍后刷新即见</div>
      <a
        v-if="next.url"
        :href="next.url"
        target="_blank"
        rel="noopener"
        class="cal-hero-go"
      >前往赛场 →</a>
    </div>

    <div v-if="live" class="cal-hero-cell">
      <div class="cal-hero-kicker">
        <i class="cal-live-dot" />
        正在进行
        <span v-if="liveCount > 1" class="cal-live-more">+{{ liveCount - 1 }}</span>
      </div>
      <div class="cal-hero-name">
        <span class="platform-tag" :class="platformClass(live.platform)">
          {{ live.platform_display }}
        </span>
        <span class="cal-hero-title">{{ live.name }}</span>
      </div>
      <div class="cal-progress" :title="`已进行 ${Math.round(livePct)}%`">
        <i :style="{ width: livePct + '%' }" />
      </div>
      <div class="cal-hero-sub">
        {{ liveLeft || '不足 1 分钟即结束' }} · {{ rangeLabel(live) }}
      </div>
    </div>

    <div v-if="meta" class="cal-hero-cell cal-hero-statcell">
      <div class="cal-hero-kicker">赛程总览</div>
      <div class="cal-hero-stats">
        <div>
          <b class="num">{{ meta.catalog }}</b>
          <span>已收录赛事</span>
        </div>
        <div>
          <b class="num">{{ meta.upcoming }}</b>
          <span>排期中的场次</span>
        </div>
        <div>
          <b class="num">{{ meta.ongoing }}</b>
          <span>此刻正在进行</span>
        </div>
      </div>
      <div class="cal-hero-sub">
        排期来自
        <a class="cal-hero-src" href="https://clist.by/" target="_blank" rel="noopener">
          clist.by
        </a>
        聚合，往后看 90 天 · 最近刷新 {{ scheduleSyncLabel }}
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 视觉基调沿用全站 Dark Tech Indigo：玻璃底 + 主色渐变描边 + 顶部辉光。
   华丽点集中在倒计时数字与进度条，二者都是状态载体；入场一次性，
   循环动画只有 LIVE 点的透明度呼吸（合成层，不触发布局）。 */
.cal-hero {
  position: relative;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: var(--space-5); /* 基准按窄屏一档，≥768px 放宽到 space-6 */
  align-items: start;
  padding: var(--space-5);
  margin-bottom: var(--space-6);
  border: 1px solid var(--glass-border-color);
  border-radius: var(--radius-lg);
  background: var(--color-bg-surface);
  box-shadow: var(--shadow-glow);
  isolation: isolate;
  animation: hero-rise var(--duration-slower) var(--ease-out) backwards;
}
@keyframes hero-rise {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
/* 渐变辉光单独铺一层并用 opacity 调档：直接叠在底色上时浅色主题会被压成
   一大块薰衣草色 */
.cal-hero::after {
  content: '';
  position: absolute;
  inset: 0;
  z-index: -1;
  border-radius: inherit;
  background: var(--gradient-hero-glow), var(--gradient-primary-soft);
  opacity: 0.45;
  pointer-events: none;
}
/* 渐变 hairline：压在边框上，只在顶部最亮 */
.cal-hero::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  padding: 1px;
  background: var(--gradient-primary);
  -webkit-mask:
    linear-gradient(#000 0 0) content-box,
    linear-gradient(#000 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  opacity: 0.35;
  pointer-events: none;
}
.cal-hero-cell {
  min-width: 0;
}
.cal-hero-kicker {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-xs);
  font-weight: 600;
  letter-spacing: 0.04em;
  color: var(--color-text-tertiary);
  text-transform: uppercase;
}
.cal-hero-kicker svg {
  width: 14px;
  height: 14px;
}
.cal-hero-name {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin: var(--space-3) 0 var(--space-1);
  min-width: 0;
}
.cal-hero-title {
  font-size: var(--text-lg);
  font-weight: 700;
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.cal-hero-sub {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}
/* A4：主色 #6366f1 当文字只有 4.1~4.5:1，链接一律走「文本安全色」档 */
.cal-hero-go {
  display: inline-block;
  margin-top: var(--space-4);
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-primary-text);
}
.cal-hero-src {
  color: var(--color-text-secondary);
  text-decoration: underline;
  text-underline-offset: 2px;
}
.cal-hero-go:focus-visible,
.cal-hero-src:focus-visible {
  outline: 2px solid var(--color-primary-text);
  outline-offset: 2px;
}
/* R5：悬停增强只在真有 hover 的设备上生效 */
@media (hover: hover) {
  .cal-hero-go:hover {
    color: var(--color-text-primary);
  }
  .cal-hero-src:hover {
    color: var(--color-primary-text);
  }
}
.cal-hero-stats {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  margin: var(--space-3) 0 var(--space-2);
}
.cal-hero-stats div {
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
}
.cal-hero-stats b {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  font-size: var(--text-xl);
  font-weight: 700;
  color: var(--color-text-primary);
  min-width: 40px;
}
.cal-hero-stats span {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}
.cal-hero-statcell {
  /* 基准（窄屏）：竖排堆叠时不该有左分隔线；≥768px 并排才立这根线 */
  border-left: none;
  padding-left: 0;
}

/* 倒计时：等宽数字 + 渐变字面，每秒只改文本，不动布局 */
.cal-countdown {
  display: flex;
  gap: var(--space-2);
  margin-top: var(--space-4);
}
.cal-cd {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-05);
  min-width: 48px; /* 基准按窄屏 4 组倒计时能平排；宽屏再加宽 */
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--glass-bg);
}
.cal-cd b {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  font-size: var(--text-xl);
  line-height: 1.1;
  font-weight: 700;
  background: var(--gradient-primary);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.cal-cd i {
  font-style: normal;
  font-size: var(--text-2xs);
  color: var(--color-text-tertiary);
}

/* LIVE 指示：只动 opacity（合成层），不插值 box-shadow（那会逐帧重绘） */
.cal-live-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--color-success);
  box-shadow: 0 0 0 3px var(--color-success-subtle);
  animation: cal-breathe 2.4s var(--ease-in-out) infinite;
}
@keyframes cal-breathe {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.45;
  }
}
.cal-live-more {
  font-family: var(--font-mono);
  font-size: var(--text-2xs);
  color: var(--color-text-tertiary);
}
.cal-progress {
  height: 6px;
  margin: var(--space-4) 0 var(--space-2);
  border-radius: var(--radius-full);
  background: var(--color-bg-inset);
  overflow: hidden;
}
.cal-progress i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--gradient-primary);
  /* P5：不对 width 做逐帧补间（每帧重排）。原来的 `transition: width 300ms`
     本意是「摊平每秒的跳变」，但秒级增量 = 1/比赛时长 ≈ 0.01%，在 600px 的条上
     连一个像素都不到，去掉过渡后视觉等价、且不再有任何布局动画。 */
}

/* R1 移动优先：基准已是窄屏形态，这里只恢复宽屏排布。
   断点唯一事实源见 tokens.css --bp-md，改值得两处一起改。 */
@media (min-width: 768px) {
  .cal-hero {
    gap: var(--space-6);
    padding: var(--space-6);
  }
  .cal-hero-statcell {
    border-left: 1px solid var(--color-divider);
    padding-left: var(--space-6);
  }
  .cal-cd {
    min-width: 58px;
  }
  .cal-cd b {
    font-size: var(--text-2xl);
  }
}
</style>
