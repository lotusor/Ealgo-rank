<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { platformClass, platformLabel } from '@/platforms/meta'
import CountUp from '@/components/ui/CountUp.vue'

interface Point {
  label: string
  value: number
  meta?: Record<string, any>
}

interface Tier {
  min: number
  color: string
}
interface TierSet {
  tiers: Tier[]
  lines: number[]
}

// 注册表新增「可计分且有平台 rating」的平台时，必须在这里补段位表；
// 缺表不会报错，但线段会退回强调色，段位参考线也会消失。
const TIER_SETS: Record<string, TierSet> = {
  codeforces: {
    tiers: [
      { min: 0, color: 'var(--chart-tier-none)' },
      { min: 1200, color: 'var(--chart-tier-green)' },
      { min: 1400, color: 'var(--chart-tier-cyan)' },
      { min: 1600, color: 'var(--chart-tier-blue)' },
      { min: 1900, color: 'var(--chart-tier-purple)' },
      { min: 2100, color: 'var(--chart-tier-orange)' },
      { min: 2400, color: 'var(--chart-tier-red)' },
      { min: 3000, color: 'var(--chart-tier-crimson)' },
    ],
    lines: [1200, 1400, 1600, 1900, 2100, 2400, 3000],
  },
  atcoder: {
    tiers: [
      { min: 0, color: 'var(--chart-tier-none)' },
      { min: 400, color: 'var(--chart-tier-brown)' },
      { min: 800, color: 'var(--chart-tier-green)' },
      { min: 1200, color: 'var(--chart-tier-cyan)' },
      { min: 1600, color: 'var(--chart-tier-blue)' },
      { min: 2000, color: 'var(--chart-tier-amber)' },
      { min: 2400, color: 'var(--chart-tier-orange)' },
      { min: 2800, color: 'var(--chart-tier-red)' },
    ],
    lines: [400, 800, 1200, 1600, 2000, 2400, 2800],
  },
  nowcoder: {
    tiers: [
      { min: 0, color: 'var(--chart-tier-none)' },
      { min: 700, color: 'var(--chart-tier-purple)' },
      { min: 1100, color: 'var(--chart-tier-blue)' },
      { min: 1500, color: 'var(--chart-tier-teal)' },
      { min: 2000, color: 'var(--chart-tier-amber)' },
      { min: 2400, color: 'var(--chart-tier-orange)' },
      { min: 2800, color: 'var(--chart-tier-red)' },
    ],
    lines: [700, 1100, 1500, 2000, 2400, 2800],
  },
}

const props = withDefaults(
  defineProps<{
    points: Point[]
    height?: number
    /** 空串 = 站内总积分；平台键 = 该平台官方 rating */
    platform?: string
  }>(),
  { height: 260, platform: '' },
)

const isAggregate = computed(() => !props.platform)
const tierSet = computed(() =>
  props.platform ? TIER_SETS[props.platform] ?? null : null,
)
const metricLabel = computed(() =>
  isAggregate.value ? '站内总积分' : '官方 Rating',
)
const modeLabel = computed(() =>
  isAggregate.value ? 'SITE TOTAL' : 'PLATFORM RATING',
)

const plotEl = ref<HTMLElement | null>(null)
const chartPlotEl = ref<HTMLElement | null>(null)
const width = ref(720)
const ready = ref(false)
const animKey = ref(0)

let resizeObserver: ResizeObserver | null = null
function measure() {
  const next = Math.max(280, Math.round(plotEl.value?.clientWidth || 720))
  if (next !== width.value) width.value = next
  ready.value = true
}

const H = computed(() =>
  width.value < 480 ? Math.max(210, props.height - 34) : props.height,
)
const PAD = computed(() => ({
  top: 24,
  right: tierSet.value ? (width.value < 400 ? 36 : 44) : 16,
  bottom: 32,
  left: width.value < 400 ? 36 : 46,
}))

function tierColor(value: number): string {
  const ts = tierSet.value
  if (!ts) return 'var(--accent)'
  let color = ts.tiers[0].color
  for (const tier of ts.tiers) if (value >= tier.min) color = tier.color
  return color
}

