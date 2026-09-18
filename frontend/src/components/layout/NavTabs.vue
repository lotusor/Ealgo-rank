<script setup lang="ts">
/**
 * 顶部选项卡条：只渲染用户固定（且当前身份可见）的功能项。
 *
 * 复用 components.css 既有的 `.nav-links` / `.nav-links a` 样式，
 * 因此 ≤768px 时会被既有响应式规则自动隐藏、改由汉堡抽屉承载。
 */
import type { NavItem } from '@/config/navRegistry'

defineProps<{
  items: NavItem[]
  activeKey: string
}>()

defineEmits<{ navigate: [key: string] }>()
</script>

<template>
  <nav class="nav-links nav-tabs" aria-label="主导航">
    <a
      v-for="item in items"
      :key="item.key"
      :class="{ active: item.key === activeKey }"
      :aria-current="item.key === activeKey ? 'page' : undefined"
      @click="$emit('navigate', item.key)"
      >{{ item.label }}</a
    >
  </nav>
</template>

<style scoped>
/* 选项卡数量多时可横向滚动，不挤压右侧操作区 */
.nav-tabs {
  flex: 0 1 auto;
  min-width: 0;
  overflow-x: auto;
  scrollbar-width: none;
  -ms-overflow-style: none;
}
.nav-tabs::-webkit-scrollbar {
  display: none;
}
.nav-tabs a {
  white-space: nowrap;
  flex-shrink: 0;
}
</style>
