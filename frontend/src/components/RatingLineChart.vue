<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { platformLabel } from '@/platforms/meta'

interface Tier {
  min: number
  color: string
}
interface TierSet {
  tiers: Tier[]
  lines: number[]
}

// 各平台官方段位配置：tiers 的 min 为该档起点，lines 为参考线阈值（= 档位边界）。
// ⚠️ 只服务「有平台 rating 的计分平台」；注册表里新增可计分平台时必须在这里补一份
// 段位表，否则折线图会静默退化成站点品牌色、右侧段位标尺一起消失。
const TIER_SETS: Record<string, TierSet> = {
  codeforces: {
    tiers: [
      { min: 0, color: '#9aa0a6' },
      { min: 1200, color: '#43a047' },
      { min: 1400, color: '#26c6da' },
      { min: 1600, color: '#5c6bc0' },
      { min: 1900, color: '#ab47bc' },
      { min: 2100, color: '#ffa726' },
      { min: 2400, color: '#ef5350' },
      { min: 3000, color: '#c62828' },
    ],
    lines: [1200, 1400, 1600, 1900, 2100, 2400, 3000],
  },
  atcoder: {
    tiers: [
      { min: 0, color: '#9aa0a6' },
      { min: 400, color: '#8d6e63' },
      { min: 800, color: '#43a047' },
      { min: 1200, color: '#26c6da' },
      { min: 1600, color: '#5c6bc0' },
      { min: 2000, color: '#fbc02d' },
      { min: 2400, color: '#ffa726' },
      { min: 2800, color: '#ef5350' },
    ],
    lines: [400, 800, 1200, 1600, 2000, 2400, 2800],
  },
  nowcoder: {
    tiers: [
      { min: 0, color: '#9aa0a6' },
      { min: 700, color: '#ab47bc' },
      { min: 1100, color: '#5c6bc0' },
      { min: 1500, color: '#26a69a' },
      { min: 2000, color: '#fbc02d' },
      { min: 2400, color: '#ffa726' },
      { min: 2800, color: '#ef5350' },
    ],
    lines: [700, 1100, 1500, 2000, 2400, 2800],
  },
}

interface Point {
  label: string
  value: number
  meta?: Record<string, any>
}

const props = withDefaults(
  defineProps<{
    points: Point[]
    height?: number
    color?: string
    /** 单平台时启用该平台段位着色与参考线；空串为聚合口径（品牌色） */
    platform?: string
  }>(),
  { height: 220, color: 'var(--brand)', platform: '' },
)

const W = 720
const H = computed(() => props.height)
const tierSet = computed(() =>
  props.platform ? TIER_SETS[props.platform] ?? null : null,
)
const PAD = computed(() => ({
  top: 18,
  right: tierSet.value ? 46 : 16,
  bottom: 40,
  left: 44,
}))

function tierColor(v: number): string {
  const ts = tierSet.value
  if (!ts) return props.color
  let c = ts.tiers[0].color
  for (const t of ts.tiers) if (v >= t.min) c = t.color
  return c
}

const geom = computed(() => {
  const pts = [...props.points].sort(
    (a, b) => new Date(a.label).getTime() - new Date(b.label).getTime(),
  )
  if (pts.length === 0) return null
  const vals = pts.map((p) => p.value)
  let min = Math.min(...vals)
  let max = Math.max(...vals)
  if (min === max) {
    min -= 10
    max += 10
  }
  const pad = (max - min) * 0.12
  min -= pad
  max += pad
  const p = PAD.value
  const innerW = W - p.left - p.right
  const innerH = H.value - p.top - p.bottom
  const x = (i: number) =>
    p.left + (pts.length === 1 ? innerW / 2 : (i / (pts.length - 1)) * innerW)
  const y = (v: number) => p.top + innerH - ((v - min) / (max - min)) * innerH
  const coords = pts.map((pt, i) => ({ ...pt, cx: x(i), cy: y(pt.value) }))
  // path（M/L 折线），便于 getTotalLength 做描线动画
  const path = coords
    .map((c, i) => `${i === 0 ? 'M' : 'L'} ${c.cx} ${c.cy}`)
    .join(' ')
  const area = `${p.left},${p.top + innerH} ${coords
    .map((c) => `${c.cx},${c.cy}`)
    .join(' ')} ${coords[coords.length - 1].cx},${p.top + innerH}`
  const ticks = Array.from({ length: 5 }, (_, i) => {
    const v = min + ((max - min) * i) / 4
    return { v: Math.round(v), y: y(v) }
  })
  const xTicks = pickXTicks(coords)
  return { coords, path, area, ticks, xTicks, min, max, y, bottom: p.top + innerH }
})