function niceStep(range: number) {
  const target = Math.max(25, range / 4)
  const steps = [10, 20, 25, 50, 100, 200, 250, 500, 1000, 2000]
  return steps.find((step) => step >= target) ?? 2000
}

interface ChartPoint extends Point {
  time: number
  cx: number
  cy: number
  index: number
}

const geom = computed(() => {
  if (!ready.value) return null
  const sorted = props.points
    .map((point) => ({ ...point, time: new Date(point.label).getTime() }))
    .filter((point) => Number.isFinite(point.time) && Number.isFinite(point.value))
    .sort((a, b) => a.time - b.time)
  if (!sorted.length) return null

  const p = PAD.value
  const innerW = width.value - p.left - p.right
  const innerH = H.value - p.top - p.bottom
  const times = sorted.map((point) => point.time)
  const minTime = Math.min(...times)
  const maxTime = Math.max(...times)
  const timeSpan = Math.max(1, maxTime - minTime)

  const values = sorted.map((point) => point.value)
  const minValue = Math.min(...values)
  const maxValue = Math.max(...values)
  const rawRange = Math.max(50, maxValue - minValue)
  const step = niceStep(rawRange)
  let low = Math.floor((minValue - rawRange * 0.12) / step) * step
  let high = Math.ceil((maxValue + rawRange * 0.12) / step) * step
  if (low === high) high += step

  const x = (time: number) =>
    p.left +
    (sorted.length === 1
      ? innerW / 2
      : ((time - minTime) / timeSpan) * innerW)
  const y = (value: number) =>
    p.top + innerH - ((value - low) / (high - low)) * innerH

  const coords: ChartPoint[] = sorted.map((point, index) => ({
    ...point,
    cx: x(point.time),
    cy: y(point.value),
    index,
  }))
  const tangents = monotoneTangents(coords)
  const baseline = p.top + innerH

  const ticks: { value: number; y: number }[] = []
  for (let value = low; value <= high + step * 0.01; value += step) {
    ticks.push({ value, y: y(value) })
  }

  const labelCount = width.value < 480 ? 3 : 5
  const xLabels = Array.from({ length: labelCount }, (_, index) => {
    const ratio = index / (labelCount - 1)
    const time = minTime + timeSpan * ratio
    return {
      x: p.left + innerW * ratio,
      text: formatAxisDate(time),
      anchor:
        index === 0 ? 'start' : index === labelCount - 1 ? 'end' : 'middle',
    }
  })

  const tierLines =
    tierSet.value && tierSet.value.lines.some((value) => value > low && value < high)
      ? tierSet.value.lines
          .filter((value) => value > low && value < high)
          .map((value) => ({ value, y: y(value), color: tierColor(value) }))
      : []

  return {
    coords,
    tangents,
    innerW,
    innerH,
    baseline,
    ticks,
    xLabels,
    tierLines,
    latest: coords[coords.length - 1],
  }
})

/**
 * 单调三次 Hermite（Fritsch–Carlson）切线。
 * 评分点的时间间隔并不均匀，普通 Catmull-Rom 在长间隔/急转折处会过冲，
 * 甚至让曲线回折成环；这里限制切线，保证每段 x 单调、y 不超出两端点范围。
 */
function monotoneTangents(points: ChartPoint[]): number[] {
  const n = points.length
  if (n < 2) return []
  const h: number[] = []
  const delta: number[] = []
  for (let i = 0; i < n - 1; i += 1) {
    const dx = points[i + 1].cx - points[i].cx
    h.push(dx)
    delta.push(dx > 0 ? (points[i + 1].cy - points[i].cy) / dx : 0)
  }
  const m = new Array<number>(n).fill(0)
  m[0] = delta[0]
  m[n - 1] = delta[n - 2]
  for (let i = 1; i < n - 1; i += 1) {
    const d0 = delta[i - 1]
    const d1 = delta[i]
    if (h[i - 1] <= 0 || h[i] <= 0 || d0 === 0 || d1 === 0 || d0 * d1 < 0) {
      m[i] = 0
      continue
    }
    const w1 = 2 * h[i] + h[i - 1]
    const w2 = h[i] + 2 * h[i - 1]
    m[i] = (w1 + w2) / (w1 / d0 + w2 / d1)
  }
  // 限制切线幅度，避免三次曲线越出相邻点范围
  for (let i = 0; i < n - 1; i += 1) {
    if (delta[i] === 0) {
      m[i] = 0
      m[i + 1] = 0
      continue
    }
    const a = m[i] / delta[i]
    const b = m[i + 1] / delta[i]
    const s = a * a + b * b
    if (s > 9) {
      const t = 3 / Math.sqrt(s)
      m[i] = t * a * delta[i]
      m[i + 1] = t * b * delta[i]
    }
  }
  return m
}

