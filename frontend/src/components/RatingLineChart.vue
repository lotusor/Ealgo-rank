<script setup lang="ts">
import { computed } from 'vue'

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
const PAD = { top: 18, right: 16, bottom: 28, left: 44 }

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
  // Y 轴刻度（4 格）
  const ticks = Array.from({ length: 5 }, (_, i) => {
    const v = min + ((max - min) * i) / 4
    return { v: Math.round(v), y: y(v) }
  })
  return { coords, line, area, ticks, min, max }
})

const gradId = `rg-${Math.random().toString(36).slice(2, 8)}`
</script>

<template>
  <div class="chart-wrap">
    <svg
      v-if="geom"
      :viewBox="`0 0 ${W} ${H}`"
      width="100%"
      :height="H"
      preserveAspectRatio="xMidYMid meet"
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

      <!-- 数据点 + hover 提示 -->
      <g v-for="(c, i) in geom.coords" :key="i">
        <circle :cx="c.cx" :cy="c.cy" r="3.5" :fill="color" />
        <title>
          {{ c.label }}\n{{ c.meta?.contest || '' }}\nrating {{ c.value
          }}<template v-if="c.meta?.delta != null">
            ({{ c.meta.delta > 0 ? '+' : '' }}{{ c.meta.delta }})</template>
        </title>
      </g>
    </svg>
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
.empty {
  padding: 40px;
  text-align: center;
  color: var(--color-text-tertiary);
  font-size: 13px;
}
</style>
