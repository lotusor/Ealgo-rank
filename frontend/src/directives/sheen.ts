import type { Directive } from 'vue'

type SheenEl = HTMLElement & { __sheenCleanup?: () => void }

function attach(el: SheenEl) {
  let frame = 0
  const move = (event: PointerEvent) => {
    const rect = el.getBoundingClientRect()
    const x = event.clientX - rect.left
    const y = event.clientY - rect.top
    cancelAnimationFrame(frame)
    frame = requestAnimationFrame(() => {
      el.style.setProperty('--sheen-x', `${x}px`)
      el.style.setProperty('--sheen-y', `${y}px`)
    })
  }
  const leave = () => {
    cancelAnimationFrame(frame)
    el.style.setProperty('--sheen-x', '30%')
    el.style.setProperty('--sheen-y', '0%')
  }
  el.addEventListener('pointermove', move)
  el.addEventListener('pointerleave', leave)
  el.__sheenCleanup = () => {
    cancelAnimationFrame(frame)
    el.removeEventListener('pointermove', move)
    el.removeEventListener('pointerleave', leave)
  }
}

export const vSheen: Directive<SheenEl> = {
  mounted(el) {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    attach(el)
  },
  unmounted(el) {
    el.__sheenCleanup?.()
  },
}
