/**
 * 极简 toast，替换 Naive UI 的 useMessage。
 * 直接挂到 document.body，复用 components.css 里的 .toast 动画类。
 */
type ToastType = 'success' | 'error' | 'info'

let host: HTMLDivElement | null = null

function ensureHost(): HTMLDivElement {
  if (host && document.body.contains(host)) return host
  host = document.createElement('div')
  host.className = 'toast-host'
  host.style.position = 'fixed'
  host.style.left = '0'
  host.style.right = '0'
  host.style.bottom = '0'
  host.style.display = 'flex'
  host.style.flexDirection = 'column'
  host.style.alignItems = 'center'
  host.style.gap = 'var(--space-2, 8px)'
  host.style.pointerEvents = 'none'
  host.style.zIndex = 'var(--z-toast, 4000)'
  document.body.appendChild(host)
  return host
}

export function toast(message: string, type: ToastType = 'info', duration = 2600) {
  const el = document.createElement('div')
  el.className = 'toast' + (type === 'success' ? ' toast-success' : type === 'error' ? ' toast-error' : '')
  el.textContent = message
  ensureHost().appendChild(el)
  window.setTimeout(() => {
    el.style.opacity = '0'
    el.style.transform = 'translate(-50%, 12px)'
    el.style.transition = 'opacity .25s, transform .25s'
    window.setTimeout(() => el.remove(), 260)
  }, duration)
}

export function useToast() {
  return {
    success: (m: string) => toast(m, 'success'),
    error: (m: string) => toast(m, 'error'),
    info: (m: string) => toast(m, 'info'),
  }
}
