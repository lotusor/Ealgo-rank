<script setup lang="ts">
import { computed } from 'vue'
import { orgColor, orgShort } from '@/utils/format'

const props = withDefaults(
  defineProps<{
    name: string | null | undefined
    shortName?: string | null
    /** sm 用于学生榜里的次级学校标（原型 24px），md 用于学校榜主标（原型 30px） */
    size?: 'sm' | 'md'
  }>(),
  { shortName: null, size: 'md' },
)

const color = computed(() => orgColor(props.name))
const short = computed(() => orgShort(props.shortName, props.name))
const style = computed(() =>
  props.size === 'sm'
    ? { background: color.value, width: '24px', height: '24px', fontSize: '10px' }
    : { background: color.value },
)
</script>

<template>
  <span class="org-logo" :style="style" :title="name || ''">{{ short }}</span>
</template>
