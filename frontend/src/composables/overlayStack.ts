/**
 * 浮层栈：保证「一次 Esc 只关最上层」。
 *
 * 站内存在叠放场景（成员名单的平台账号弹窗之上再开改绑/解绑确认），
 * 若每个浮层各自 document.addEventListener，一次 Esc 会把所有层一起关掉。
 */
export interface Overlay {
  requestClose: () => void
}

const stack: Overlay[] = []
let listening = false

function onKeydown(event: KeyboardEvent) {
  if (event.key !== 'Escape' || !stack.length) return
  stack[stack.length - 1].requestClose()
}

export function pushOverlay(overlay: Overlay) {
  stack.push(overlay)
  if (!listening) {
    document.addEventListener('keydown', onKeydown)
    listening = true
  }
}

export function popOverlay(overlay: Overlay) {
  const index = stack.lastIndexOf(overlay)
  if (index !== -1) stack.splice(index, 1)
  if (!stack.length && listening) {
    document.removeEventListener('keydown', onKeydown)
    listening = false
  }
}

export function overlayDepth() {
  return stack.length
}
