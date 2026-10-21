<script setup lang="ts" generic="T extends string | number">
/** 原型 .segmented / .seg-btn 的受控版本。 */
defineProps<{
  modelValue: T
  options: { label: string; value: T }[]
}>()
defineEmits<{ 'update:modelValue': [value: T] }>()
</script>

<template>
  <div class="segmented" role="tablist">
    <button
      v-for="opt in options"
      :key="String(opt.value)"
      type="button"
      role="tab"
      class="seg-btn"
      :class="{ active: opt.value === modelValue }"
      :aria-selected="opt.value === modelValue"
      @click="$emit('update:modelValue', opt.value)"
    >
      {{ opt.label }}
    </button>
  </div>
</template>
