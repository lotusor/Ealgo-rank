<script setup lang="ts">
import { computed } from 'vue'
import { initial } from '@/utils/format'

const props = withDefaults(
  defineProps<{ name: string | null | undefined; size?: number }>(),
  { size: 32 },
)

const char = computed(() => initial(props.name))
const style = computed(() => ({
  width: `${props.size}px`,
  height: `${props.size}px`,
  fontSize: `${Math.round(props.size * 0.41)}px`,
}))
</script>

<template>
  <span class="avatar" :style="style">{{ char }}</span>
</template>