function pickXTicks(coords: { label: string; cx: number }[]) {
  if (coords.length === 0) return []
  if (coords.length === 1) return [{ ...coords[0], i: 0 }]
  const idxs = new Set<number>([0, coords.length - 1])
  const step = Math.max(1, Math.floor((coords.length - 1) / 5))
  for (let i = step; i < coords.length - 1; i += step) idxs.add(i)
  return [...idxs]
    .sort((a, b) => a - b)
    .map((i) => ({ ...coords[i], i }))
}

// 段位参考线：只画落在可见 Y 范围内的
const tierLines = computed(() => {
  const ts = tierSet.value
  const g = geom.value
  if (!ts || !g) return []
  return ts.lines
    .filter((v) => v > g.min && v < g.max)
    .map((v) => ({ v, y: g.y(v), color: tierColor(v) }))
})

// 最新点小旗（当前 rating 锚点）
const flag = computed(() => {
  const g = geom.value
  if (!g || g.coords.length === 0) return null
  const last = g.coords[g.coords.length - 1]
  return { x: last.cx, y: last.cy, color: tierColor(last.value) }
})

// 面积渐变主色：段位模式用最新点段位色，聚合模式用品牌色
const areaColor = computed(() => {
  const g = geom.value
  if (tierSet.value && g && g.coords.length > 0) {
    return tierColor(g.coords[g.coords.length - 1].value)
  }
  return props.color
})

// ---- hover 交互 ----
const hoverIndex = ref<number | null>(null)

function onMove(e: MouseEvent) {
  const svg = e.currentTarget as SVGSVGElement
  const rect = svg.getBoundingClientRect()
  if (rect.width === 0) return
  const px = ((e.clientX - rect.left) / rect.width) * W
  const g = geom.value
  if (!g || g.coords.length === 0) return
  let best = 0
  let bestDist = Infinity
  g.coords.forEach((c, i) => {
    const d = Math.abs(c.cx - px)
    if (d < bestDist) {
      bestDist = d
      best = i
    }
  })
  hoverIndex.value = best
}
function onLeave() {
  hoverIndex.value = null
}

const hoverPoint = computed(() => {
  const g = geom.value
  if (g === null || hoverIndex.value == null) return null
  return g.coords[hoverIndex.value]
})

function hexToRgb(hex: string): [number, number, number] | null {
  const m = /^#([0-9a-f]{6})$/i.exec(hex)
  if (!m) return null
  const n = parseInt(m[1], 16)
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255]
}
function darken(hex: string, f = 0.72): string {
  const rgb = hexToRgb(hex)
  if (!rgb) return hex
  const [r, g, b] = rgb.map((v) => Math.round(v * f))
  return `rgb(${r}, ${g}, ${b})`
}

// tooltip 头部段位色渐变（非段位模式用品牌色平面色）
const tipHeadBg = computed(() => {
  const p = hoverPoint.value
  if (!p) return ''
  const c = tierColor(p.value)
  if (c.startsWith('#')) return `linear-gradient(135deg, ${c}, ${darken(c)})`
  return c
})

// tooltip 定位：默认在点下方，靠近底部翻到上方；靠近右缘水平翻转。带过渡实现平滑跟随。
const tipStyle = computed(() => {
  const p = hoverPoint.value
  if (!p) return {} as Record<string, string>
  const xr = p.cx / W
  const yr = p.cy / H.value
  const s: Record<string, string> = {}
  if (xr > 0.62) {
    s.left = 'auto'
    s.right = `${(1 - xr) * 100}%`
  } else {
    s.left = `${xr * 100}%`
    s.right = 'auto'
  }
  const tx = xr > 0.62 ? '50%' : '-50%'
  if (yr > 0.6) {
    // 点靠下 → tooltip 放上方
    s.top = `calc(${yr * 100}% - 14px)`
    s.transform = `translate(${tx}, -100%)`
  } else {
    s.top = `calc(${yr * 100}% + 16px)`
    s.transform = `translate(${tx}, 0)`
  }
  return s
})

