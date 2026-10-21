<script setup lang="ts">
import { computed } from 'vue'
import { medalTier } from '@/utils/format'

const props = defineProps<{ rank: number | null | undefined }>()

const tier = computed(() => medalTier(props.rank))
const text = computed(() =>
  props.rank === null || props.rank === undefined ? '—' : String(props.rank),
)
</script>

<template>
  <span class="rank-badge" :class="tier">{{ text }}</span>
</template>
