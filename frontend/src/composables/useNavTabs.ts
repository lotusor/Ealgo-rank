/**
 * 顶部选项卡的用户自定义偏好。
 *
 * 存储：`localStorage['nav_tabs']`（与主题 `theme_pref` 同一套模式）。
 * 只存**键的顺序**，功能项的文案/路由/图标一律来自 `navRegistry`，
 * 因此清单改动（改文案、加功能）不需要迁移用户偏好。
 *
 * 三条硬规则：
 *  1. 可见性优先于偏好 —— 当前身份不可见的项，即使存在于偏好里也不渲染；
 *  2. 偏好里的项在当前身份下全部不可见时，退回默认集（登出场景）；
 *  3. 顶部至少保留 1 个、最多 `MAX_TABS` 个，避免空导航或被挤爆。
 */
import { computed, ref } from 'vue'
import {
  DEFAULT_TAB_KEYS,
  MAX_TABS,
  NAV_ITEMS,
  isNavItemVisible,
  type NavItem,
  type NavViewer,
} from '@/config/navRegistry'

const STORAGE_KEY = 'nav_tabs'

/** 读取并清洗已保存的偏好；返回 null 表示"从未自定义过，用默认集" */
function readSaved(): string[] | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed: unknown = JSON.parse(raw)
    if (!Array.isArray(parsed)) return null
    // 去掉功能下线 / 改名后残留的键，以及重复项
    const known = [
      ...new Set(
        parsed.filter(
          (k): k is string =>
            typeof k === 'string' && NAV_ITEMS.some((i) => i.key === k),
        ),
      ),
    ]
    return known.length ? known.slice(0, MAX_TABS) : null
  } catch {
    // 存储被手改坏 / 隐私模式禁用 → 当作未自定义，不抛错
    return null
  }
}

/** 模块级共享状态：NavBar 与移动抽屉读的是同一份 */
const savedKeys = ref<string[] | null>(readSaved())

function persist(keys: string[]) {
  savedKeys.value = keys
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(keys))
  } catch {
    /* 隐私模式等场景：仅本次会话生效，不阻断交互 */
  }
}

export type ToggleResult = 'pinned' | 'unpinned' | 'max' | 'min' | 'denied'

export function useNavTabs(viewer: NavViewer) {
  /** 当前身份可见的全部功能项 */
  const availableItems = computed<NavItem[]>(() =>
    NAV_ITEMS.filter((item) => isNavItemVisible(item, viewer)),
  )

  /** 固定在顶部的项（已按用户顺序、已按可见性过滤） */
  const tabItems = computed<NavItem[]>(() => {
    const byKey = new Map(availableItems.value.map((i) => [i.key, i]))
    const keys = savedKeys.value ?? DEFAULT_TAB_KEYS
    const picked = keys
      .map((k) => byKey.get(k))
      .filter((i): i is NavItem => Boolean(i))
    if (picked.length) return picked
    // 兜底：偏好项全部不可见（典型是登出后只剩公开项）→ 用默认集里可见的那部分
    return DEFAULT_TAB_KEYS.map((k) => byKey.get(k)).filter(
      (i): i is NavItem => Boolean(i),
    )
  })

  const pinnedKeys = computed<string[]>(() => tabItems.value.map((i) => i.key))

  const canPinMore = computed(() => pinnedKeys.value.length < MAX_TABS)

  function isPinned(key: string): boolean {
    return pinnedKeys.value.includes(key)
  }

  /** 固定 / 取消固定 */
  function toggle(key: string): ToggleResult {
    const item = NAV_ITEMS.find((i) => i.key === key)
    if (!item || !isNavItemVisible(item, viewer)) return 'denied'
    const current = pinnedKeys.value
    if (current.includes(key)) {
      if (current.length <= 1) return 'min'
      persist(current.filter((k) => k !== key))
      return 'unpinned'
    }
    if (current.length >= MAX_TABS) return 'max'
    persist([...current, key])
    return 'pinned'
  }

  /** 在固定列表内上/下移一位（键盘与按钮可达，不依赖拖拽） */
  function moveBy(key: string, delta: number): void {
    const current = [...pinnedKeys.value]
    const from = current.indexOf(key)
    if (from < 0) return
    const to = Math.min(Math.max(from + delta, 0), current.length - 1)
    if (to === from) return
    current.splice(to, 0, ...current.splice(from, 1))
    persist(current)
  }

  /** 拖拽排序：把 fromKey 移到 toKey 的位置 */
  function moveTo(fromKey: string, toKey: string): void {
    const current = [...pinnedKeys.value]
    const from = current.indexOf(fromKey)
    const to = current.indexOf(toKey)
    if (from < 0 || to < 0 || from === to) return
    current.splice(to, 0, ...current.splice(from, 1))
    persist(current)
  }

  /** 恢复默认选项卡 */
  function reset(): void {
    savedKeys.value = null
    try {
      localStorage.removeItem(STORAGE_KEY)
    } catch {
      /* ignore */
    }
  }

  return {
    availableItems,
    tabItems,
    pinnedKeys,
    canPinMore,
    isPinned,
    toggle,
    moveBy,
    moveTo,
    reset,
    maxTabs: MAX_TABS,
  }
}
