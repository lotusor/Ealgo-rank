<script setup lang="ts">
/**
 * 通用浮层容器（受控组件）。
 *
 * 项目此前没有 popover 组件，各页面各自内联 `.modal-overlay` / 手写
 * `document.addEventListener('mousedown')` 做外点关闭（重复多处）。
 * 这里抽出统一实现：外点关闭 + Esc 关闭 + 定位 + 层级令牌。
 *
 * 用法：
 *   <Popover v-model:open="open" align="end">
 *     <template #trigger="{ toggle, open }">
 *       <button @click="toggle" :aria-expanded="open">触发</button>
 *     </template>
 *     <template #panel>…</template>
 *   </Popover>
 */
import { onMounted, onUnmounted, ref } from 'vue'

const props = withDefaults(
  defineProps<{
    open: boolean
    /** 面板对齐方向：start = 左对齐触发元素，end = 右对齐 */
    align?: 'start' | 'end'
    /** 面板宽度（CSS 长度），默认 260px */
    panelWidth?: string
  }>(),
  { align: 'start', panelWidth: '260px' },
)

const emit = defineEmits<{ 'update:open': [value: boolean] }>()

const rootRef = ref<HTMLElement | null>(null)

function close() {
  if (props.open) emit('update:open', false)
}
function toggle() {
  emit('update:open', !props.open)
}

function onDocMouseDown(e: MouseEvent) {
  if (!props.open) return
  if (rootRef.value && !rootRef.value.contains(e.target as Node)) close()
}
function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') close()
}

onMounted(() => {
  document.addEventListener('mousedown', onDocMouseDown)
  document.addEventListener('keydown', onKeydown)
})
onUnmounted(() => {
  document.removeEventListener('mousedown', onDocMouseDown)
  document.removeEventListener('keydown', onKeydown)
})
</script>

<template>
  <div ref="rootRef" class="popover">
    <slot name="trigger" :open="open" :toggle="toggle" :close="close" />
    <transition name="popover-fade">
      <div
        v-if="open"
        class="popover-panel"
        :class="align === 'end' ? 'is-end' : 'is-start'"
        :style="{ width: panelWidth }"
      >
        <slot name="panel" :close="close" />
      </div>
    </transition>
  </div>
</template>

<style scoped>
.popover {
  position: relative;
}
.popover-panel {
  position: absolute;
  top: calc(100% + 8px);
  max-height: min(70vh, 560px);
  overflow-y: auto;
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  z-index: var(--z-dropdown);
}
.popover-panel.is-start {
  left: 0;
}
.popover-panel.is-end {
  right: 0;
}
.popover-fade-enter-active,
.popover-fade-leave-active {
  transition:
    opacity var(--duration-fast) var(--ease-standard),
    transform var(--duration-fast) var(--ease-standard);
}
.popover-fade-enter-from,
.popover-fade-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}
</style>
