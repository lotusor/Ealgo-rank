<script setup lang="ts">
withDefaults(
  defineProps<{ title?: string; hint?: string }>(),
  { title: '暂无数据', hint: '' },
)
</script>

<template>
  <div class="empty-state">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
      <path d="M3 7v10a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V7" />
      <path d="M3 7l2-3h14l2 3M3 7h18" />
      <path d="M9 12h6" />
    </svg>
    <div class="body-sm" style="font-weight: 600; color: var(--color-text-secondary)">
      {{ title }}
    </div>
    <div v-if="hint" class="caption" style="margin-top: 4px">{{ hint }}</div>
  </div>
</template>
