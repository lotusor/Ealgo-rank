<script setup lang="ts">
import { computed, ref } from 'vue'

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
  }>(),
  { height: 220, color: 'var(--brand)' },
)

const W = 720
const H = computed(() => props.height)
const PAD = { top: 18, right: 16, bottom: 40, left: 44 }

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
  const innerW = W - PAD.left - PAD.right
  const innerH = H.value - PAD.top - PAD.bottom
  const x = (i: number) =>
    PAD.left + (pts.length === 1 ? innerW / 2 : (i / (pts.length - 1)) * innerW)
  const y = (v: number) => PAD.top + innerH - ((v - min) / (max - min)) * innerH
  const coords = pts.map((p, i) => ({ ...p, cx: x(i), cy: y(p.value) }))
  const line = coords.map((c) => `${c.cx},${c.cy}`).join(' ')
  const area = `${PAD.left},${PAD.top + innerH} ${line} ${
    coords[coords.length - 1].cx
  },${PAD.top + innerH}`
  const ticks = Array.from({ length: 5 }, (_, i) => {
    const v = min + ((max - min) * i) / 4
    return { v: Math.round(v), y: y(v) }
  })
  const xTicks = pickXTicks(coords)
  return { coords, line, area, ticks, xTicks, min, max }
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

// tooltip 定位：以 SVG 相对位置百分比定位；靠近右侧时翻转避免溢出
const tipStyle = computed(() => {
  const p = hoverPoint.value
  if (!p) return {}
  const ratio = p.cx / W
  if (ratio > 0.62) {
    return { left: 'auto', right: `${(1 - ratio) * 100}%`, transform: 'translate(50%, -100%)' }
  }
  return { left: `${ratio * 100}%`, right: 'auto', transform: 'translate(-50%, -100%)' }
})

function fmtDateLabel(s: string) {
  const d = new Date(s)
  if (isNaN(d.getTime())) return s
  return d.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
}
function fmtDateTime(s: string) {
  const d = new Date(s)
  if (isNaN(d.getTime())) return s
  return d.toLocaleString('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  })
}
function platformCls(p: string) {
  return p === 'codeforces' ? 'cf' : p === 'atcoder' ? 'atcoder' : p === 'nowcoder' ? 'nowcoder' : ''
}
function platformLabel(p: string) {
  return p === 'codeforces' ? 'Codeforces' : p === 'atcoder' ? 'AtCoder' : p === 'nowcoder' ? 'NowCoder' : p
}

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
            <stop offset="0%" :stop-color="color" stop-opacity="0.28" />
            <stop offset="100%" :stop-color="color" stop-opacity="0.02" />
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
            :stroke="'var(--color-divider)'"
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
        <polygon :points="geom.area" :fill="`url(#${gradId})`" />
        <polyline
          :points="geom.line"
          fill="none"
          :stroke="color"
          stroke-width="2.5"
          stroke-linejoin="round"
          stroke-linecap="round"
        />

        <!-- hover 垂直参考线 -->
        <line
          v-if="hoverPoint"
          :x1="hoverPoint.cx"
          :x2="hoverPoint.cx"
          :y1="PAD.top"
          :y2="PAD.top + H - PAD.top - PAD.bottom"
          stroke="var(--color-text-tertiary)"
          stroke-width="1"
          stroke-dasharray="2 3"
        />

        <!-- 数据点 -->
        <g v-for="(c, i) in geom.coords" :key="i">
          <circle
            :cx="c.cx"
            :cy="c.cy"
            :r="hoverIndex === i ? 5.5 : 3.5"
            :fill="color"
            :stroke="hoverIndex === i ? '#fff' : 'none'"
            :stroke-width="hoverIndex === i ? 1.5 : 0"
          />
        </g>
      </svg>

      <!-- 悬浮提示卡片 -->
      <Transition name="tip">
        <div v-if="hoverPoint" class="chart-tip" :style="tipStyle">
          <div class="tip-time">{{ fmtDateTime(hoverPoint.label) }}</div>
          <div class="tip-rating">
            rating <b class="num">{{ hoverPoint.value }}</b>
          </div>
          <div v-if="hoverPoint.meta?.contest" class="tip-contest">
            <span v-if="hoverPoint.meta?.platform" class="platform-tag" :class="platformCls(hoverPoint.meta.platform)">{{ platformLabel(hoverPoint.meta.platform) }}</span>
            {{ hoverPoint.meta.contest }}
          </div>
          <div
            v-if="hoverPoint.meta?.delta != null"
            class="tip-delta"
            :class="hoverPoint.meta.delta >= 0 ? 'up' : 'down'"
          >
            {{ hoverPoint.meta.delta >= 0 ? '▲' : '▼' }}
            {{ hoverPoint.meta.delta > 0 ? '+' : '' }}{{ hoverPoint.meta.delta }}
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
.chart-tip {
  position: absolute;
  top: 0;
  margin-top: -10px;
  min-width: 140px;
  max-width: 240px;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-lg);
  pointer-events: none;
  z-index: 10;
  font-size: 12px;
}
.tip-time {
  color: var(--color-text-tertiary);
  margin-bottom: 4px;
}
.tip-rating {
  color: var(--color-text-primary);
  font-size: 13px;
}
.tip-rating b {
  color: var(--color-primary);
  font-size: 16px;
}
.tip-contest {
  color: var(--color-text-secondary);
  margin-top: 4px;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.tip-delta {
  margin-top: 4px;
  font-weight: 600;
}
.up { color: var(--color-success); }
.down { color: var(--color-danger); }
.tip-enter-active,
.tip-leave-active {
  transition: opacity 0.12s ease;
}
.tip-enter-from,
.tip-leave-to {
  opacity: 0;
}
</style>