function fmtDateLabel(s: string) {
  const d = new Date(s)
  if (isNaN(d.getTime())) return s
  return d.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
}
function fmtDateTime(s: string) {
  const d = new Date(s)
  if (isNaN(d.getTime())) return s
  const p2 = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p2(d.getMonth() + 1)}-${p2(d.getDate())} ${p2(
    d.getHours(),
  )}:${p2(d.getMinutes())}`
}
function fmtNum(v: number) {
  return v.toLocaleString('en-US')
}

// ---- 进场动画 ----
const lineRef = ref<SVGPathElement | null>(null)
const animKey = ref(0)

function runLineAnim() {
  const el = lineRef.value
  if (!el) return
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  const L = el.getTotalLength()
  el.style.transition = 'none'
  el.style.strokeDasharray = reduce ? 'none' : `${L}`
  el.style.strokeDashoffset = reduce ? '0' : `${L}`
  if (reduce) return
  void el.getBoundingClientRect() // 强制回流后启动过渡
  el.style.transition = 'stroke-dashoffset 0.9s cubic-bezier(0.4, 0, 0.2, 1)'
  el.style.strokeDashoffset = '0'
}

onMounted(() => {
  runLineAnim()
})
watch(
  [() => props.points, () => props.platform],
  () => {
    animKey.value++
    hoverIndex.value = null
    runLineAnim()
  },
  { flush: 'post' },
)

const stagger = computed(() => {
  const g = geom.value
  const n = g ? g.coords.length : 1
  return Math.min(60, Math.floor(900 / Math.max(n, 1)))
})

const gradId = `rg-${Math.random().toString(36).slice(2, 8)}`
</script>

<template>
  <div class="chart-wrap">
    <div v-if="geom" class="chart-area">
      <svg
        :viewBox="`0 0 ${W} ${H}`"
        width="100%"
        :height="H"
        preserveAspectRatio="xMidYMid meet"
        @mousemove="onMove"
        @mouseleave="onLeave"
      >
        <defs>
          <linearGradient :id="gradId" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" :stop-color="areaColor" :stop-opacity="tierSet ? 0.14 : 0.2" />
            <stop offset="100%" :stop-color="areaColor" stop-opacity="0.02" />
          </linearGradient>
        </defs>

        <!-- Y 轴网格与刻度 -->
        <g>
          <line
            v-for="t in geom.ticks"
            :key="t.v"
            :x1="PAD.left"
            :x2="W - PAD.right"
            :y1="t.y"
            :y2="t.y"
            stroke="var(--color-divider)"
            stroke-width="1"
            stroke-dasharray="3 4"
          />
          <text
            v-for="t in geom.ticks"
            :key="'l' + t.v"
            :x="PAD.left - 8"
            :y="t.y + 4"
            text-anchor="end"
            font-size="11"
            fill="var(--color-text-tertiary)"
          >
            {{ fmtNum(t.v) }}
          </text>
        </g>

        <!-- 段位参考线（仅单平台模式，画在可见范围内的档位边界） -->
        <g v-if="tierSet" :key="'tiers-' + animKey" class="tier-g">
          <line
            v-for="t in tierLines"
            :key="'t' + t.v"
            :x1="PAD.left"
            :x2="W - PAD.right"
            :y1="t.y"
            :y2="t.y"
            :stroke="t.color"
            stroke-opacity="0.45"
            stroke-width="1"
            stroke-dasharray="4 5"
          />
          <text
            v-for="t in tierLines"
            :key="'tl' + t.v"
            :x="W - PAD.right + 6"
            :y="t.y + 3.5"
            text-anchor="start"
            font-size="10"
            font-weight="600"
            :fill="t.color"
          >
            {{ t.v }}
          </text>
        </g>

        <!-- X 轴时间刻度 -->
        <g>
          <text
            v-for="t in geom.xTicks"
            :key="'x' + t.i"
            :x="t.cx"
            :y="H - 14"
            text-anchor="middle"
            font-size="10"
            fill="var(--color-text-tertiary)"
          >
            {{ fmtDateLabel(t.label) }}
          </text>
        </g>

        <!-- 面积 + 折线 -->
        <polygon :key="'area-' + animKey" :points="geom.area" :fill="`url(#${gradId})`" class="area-in" />
        <path
          ref="lineRef"
          :d="geom.path"
          fill="none"
          :stroke="tierSet ? 'var(--color-text-tertiary)' : color"
          :stroke-opacity="tierSet ? 0.6 : 1"
          :stroke-width="tierSet ? 1.5 : 2.5"
          stroke-linejoin="round"
          stroke-linecap="round"
        />

        <!-- hover 垂直参考线 -->
        <line
          v-if="hoverPoint"
          :x1="hoverPoint.cx"
          :x2="hoverPoint.cx"
          :y1="PAD.top"
          :y2="geom.bottom"
          stroke="var(--color-text-tertiary)"
          stroke-width="1"
          stroke-dasharray="2 3"
        />

        <!-- 数据点（段位模式按档位着色） -->
        <g :key="'pts-' + animKey">
          <g v-for="(c, i) in geom.coords" :key="i">
            <circle
              v-if="hoverIndex === i"
              class="halo"
              :cx="c.cx"
              :cy="c.cy"
              r="10"
              :fill="tierColor(c.value)"
            />
            <circle
              class="pt"
              :style="{ animationDelay: `${i * stagger}ms` }"
              :cx="c.cx"
              :cy="c.cy"
              :r="hoverIndex === i ? 5.5 : 3.5"
              :fill="tierColor(c.value)"
              :stroke="hoverIndex === i ? 'var(--color-bg-surface)' : 'none'"
              :stroke-width="hoverIndex === i ? 1.5 : 0"
            />
          </g>
        </g>

        <!-- 最新点小旗（当前 rating 锚点） -->
        <g v-if="flag" :key="'flag-' + animKey" class="flag-in">
          <line
            :x1="flag.x"
            :x2="flag.x"
            :y1="flag.y - 4"
            :y2="flag.y - 22"
            :stroke="flag.color"
            stroke-width="1.6"
            stroke-linecap="round"
          />
          <path
            :d="`M ${flag.x} ${flag.y - 22} L ${flag.x + 12} ${flag.y - 18} L ${flag.x} ${flag.y - 14} Z`"
            :fill="flag.color"
          />
        </g>
      </svg>

      <!-- 悬浮提示卡片 -->
      <Transition name="tip">
        <div v-if="hoverPoint" class="chart-tip" :style="tipStyle">
          <div class="tip-head" :style="{ background: tipHeadBg }">
            <b class="num">{{ hoverPoint.value }}</b>
            <span v-if="hoverPoint.meta?.delta != null" class="tip-delta">
              ({{ hoverPoint.meta.delta > 0 ? '+' : '' }}{{ hoverPoint.meta.delta }})
            </span>
            <span v-if="hoverPoint.meta?.rank != null" class="tip-rank">
              (第 {{ hoverPoint.meta.rank }} 名)
            </span>
          </div>
          <div class="tip-body">
            <div v-if="hoverPoint.meta?.contest" class="tip-contest">
              <span
                v-if="!tierSet && hoverPoint.meta?.platform"
                class="platform-tag"
              >{{ platformLabel(hoverPoint.meta.platform) }}</span>
              {{ hoverPoint.meta.contest }}
            </div>
            <div class="tip-time">{{ fmtDateTime(hoverPoint.label) }}</div>
          </div>
        </div>
      </Transition>
    </div>
    <div v-else class="empty">暂无评分变化数据</div>
  </div>
</template>

<style scoped>
.chart-wrap {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 8px 8px 0;
  width: 100%;
  background: var(--color-bg-surface);
}
.chart-area {
  position: relative;
}
.chart-area svg {
  display: block;
}
.empty {
  padding: 40px;
  text-align: center;
  color: var(--color-text-tertiary);
  font-size: 13px;
}

/* ---- 进场动画 ---- */
.pt {
  transform-box: fill-box;
  transform-origin: center;
  animation: pt-in 0.35s ease-out backwards;
  transition: r 0.15s ease;
}
.halo {
  opacity: 0.18;
  animation: pt-in 0.18s ease-out backwards;
  transform-box: fill-box;
  transform-origin: center;
}
.area-in {
  animation: fade-in 0.8s ease-out 0.25s backwards;
}
.tier-g {
  animation: fade-in 0.7s ease-out 0.1s backwards;
}
.flag-in {
  animation: fade-in 0.5s ease-out 0.85s backwards;
}
@keyframes pt-in {
  from {
    opacity: 0;
    transform: scale(0);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}
@keyframes fade-in {
  from {
    opacity: 0;
  }
}

/* ---- tooltip ---- */
.chart-tip {
  position: absolute;
  top: 0;
  left: 0;
  min-width: 150px;
  max-width: 250px;
  border-radius: var(--radius-md);
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-lg);
  pointer-events: none;
  z-index: 10;
  font-size: 12px;
  overflow: hidden;
  transition:
    left 0.16s ease-out,
    right 0.16s ease-out,
    top 0.16s ease-out;
}
.tip-head {
  display: flex;
  align-items: baseline;
  gap: 5px;
  padding: 7px 12px;
  color: #fff;
  white-space: nowrap;
}
.tip-head b {
  font-size: 17px;
  font-weight: 700;
  letter-spacing: 0.01em;
}
.tip-delta,
.tip-rank {
  font-size: 12px;
  font-weight: 600;
  opacity: 0.92;
}
.tip-body {
  padding: 8px 12px 9px;
}
.tip-contest {
  color: var(--color-text-secondary);
  line-height: 1.45;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.tip-contest .platform-tag {
  margin-right: 6px;
}
.tip-time {
  color: var(--color-text-tertiary);
  margin-top: 3px;
}
.tip-enter-active,
.tip-leave-active {
  transition: opacity 0.12s ease;
}
.tip-enter-from,
.tip-leave-to {
  opacity: 0;
}

@media (prefers-reduced-motion: reduce) {
  .pt,
  .halo,
  .area-in,
  .tier-g,
  .flag-in {
    animation: none;
  }
  .chart-tip {
    transition: none;
  }
}
</style>