function cubicControls(p1: ChartPoint, p2: ChartPoint, t1: number, t2: number) {
  const h = p2.cx - p1.cx
  if (h <= 0) return null
  return {
    c1x: p1.cx + h / 3,
    c1y: p1.cy + (t1 * h) / 3,
    c2x: p2.cx - h / 3,
    c2y: p2.cy - (t2 * h) / 3,
  }
}

function smoothPath(points: ChartPoint[], tangents: number[]) {
  if (!points.length) return ''
  if (points.length === 1) return `M${points[0].cx.toFixed(1)},${points[0].cy.toFixed(1)}`
  let d = `M${points[0].cx.toFixed(1)},${points[0].cy.toFixed(1)}`
  for (let i = 0; i < points.length - 1; i += 1) {
    const p1 = points[i]
    const p2 = points[i + 1]
    const c = cubicControls(p1, p2, tangents[i] ?? 0, tangents[i + 1] ?? 0)
    d += c
      ? ` C${c.c1x.toFixed(1)},${c.c1y.toFixed(1)} ${c.c2x.toFixed(1)},${c.c2y.toFixed(1)} ${p2.cx.toFixed(1)},${p2.cy.toFixed(1)}`
      : ` L${p2.cx.toFixed(1)},${p2.cy.toFixed(1)}`
  }
  return d
}

function segmentPath(points: ChartPoint[], index: number, tangents: number[]) {
  const p1 = points[index]
  const p2 = points[index + 1]
  const c = cubicControls(p1, p2, tangents[index] ?? 0, tangents[index + 1] ?? 0)
  if (!c) return `M${p1.cx.toFixed(1)},${p1.cy.toFixed(1)} L${p2.cx.toFixed(1)},${p2.cy.toFixed(1)}`
  return `M${p1.cx.toFixed(1)},${p1.cy.toFixed(1)} C${c.c1x.toFixed(1)},${c.c1y.toFixed(1)} ${c.c2x.toFixed(1)},${c.c2y.toFixed(1)} ${p2.cx.toFixed(1)},${p2.cy.toFixed(1)}`
}

const areaPath = computed(() => {
  const g = geom.value
  if (!g || g.coords.length < 2) return ''
  const path = smoothPath(g.coords, g.tangents)
  const first = g.coords[0]
  const last = g.coords[g.coords.length - 1]
  return `M${first.cx.toFixed(1)},${g.baseline.toFixed(1)} L${first.cx.toFixed(1)},${first.cy.toFixed(1)} ${path.replace(/^M[^ ]+/, '')} L${last.cx.toFixed(1)},${g.baseline.toFixed(1)} Z`
})

const segments = computed(() => {
  const g = geom.value
  if (!g || g.coords.length < 2) return []
  return g.coords.slice(0, -1).map((point, index) => ({
    d: segmentPath(g.coords, index, g.tangents),
    color: tierColor(g.coords[index + 1].value),
    delay: Math.min(460, index * 26),
    target: g.coords[index + 1],
  }))
})

const latestValue = computed(() => geom.value?.latest.value ?? null)
const latestPrecision = computed(() => {
  const value = latestValue.value
  return value != null && !Number.isInteger(value) ? 1 : 0
})
const latestTier = computed(() => {
  const ts = tierSet.value
  const value = latestValue.value
  if (!ts || value == null) return null
  let index = 0
  for (let i = 0; i < ts.tiers.length; i += 1) {
    if (value >= ts.tiers[i].min) index = i
  }
  const next = ts.tiers[index + 1]
  return { min: ts.tiers[index].min, max: next ? next.min - 1 : null }
})
const tierRangeText = computed(() => {
  const tier = latestTier.value
  if (!tier) return ''
  return `段位 ${tier.min}${tier.max == null ? '+' : `–${tier.max}`}`
})
const areaColor = computed(() => {
  const g = geom.value
  if (!g) return 'var(--accent)'
  return tierColor(g.latest.value)
})
const gradientId = `rating-area-${Math.random().toString(36).slice(2, 8)}`
const maskId = `rating-mask-${Math.random().toString(36).slice(2, 8)}`
const numberFormat = new Intl.NumberFormat('en-US')
function fmtNumber(value: number | string | null | undefined) {
  if (value == null) return '—'
  const n = Number(value)
  return Number.isFinite(n) ? numberFormat.format(n) : String(value)
}

