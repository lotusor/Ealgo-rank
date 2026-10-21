<script setup lang="ts">
import { computed } from 'vue'
import { initial } from '@/utils/format'

const props = withDefaults(
  defineProps<{
    name: string | null | undefined
    size?: number
    /** 头像图片完整 URL，无则回退到首字母头像 */
    avatar?: string | null
  }>(),
  { size: 32, avatar: null },
)

const char = computed(() => initial(props.name))
const style = computed(() => ({
  width: `${props.size}px`,
  height: `${props.size}px`,
  fontSize: `${Math.round(props.size * 0.41)}px`,
}))
</script>

<template>
  <img v-if="avatar" class="avatar avatar-img" :style="style" :src="avatar" alt="" />
  <span v-else class="avatar" :style="style">{{ char }}</span>
</template>
