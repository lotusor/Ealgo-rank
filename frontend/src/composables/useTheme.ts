/**
 * 主题切换（深色 / 浅色），偏好持久化到 localStorage。
 * 通过 <html data-theme="light"> 触发 tokens.css 里的浅色令牌覆盖集。
 */
import { ref } from 'vue'

const STORAGE_KEY = 'theme_pref'
export type Theme = 'dark' | 'light'

function initial(): Theme {
  const saved = localStorage.getItem(STORAGE_KEY)
  return saved === 'light' || saved === 'dark' ? saved : 'dark'
}

const theme = ref<Theme>(initial())

function apply(t: Theme) {
  theme.value = t
  document.documentElement.dataset.theme = t
  localStorage.setItem(STORAGE_KEY, t)
}

// 首屏即应用，避免浅色模式下的深色闪屏
apply(theme.value)

export function useTheme() {
  return {
    theme,
    toggle: () => apply(theme.value === 'dark' ? 'light' : 'dark'),
    set: apply,
  }
}
