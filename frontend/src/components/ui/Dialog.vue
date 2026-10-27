<script setup lang="ts">
/**
 * 模态对话框基元。
 *
 * 此前站内 7 处弹窗各写一份 `.modal-overlay` + `v-esc`，焦点管理普遍缺失
 * （Tab 可以走出弹窗、关闭后焦点掉回 body）。这里统一：
 *  - Teleport 到 body：内容区转场会创建层叠上下文，固定遮罩留在页面内会被压住；
 *  - 打开聚焦首个控件、Tab 在面板内回环、关闭把焦点还给触发元素；
 *  - `busy`（提交中）期间屏蔽遮罩点击与 Esc，并把焦点留在面板内，
 *    避免迟到响应关掉用户随后打开的另一个编辑器。
 */
import { computed, nextTick, onBeforeUnmount, onMounted, ref, useId, watch } from 'vue'
import { popOverlay, pushOverlay, type Overlay } from '@/composables/overlayStack'
import { getFocusable, nextFocusable } from '@/composables/focusTrap'

const props = withDefaults(
  defineProps<{
    open: boolean
    title: string
    /** CSS 宽度，沿用原内联弹窗的写法 */
    width?: string
    maxWidth?: string
    /** 提交中：屏蔽一切关闭途径 */
    busy?: boolean
    closeOnOverlay?: boolean
    /** 面板内说明元素的 id（错误提示等） */
    describedBy?: string
  }>(),
  { width: '480px', maxWidth: '', busy: false, closeOnOverlay: true, describedBy: undefined },
)

const emit = defineEmits<{ 'update:open': [value: boolean] }>()

const panelEl = ref<HTMLElement | null>(null)
const headingId = useId()
let trigger: HTMLElement | null = null
let layered = false

const panelStyle = computed(() => ({
  width: props.width,
  ...(props.maxWidth ? { maxWidth: props.maxWidth } : {}),
}))

const overlay: Overlay = {
  requestClose: () => {
    if (props.busy) {
      panelEl.value?.focus()
      return
    }
    emit('update:open', false)
  },
}

function activate() {
  if (layered) return
  layered = true
  // 触发元素必须在打开这一刻取：关闭后 DOM 可能已经换了一批按钮
  trigger = document.activeElement instanceof HTMLElement ? document.activeElement : null
  pushOverlay(overlay)
  nextTick(() => {
    const first = getFocusable(panelEl.value)[0]
    ;(first ?? panelEl.value)?.focus()
  })
}

function deactivate() {
  if (!layered) return
  layered = false
  popOverlay(overlay)
  const returned = trigger
  trigger = null
  nextTick(() => {
    if (returned?.isConnected) returned.focus()
  })
}

function onPanelKeydown(event: KeyboardEvent) {
  if (event.key !== 'Tab') return
  event.preventDefault()
  const list = getFocusable(panelEl.value)
  if (!list.length) {
    panelEl.value?.focus()
    return
  }
  const next = nextFocusable(list, document.activeElement as HTMLElement | null, event.shiftKey)
  next?.focus()
}

watch(
  () => props.open,
  (open) => (open ? activate() : deactivate()),
)

onMounted(() => {
  if (props.open) activate()
})
onBeforeUnmount(deactivate)
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="modal-overlay"
      @click.self="props.closeOnOverlay && overlay.requestClose()"
    >
      <div
        ref="panelEl"
        class="modal"
        role="dialog"
        aria-modal="true"
        tabindex="-1"
        :style="panelStyle"
        :aria-labelledby="`${headingId}-title`"
        :aria-describedby="describedBy"
        :aria-busy="busy || undefined"
        @keydown="onPanelKeydown"
      >
        <div class="modal-header" :id="`${headingId}-title`">{{ title }}</div>
        <div class="modal-body"><slot /></div>
        <div v-if="$slots.footer" class="modal-footer">
          <slot name="footer" :close="overlay.requestClose" />
        </div>
      </div>
    </div>
  </Teleport>
</template>
