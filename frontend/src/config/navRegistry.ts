/**
 * 全站功能清单 —— 导航的**单一数据源**。
 *
 * 为什么要有这个文件：改造前 `NavBar.vue` 把导航写死成两个数组（桌面一份、
 * 移动抽屉一份），新增一个功能要改两处、漏改就会出现"桌面有、手机没有"。
 * 现在桌面选项卡条、移动抽屉、全部功能面板三处**共用本清单**。
 *
 * 约定：
 * - `key` 必须等于 vue-router 的路由 `name`，既用于跳转也用于高亮匹配。
 * - 可见性一律由 `anonymous` / `superOnly` 声明，**不要在组件里写死**。
 * - 用户自定义只能在这个清单里"取舍与排序"，不能越权显示。
 */

/** 导航分组（决定「全部功能」面板的分节顺序） */
export type NavGroupKey = 'overview' | 'contest' | 'ranking' | 'mine' | 'admin'

export interface NavGroup {
  key: NavGroupKey
  label: string
}

export const NAV_GROUPS: NavGroup[] = [
  { key: 'overview', label: '概览' },
  { key: 'contest', label: '赛事' },
  { key: 'ranking', label: '排行与规则' },
  { key: 'mine', label: '我的' },
  { key: 'admin', label: '管理' },
]

export interface NavItem {
  /** 等于 vue-router 路由 name（同时作为偏好存储的键） */
  key: string
  label: string
  group: NavGroupKey
  /** 内联 SVG 的 path d（24×24、stroke 风格，与后台侧栏一致） */
  icon: string
  /** 「全部功能」面板里的一行说明 */
  desc: string
  /** 未登录是否可见。默认 false = 需要登录 */
  anonymous?: boolean
  /** 仅超级管理员可见 */
  superOnly?: boolean
}

/** 判定可见性所需的最小身份信息（结构化类型，避免与 Pinia store 强耦合） */
export interface NavViewer {
  isAuthenticated: boolean
  isAdmin: boolean
  isSuperAdmin: boolean
}

/**
 * ⚠️ **「竞赛日历」入口当前未开放（2026-09-18 上线导航时临时摘除）**。
 *
 * 原因：日历前端依赖后端新增的 `/api/v1/contests/meta/` 与 `status=` /
 * `end_after=` 过滤，而该后端尚未部署；若此时暴露入口，用户点进去会看到加载失败。
 *
 * 放开步骤（后端与日历前端一起部署时）：
 *  1. 在下方 `NAV_ITEMS` 的「赛事」分组内恢复 calendar 项：
 *     `{ key: 'calendar', label: '竞赛日历', group: 'contest',
 *        icon: 'M3 4h18v18H3zM16 2v4M8 2v4M3 10h18',
 *        desc: '赛程月历与近期赛事', anonymous: true }`
 *  2. 恢复 `router/index.ts` 里的 `/calendar` 路由（`meta: { optionalAuth: true }`）
 *  详见 HANDOVER §1.7.22。
 */
export const NAV_ITEMS: NavItem[] = [
  {
    key: 'home',
    label: '首页',
    group: 'overview',
    icon: 'M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2zM9 22V12h6v10',
    desc: '数据看板与快捷入口',
  },
  {
    key: 'contests',
    label: '比赛列表',
    group: 'contest',
    icon: 'M8 21h8M12 17v4M7 4h10v5a5 5 0 0 1-10 0zM17 5h3v2a3 3 0 0 1-3 3M7 5H4v2a3 3 0 0 0 3 3',
    desc: '按平台与难度检索历史赛事',
  },
  {
    key: 'rankings',
    label: '排名榜',
    group: 'ranking',
    icon: 'M2 20h20M4 20V10M10 20V4M16 20v-7',
    desc: '学校榜与个人榜',
  },
  {
    key: 'score-rules',
    label: '积分规则',
    group: 'ranking',
    icon: 'M12 2l3 6 7 1-5 5 1 7-6-3-6 3 1-7-5-5 7-1z',
    desc: '计分口径与系数说明',
  },
  {
    key: 'my-scores',
    label: '个人中心',
    group: 'mine',
    icon: 'M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2M9 2h6v4H9z',
    desc: '我的成绩与参赛记录',
  },
  {
    key: 'profile',
    label: '资料编辑',
    group: 'mine',
    icon: 'M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2M12 3a4 4 0 1 0 0 8 4 4 0 0 0 0-8z',
    desc: '昵称、头像与平台账号绑定',
  },
  {
    key: 'security',
    label: '账号安全',
    group: 'mine',
    icon: 'M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z',
    desc: '密码、会话与登录历史',
  },
  {
    key: 'my-application',
    label: '我的申请',
    group: 'mine',
    icon: 'M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6',
    desc: '学校管理员申请进度',
  },
  {
    key: 'dashboard',
    label: '管理后台',
    group: 'admin',
    icon: 'M3 3h7v9H3zM14 3h7v5h-7zM14 12h7v9h-7zM3 16h7v5H3z',
    desc: '学校、审批、爬虫与运营',
  },
]

/** 单个功能项对当前身份是否可见 */
export function isNavItemVisible(item: NavItem, viewer: NavViewer): boolean {
  if (item.superOnly && !viewer.isSuperAdmin) return false
  if (item.group === 'admin' && !viewer.isAdmin) return false
  if (!item.anonymous && !viewer.isAuthenticated) return false
  return true
}

/** 当前身份可见的全部功能项（保持清单声明顺序） */
export function visibleNavItems(viewer: NavViewer): NavItem[] {
  return NAV_ITEMS.filter((item) => isNavItemVisible(item, viewer))
}

/** 按分组聚合可见项，供「全部功能」面板渲染 */
export function groupedNavItems(
  viewer: NavViewer,
): { group: NavGroup; items: NavItem[] }[] {
  const visible = visibleNavItems(viewer)
  return NAV_GROUPS.map((group) => ({
    group,
    items: visible.filter((item) => item.group === group.key),
  })).filter((section) => section.items.length > 0)
}

/**
 * 首次访问（用户从未自定义过）时默认固定在顶部的项。
 * 未登录时其中多数不可见，`useNavTabs` 会自动退化为"仅可见的那部分"。
 *
 * 注：`calendar` 当前不在 `NAV_ITEMS` 里（竞赛日历入口暂未开放，见下），
 * 保留在此是为了放开时无需改这里；`useNavTabs` 会自动忽略清单里不存在的键。
 */
export const DEFAULT_TAB_KEYS = ['home', 'rankings', 'calendar', 'contests']

/** 顶部最多固定几个选项卡（超过会挤压右侧操作区） */
export const MAX_TABS = 6
