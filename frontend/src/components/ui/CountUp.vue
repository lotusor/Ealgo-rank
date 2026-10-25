<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    value: number | null | undefined
    precision?: number
    duration?: number
    prefix?: string
    suffix?: string
    grouping?: boolean
  }>(),
  { precision: 0, duration: 860, prefix: '', suffix: '', grouping: true },
)

const visual = ref('—')
const formatter = computed(
  () =>
    new Intl.NumberFormat('en-US', {
      useGrouping: props.grouping,
      minimumFractionDigits: props.precision,
      maximumFractionDigits: props.precision,
    }),
)
const finalText = computed(() => {
  if (props.value == null || !Number.isFinite(Number(props.value))) return '—'
  return `${props.prefix}${formatter.value.format(Number(props.value))}${props.suffix}`
})

let frame = 0
let current = 0

function reduceMotion() {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

function paint(value: number) {
  visual.value = `${props.prefix}${formatter.value.format(value)}${props.suffix}`
}

function animateTo(target: number, first: boolean) {
  cancelAnimationFrame(frame)
  if (reduceMotion() || document.hidden) {
    current = target
    paint(target)
    return
  }
  const from = first ? 0 : current
  current = target
  if (from === target) {
    paint(target)
    return
  }
  const started = performance.now()
  const duration = Math.min(1600, Math.max(200, props.duration))
  const tick = (now: number) => {
    const t = Math.min(1, (now - started) / duration)
    const eased = 1 - Math.pow(1 - t, 3)
    paint(from + (target - from) * eased)
    if (t < 1) frame = requestAnimationFrame(tick)
    else paint(target)
  }
  frame = requestAnimationFrame(tick)
}

function sync() {
  if (props.value == null || !Number.isFinite(Number(props.value))) {
    cancelAnimationFrame(frame)
    visual.value = '—'
    return
  }
  animateTo(Number(props.value), false)
}

onMounted(() => {
  if (props.value == null || !Number.isFinite(Number(props.value))) {
    visual.value = '—'
    return
  }
  animateTo(Number(props.value), true)
})
watch(() => props.value, sync)
onBeforeUnmount(() => cancelAnimationFrame(frame))
</script>

<template>
  <span class="count-up num">
    <span aria-hidden="true">{{ visual }}</span>
    <span class="sr-only">{{ finalText }}</span>
  </span>
</template>

<style scoped>
.count-up {
  display: inline-block;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
</style>
