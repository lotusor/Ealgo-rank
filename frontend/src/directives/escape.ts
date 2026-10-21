/**
 * v-esc —— Esc 关闭浮层。
 *
 * 用法：`<div class="modal-overlay" v-esc="() => (open = false)">`
 *
 * 为什么用指令而不是在每个组件里写 `document.addEventListener`：
 * ① 遮罩元素本身不可聚焦，把 keydown 挂在它身上需要先给它 tabindex，
 *    等于给键盘用户多一个无意义的 Tab 停靠点；
 * ② 弹窗是 `v-if` 渲染的，元素挂载 == 弹窗打开，卸载 == 关闭，
 *    指令的 mounted / unmounted 天然就是「注册 / 注销监听」的时机。
 *
 * 多层叠放（改绑弹窗里再套解绑确认）：只有**栈顶**（最后挂载的那一层）响应 Esc，
 * 一次 Esc 只关一层，符合用户对「逐层退出」的预期。
 */
import type { Directive } from 'vue'

const stack: HTMLElement[] = []

function onKeydown(event: KeyboardEvent) {
  if (event.key !== 'Escape') return
  if (!stack.length) return
  const top = stack[stack.length - 1]
  const handler = handlers.get(top)
  if (handler) handler()
}

const handlers = new WeakMap<HTMLElement, () => void>()

export const vEsc: Directive<HTMLElement, () => void> = {
  mounted(el, binding) {
    handlers.set(el, binding.value)
    stack.push(el)
    if (stack.length === 1) {
      document.addEventListener('keydown', onKeydown)
    }
  },
  updated(el, binding) {
    // 关闭回调可能捕获了旧的响应式状态，每次更新都换掉
    handlers.set(el, binding.value)
  },
  unmounted(el) {
    handlers.delete(el)
    const idx = stack.lastIndexOf(el)
    if (idx !== -1) stack.splice(idx, 1)
    if (!stack.length) {
      document.removeEventListener('keydown', onKeydown)
    }
  },
}
