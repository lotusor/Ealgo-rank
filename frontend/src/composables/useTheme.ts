/**
 * 主题切换（纸本浅色 / 夜读深色），偏好持久化到 localStorage。
 * 新访客默认落纸本；已表达过偏好的用户保持原选择。
 */
import { ref } from 'vue'

const STORAGE_KEY = 'theme_pref'
export type Theme = 'dark' | 'light'

function initial(): Theme {
  const saved = localStorage.getItem(STORAGE_KEY)
  return saved === 'light' || saved === 'dark' ? saved : 'light'
}

const theme = ref<Theme>(initial())

function apply(t: Theme) {
  theme.value = t
  document.documentElement.dataset.theme = t
  document
    .querySelector('meta[name="theme-color"]')
    ?.setAttribute('content', t === 'dark' ? '#12100D' : '#F3EFE6')
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