const labelPos = computed(() => {
  const g = geom.value
  if (!g) return null
  const last = g.latest
  return {
    x: last.cx - 9,
    y: Math.max(12, last.cy - 11),
    anchor: 'end',
    color: tierColor(last.value),
  }
})

/* ===== interactions ===== */
const tipIndex = ref<number | null>(null)
const tipVisible = ref(false)
const tipLeft = ref(0)
const tipTop = ref(0)
const tipEl = ref<HTMLElement | null>(null)
const tipPoint = computed(() =>
  tipIndex.value == null ? null : geom.value?.coords[tipIndex.value] ?? null,
)
const marker = computed(() => {
  const point = tipPoint.value
  if (!point) return null
  return { x: point.cx, y: point.cy, color: tierColor(point.value) }
})

function placeTip() {
  const point = tipPoint.value
  const tip = tipEl.value
  if (!point || !tip) return
  const tipWidth = tip.offsetWidth || 220
  const tipHeight = tip.offsetHeight || 140
  const p = PAD.value
  let left = point.cx + 14
  if (left + tipWidth > width.value - 8) left = point.cx - tipWidth - 14
  left = Math.max(8, Math.min(left, width.value - tipWidth - 8))
  let top = point.cy - tipHeight - 14
  if (top < 8) top = point.cy + 14
  if (top + tipHeight > H.value - 8) top = Math.max(8, H.value - tipHeight - 8)
  tipLeft.value = left
  tipTop.value = top
}

function show(index: number) {
  if (!geom.value) return
  tipIndex.value = index
  tipVisible.value = true
  nextTick(placeTip)
}
function hide() {
  tipVisible.value = false
  tipIndex.value = null
}

function pointFromEvent(event: PointerEvent | MouseEvent) {
  const g = geom.value
  const target = chartPlotEl.value
  if (!g || !target) return
  const box = target.getBoundingClientRect()
  const px = event.clientX - box.left
  const py = event.clientY - box.top
  if (px < 0 || py < 0 || px > box.width || py > box.height) {
    hide()
    return
  }
  let best = -1
  let bestScore = Infinity
  g.coords.forEach((point, index) => {
    const dx = Math.abs(px - point.cx)
    if (dx > 42) return
    const score = dx + Math.abs(py - point.cy) * 0.32
    if (score < bestScore) {
      bestScore = score
      best = index
    }
  })
  if (best >= 0) show(best)
  else hide()
}

function onPointerMove(event: PointerEvent) {
  if (event.pointerType === 'touch') return
  pointFromEvent(event)
}
function onPointerDown(event: PointerEvent) {
  pointFromEvent(event)
}
function onPointerLeave(event: PointerEvent) {
  if (event.pointerType !== 'touch') hide()
}
function onFocus(index: number) {
  show(index)
}
function onKeydown(event: KeyboardEvent, index: number) {
  if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return
  event.preventDefault()
  const total = geom.value?.coords.length || 0
  if (!total) return
  let next = index
  if (event.key === 'Home') next = 0
  else if (event.key === 'End') next = total - 1
  else next = (index + (event.key === 'ArrowRight' ? 1 : -1) + total) % total
  const hits = chartPlotEl.value?.querySelectorAll<SVGCircleElement>('[data-point]')
  hits?.[next]?.focus()
}

function onDocPointerDown(event: PointerEvent) {
  if (!chartPlotEl.value?.contains(event.target as Node)) hide()
}

