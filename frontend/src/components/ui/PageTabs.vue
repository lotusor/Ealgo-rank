<script setup lang="ts" generic="T extends string | number">
/** 原型 .tabs / .tab / .tab-count 的受控版本。count 为 null 时不渲染计数气泡。 */
defineProps<{
  modelValue: T
  options: { label: string; value: T; count?: number | null }[]
}>()
defineEmits<{ 'update:modelValue': [value: T] }>()
</script>

<template>
  <div class="tabs" role="tablist">
    <button
      v-for="opt in options"
      :key="String(opt.value)"
      type="button"
      role="tab"
      class="tab"
      :class="{ active: opt.value === modelValue }"
      :aria-selected="opt.value === modelValue"
      @click="$emit('update:modelValue', opt.value)"
    >
      {{ opt.label }}
      <span v-if="opt.count !== null && opt.count !== undefined" class="tab-count">
        {{ opt.count }}
      </span>
    </button>
  </div>
</template>