function pointAria(point: ChartPoint) {
  const meta = point.meta || {}
  const rank = meta.rank != null ? `第 ${meta.rank} 名` : '名次未知'
  const delta =
    meta.delta != null
      ? `变化 ${meta.delta > 0 ? '+' : ''}${meta.delta}`
      : ''
  return `${formatFullDate(point.time)}，${platformLabel(meta.platform) || ''} ${meta.contest || ''}，${metricLabel.value} ${point.value}，${rank}${delta ? `，${delta}` : ''}`
}

function chartSummary() {
  const n = geom.value?.coords.length || 0
  return isAggregate.value
    ? `站内总积分曲线，共 ${n} 场计入排名的比赛。悬停、聚焦或轻触数据点查看比赛详情。`
    : `${platformLabel(props.platform)} 官方 Rating 曲线，共 ${n} 场 rated 比赛。线条颜色随该平台段位变化。悬停、聚焦或轻触查看比赛详情。`
}

function platformName() {
  return props.platform ? platformLabel(props.platform) : ''
}
function formatAxisDate(time: number) {
  const date = new Date(time)
  return `${String(date.getFullYear()).slice(2)}.${String(date.getMonth() + 1).padStart(2, '0')}`
}
function formatFullDate(time: number) {
  const date = new Date(time)
  return `${date.getFullYear()}.${String(date.getMonth() + 1).padStart(2, '0')}.${String(date.getDate()).padStart(2, '0')}`
}
function formatTime(s: string) {
  const date = new Date(s)
  if (Number.isNaN(date.getTime())) return s
  return `${date.getMonth() + 1}月${date.getDate()}日 ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}
function signed(value: number | null | undefined) {
  if (value == null) return '—'
  return `${value > 0 ? '+' : ''}${value}`
}

watch(
  [() => props.points, () => props.platform],
  () => {
    hide()
    animKey.value += 1
  },
  { flush: 'post' },
)
watch(width, () => {
  if (tipVisible.value) nextTick(placeTip)
})

onMounted(() => {
  measure()
  resizeObserver = new ResizeObserver(measure)
  if (plotEl.value) resizeObserver.observe(plotEl.value)
  document.addEventListener('pointerdown', onDocPointerDown)
})
onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  document.removeEventListener('pointerdown', onDocPointerDown)
})
</script>

<template>
  <div ref="plotEl" class="rating-chart">
    <div class="chart-top">
      <div class="chart-legend">
        <span
          class="chart-legend__swatch"
          :style="{ background: isAggregate ? 'var(--accent)' : tierColor(latestValue ?? 0) }"
          aria-hidden="true"
        />
        <span class="chart-legend__label">
          {{ isAggregate ? '站内总积分' : platformName() }}
          <small>{{ isAggregate ? 'SITE TOTAL · 近一年' : `OFFICIAL RATING · 平台口径${tierRangeText ? ` · ${tierRangeText}` : ''}` }}</small>
        </span>
        <span class="chart-legend__value">
          <CountUp :value="latestValue" :precision="latestPrecision" />
        </span>
      </div>
      <span class="chart-mode">
        {{ isAggregate ? '单线 · 后端评分口径' : tierSet ? '线条颜色 = 官方段位' : '平台 Rating · 官方口径' }}
      </span>
    </div>

    <div
      v-if="geom"
      ref="chartPlotEl"
      :key="animKey"
      class="chart-plot"
      @pointermove="onPointerMove"
      @pointerdown="onPointerDown"
      @pointerleave="onPointerLeave"
    >
      <svg
        class="chart-svg"
        :viewBox="`0 0 ${width} ${H}`"
        :width="width"
        :height="H"
        role="group"
        :aria-label="chartSummary()"
      >
        <defs>
          <linearGradient :id="gradientId" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" :stop-color="areaColor" stop-opacity="0.22" />
            <stop offset="100%" :stop-color="areaColor" stop-opacity="0" />
          </linearGradient>
          <linearGradient :id="`${maskId}-alpha`" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0" stop-color="white" stop-opacity="0" />
            <stop offset="0.08" stop-color="white" stop-opacity="1" />
            <stop offset="0.9" stop-color="white" stop-opacity="1" />
            <stop offset="1" stop-color="white" stop-opacity="0" />
          </linearGradient>
          <mask :id="maskId" maskUnits="userSpaceOnUse">
            <rect
              :x="PAD.left"
              :y="PAD.top"
              :width="width - PAD.left - PAD.right"
              :height="H - PAD.top - PAD.bottom + 20"
              :fill="`url(#${maskId}-alpha)`"
            />
          </mask>
        </defs>

        <g aria-hidden="true">
          <line
            v-for="tick in geom.ticks"
            :key="`grid-${tick.value}`"
            class="chart-grid"
            :x1="PAD.left"
            :x2="width - PAD.right"
            :y1="tick.y"
            :y2="tick.y"
          />
          <text
            v-for="tick in geom.ticks"
            :key="`axis-${tick.value}`"
            class="chart-axis"
            :x="PAD.left - 7"
            :y="tick.y + 3"
            text-anchor="end"
          >
            {{ fmtNumber(tick.value) }}
          </text>

          <template v-if="tierSet">
            <g v-for="line in geom.tierLines" :key="`tier-${line.value}`">
              <line
                class="chart-tier-line"
                :x1="PAD.left"
                :x2="width - PAD.right"
                :y1="line.y"
                :y2="line.y"
                :stroke="line.color"
              />
              <text
                class="chart-tier-label"
                :x="width - PAD.right + 5"
                :y="line.y + 3"
                :fill="line.color"
              >
                {{ fmtNumber(line.value) }}
              </text>
            </g>
          </template>

          <text
            v-for="(label, index) in geom.xLabels"
            :key="`x-${index}`"
            class="chart-axis"
            :x="label.x"
            :y="H - 9"
            :text-anchor="label.anchor"
          >
            {{ label.text }}
          </text>
        </g>

        <path
          v-if="areaPath"
          class="chart-area"
          :d="areaPath"
          :fill="`url(#${gradientId})`"
          :mask="`url(#${maskId})`"
          aria-hidden="true"
        />

        <g v-if="segments.length" aria-hidden="true">
          <path
            v-for="(segment, index) in segments"
            :key="`segment-${index}`"
            class="chart-series-segment"
            :d="segment.d"
            pathLength="1"
            :stroke="segment.color"
            :style="{ animationDelay: `${segment.delay}ms` }"
          />
        </g>
        <path
          v-else-if="geom.coords.length === 1"
          class="chart-single-dot-halo"
          :cx="geom.coords[0].cx"
          :cy="geom.coords[0].cy"
          r="10"
          :stroke="tierColor(geom.coords[0].value)"
          aria-hidden="true"
        />

        <g aria-hidden="true">
          <circle
            v-for="point in geom.coords"
            :key="`dot-${point.index}`"
            class="chart-dot"
            :cx="point.cx"
            :cy="point.cy"
            r="3.1"
            :stroke="tierColor(point.value)"
          />
        </g>

        <g v-if="tipPoint" aria-hidden="true">
          <line
            class="chart-crosshair"
            :x1="tipPoint.cx"
            :x2="tipPoint.cx"
            :y1="PAD.top"
            :y2="geom.baseline"
          />
          <circle
            class="chart-marker"
            :cx="tipPoint.cx"
            :cy="tipPoint.cy"
            r="6"
            :stroke="tierColor(tipPoint.value)"
          />
        </g>

        <g v-if="labelPos" aria-hidden="true">
          <text
            class="chart-last-label"
            :x="labelPos.x"
            :y="labelPos.y"
            :text-anchor="labelPos.anchor"
            :fill="labelPos.color"
          >
            {{ fmtNumber(latestValue) }}
          </text>
        </g>

        <circle
          v-for="point in geom.coords"
          :key="`hit-${point.index}`"
          class="chart-hit"
          data-point
          :cx="point.cx"
          :cy="point.cy"
          r="12"
          tabindex="0"
          role="img"
          :aria-label="pointAria(point)"
          @focus="onFocus(point.index)"
          @blur="hide"
          @keydown="onKeydown($event, point.index)"
        />
      </svg>

      <div
        v-show="tipVisible && tipPoint"
        ref="tipEl"
        class="chart-tooltip"
        :class="{ 'is-visible': tipVisible && tipPoint }"
        :style="{ left: `${tipLeft}px`, top: `${tipTop}px` }"
        aria-hidden="true"
      >
        <template v-if="tipPoint">
          <p class="chart-tooltip__eyebrow">
            {{ formatFullDate(tipPoint.time) }}
            <span>·</span>
            <span
              v-if="tipPoint.meta?.platform"
              class="platform-tag"
              :class="platformClass(tipPoint.meta.platform)"
            >{{ platformLabel(tipPoint.meta.platform) }}</span>
          </p>
          <strong class="chart-tooltip__title">{{ tipPoint.meta?.contest || '—' }}</strong>
          <div class="chart-tooltip__grid">
            <span><small>名次</small><b>{{ tipPoint.meta?.rank != null ? `#${tipPoint.meta.rank}` : '—' }}</b></span>
            <span><small>{{ metricLabel }}</small><b>{{ fmtNumber(tipPoint.value) }}</b></span>
            <span>
              <small>变化</small>
              <b :class="(tipPoint.meta?.delta ?? 0) >= 0 ? 'delta-up' : 'delta-down'">{{ signed(tipPoint.meta?.delta) }}</b>
            </span>
          </div>
          <span class="chart-tooltip__foot">
            {{ isAggregate ? '站内总积分 · 与榜单同口径' : '官方 Rating · 平台口径' }}
            <template v-if="tipPoint.meta?.platform"> · {{ platformLabel(tipPoint.meta.platform) }}</template>
          </span>
        </template>
      </div>
    </div>

    <div v-else class="chart-empty">还没有可展示的评分记录。</div>
    <p v-if="geom" class="chart-time">最近一场 · {{ formatTime(geom.latest.label) }} · 悬停 / 轻触查看比赛</p>
  </div>
</template>

<style scoped>
.rating-chart {
  width: 100%;
  min-width: 0;
}
.chart-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--space-2) var(--space-3);
  padding: 2px 2px 4px;
}
.chart-legend {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.chart-legend__swatch {
  position: relative;
  width: 24px;
  height: 2px;
  background: var(--accent);
  flex-shrink: 0;
}
.chart-legend__swatch::after {
  content: '';
  position: absolute;
  right: -2px;
  top: -2px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: inherit;
}
.chart-legend__label {
  display: grid;
  gap: 1px;
  font-size: 12px;
  line-height: 1.3;
  color: var(--ink-2);
  white-space: nowrap;
}
.chart-legend__label small {
  font-family: var(--font-mono);
  font-size: 8px;
  letter-spacing: 0.06em;
  color: var(--ink-3);
}
.chart-legend__value {
  font-family: var(--font-mono);
  font-size: 20px;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.03em;
  color: var(--ink);
}
.chart-mode {
  padding: 4px 7px;
  border: 1px solid var(--rule);
  font-family: var(--font-mono);
  font-size: 8.5px;
  letter-spacing: 0.08em;
  color: var(--ink-3);
  white-space: nowrap;
}
.chart-plot {
  position: relative;
  margin-top: 6px;
  touch-action: pan-y;
}
.chart-svg {
  display: block;
  width: 100%;
  height: auto;
  overflow: visible;
}
.chart-grid {
  stroke: var(--rule);
  stroke-width: 1;
  stroke-dasharray: 1 5;
  opacity: 0.85;
  vector-effect: non-scaling-stroke;
}
.chart-tier-line {
  stroke-width: 1;
  stroke-dasharray: 4 5;
  opacity: 0.5;
  vector-effect: non-scaling-stroke;
}
.chart-axis,
.chart-tier-label {
  fill: var(--ink-3);
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.02em;
}
.chart-tier-label {
  font-size: 8.5px;
  font-weight: 500;
}
.chart-series-segment {
  fill: none;
  stroke-width: 2.2;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-dasharray: 1;
  stroke-dashoffset: 1;
  vector-effect: non-scaling-stroke;
  animation: chart-draw 0.7s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}
.chart-area {
  opacity: 0;
  animation: chart-area-in 0.7s cubic-bezier(0.16, 1, 0.3, 1) 0.22s forwards;
}
.chart-dot {
  fill: var(--paper-2);
  stroke-width: 2;
  vector-effect: non-scaling-stroke;
  opacity: 0;
  transform-box: fill-box;
  transform-origin: center;
  animation: chart-dot-in 0.4s cubic-bezier(0.16, 1, 0.3, 1) 0.44s forwards;
}
.chart-single-dot-halo {
  fill: none;
  stroke-width: 1.4;
  opacity: 0.35;
}
.chart-crosshair {
  stroke: var(--rule-strong);
  stroke-width: 1;
  stroke-dasharray: 2 3;
  vector-effect: non-scaling-stroke;
}
.chart-marker {
  fill: var(--paper-2);
  stroke-width: 2.4;
  vector-effect: non-scaling-stroke;
}
.chart-last-label {
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 500;
  paint-order: stroke;
  stroke: var(--paper-2);
  stroke-width: 3px;
  stroke-linejoin: round;
}
.chart-hit {
  fill: transparent;
  stroke: transparent;
  cursor: crosshair;
}
.chart-hit:focus-visible {
  outline: none;
  fill: color-mix(in srgb, var(--accent) 8%, transparent);
  stroke: var(--accent);
  stroke-width: 1.4;
}
.chart-tooltip {
  position: absolute;
  z-index: 4;
  width: max-content;
  max-width: 236px;
  padding: 10px 12px;
  border: 1px solid var(--glass-border-top);
  border-radius: 12px;
  background: var(--tip-bg);
  box-shadow:
    0 20px 42px -26px rgba(30, 20, 10, 0.5),
    inset 0 1px 0 rgba(255, 255, 255, 0.6);
  -webkit-backdrop-filter: blur(18px) saturate(1.45);
  backdrop-filter: blur(18px) saturate(1.45);
  opacity: 0;
  visibility: hidden;
  transform: translateY(4px);
  transition:
    opacity 0.16s var(--ease-standard),
    transform 0.16s var(--ease-standard),
    visibility 0.16s;
  pointer-events: none;
}
.chart-tooltip.is-visible {
  opacity: 1;
  visibility: visible;
  transform: translateY(0);
}
.chart-tooltip__eyebrow {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
  font-family: var(--font-mono);
  font-size: 8.5px;
  letter-spacing: 0.04em;
  color: var(--ink-3);
}
.chart-tooltip__eyebrow .platform-tag {
  font-size: 8px;
  padding: 1px 5px;
}
.chart-tooltip__title {
  display: block;
  margin-top: 4px;
  font-family: var(--font-display);
  font-size: 15px;
  font-weight: 600;
  line-height: 1.3;
  color: var(--ink);
}
.chart-tooltip__grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid var(--rule);
}
.chart-tooltip__grid span {
  display: grid;
  gap: 2px;
}
.chart-tooltip__grid small {
  font-family: var(--font-mono);
  font-size: 7.5px;
  color: var(--ink-3);
}
.chart-tooltip__grid b {
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 500;
  color: var(--ink);
}
.chart-tooltip__foot {
  display: block;
  margin-top: 7px;
  font-family: var(--font-mono);
  font-size: 7.5px;
  color: var(--ink-3);
}
.delta-up {
  color: var(--color-success);
}
.delta-down {
  color: var(--color-danger);
}
.chart-time {
  margin: 4px 2px 0;
  font-family: var(--font-mono);
  font-size: 8.5px;
  color: var(--ink-3);
  letter-spacing: 0.03em;
}
.chart-empty {
  padding: 42px 20px;
  text-align: center;
  font-size: 13px;
  color: var(--ink-3);
}
@keyframes chart-draw {
  to {
    stroke-dashoffset: 0;
  }
}
@keyframes chart-area-in {
  to {
    opacity: 1;
  }
}
@keyframes chart-dot-in {
  from {
    opacity: 0;
    transform: scale(0.55);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}
@media (max-width: 559px) {
  .chart-mode {
    display: none;
  }
  .chart-tooltip {
    max-width: 210px;
    padding: 9px 10px;
  }
  .chart-tooltip__title {
    font-size: 13px;
  }
}
@media (prefers-reduced-motion: reduce) {
  .chart-series-segment,
  .chart-area,
  .chart-dot {
    animation: none;
    stroke-dashoffset: 0;
    opacity: 1;
  }
  .chart-tooltip {
    transition: none;
  }
}
</style>
