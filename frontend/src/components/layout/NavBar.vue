<script setup lang="ts">
/**
 * 全站顶部导航。
 *
 * 改造要点（2026-09-18）：
 *  - 导航项不再写死在组件里（旧版桌面与移动抽屉各写一份，新增功能要改两处），
 *    统一取自 `@/config/navRegistry`，三处渲染共用一份清单。
 *  - 顶部只展示用户自定义的选项卡（`NavTabs`），其余收进「全部功能」面板
 *    （`NavPalette`）；≤768px 时选项卡条隐藏，抽屉直接复用同一面板内容。
 *  - 未登录时只展示公开功能，右侧降级为「登录 / 注册」。
 */
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useTheme } from '@/composables/useTheme'
import { useNavTabs } from '@/composables/useNavTabs'
import { toast } from '@/composables/useToast'
import { groupedNavItems } from '@/config/navRegistry'
import UserAvatar from '@/components/ui/UserAvatar.vue'
import Popover from '@/components/ui/Popover.vue'
import NavTabs from '@/components/layout/NavTabs.vue'
import NavPalette from '@/components/layout/NavPalette.vue'
import {
  fetchNotifications,
  markNotificationRead,
  markAllNotificationsRead,
} from '@/api'
import type { AppNotification } from '@/api/types'

const { theme, toggle: toggleTheme } = useTheme()

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

// 导航清单 + 用户自定义选项卡（偏好存 localStorage['nav_tabs']）
const {
  tabItems,
  pinnedKeys,
  maxTabs,
  toggle: toggleTab,
  moveBy,
  moveTo,
  reset: resetTabs,
} = useNavTabs(auth)
const paletteSections = computed(() => groupedNavItems(auth))

/** 当前高亮项：后台整体高亮「管理后台」 */
const activeKey = computed(() => {
  if (route.path.startsWith('/admin')) return 'dashboard'
  return typeof route.name === 'string' ? route.name : ''
})

const menuOpen = ref(false)
const paletteOpen = ref(false)

// ---------- 站内信收件箱（铃铛） ----------
const notifOpen = ref(false)
const bellRef = ref<HTMLElement | null>(null)
const notifications = ref<AppNotification[]>([])
const unreadCount = computed(() =>
  notifications.value.filter((n) => !n.is_read).length,
)

async function loadNotifications() {
  try {
    const res = await fetchNotifications({ page_size: 10 })
    notifications.value = res.results
  } catch {
    /* 忽略：未登录或网络异常时静默 */
  }
}

function toggleNotif() {
  notifOpen.value = !notifOpen.value
  if (notifOpen.value) loadNotifications()
}

async function openNotification(n: AppNotification) {
  if (!n.is_read) {
    try {
      await markNotificationRead(n.id)
      n.is_read = true
    } catch {
      /* ignore */
    }
  }
  if (n.link) {
    notifOpen.value = false
    router.push(n.link)
  }
}

async function markAll() {
  try {
    await markAllNotificationsRead()
    notifications.value.forEach((n) => (n.is_read = true))
  } catch {
    /* ignore */
  }
}

function fmtTime(s: string) {
  const d = new Date(s)
  return Number.isNaN(d.getTime()) ? s : d.toLocaleString()
}

// 铃铛面板仍是内联实现（外点关闭）；用户菜单与功能面板改用 Popover 统一处理
function onDocClick(e: MouseEvent) {
  const t = e.target as Node
  if (bellRef.value && !bellRef.value.contains(t)) notifOpen.value = false
}
onMounted(() => document.addEventListener('mousedown', onDocClick))
onUnmounted(() => document.removeEventListener('mousedown', onDocClick))

const drawerOpen = ref(false)

function closeAll() {
  drawerOpen.value = false
  menuOpen.value = false
  paletteOpen.value = false
  notifOpen.value = false
}

/** 按功能键跳转（键即路由 name） */
function goByKey(key: string) {
  closeAll()
  if (route.name === key) return
  router.push({ name: key })
}

function goPath(path: string) {
  closeAll()
  router.push(path)
}

/** 固定 / 取消固定选项卡，并给出边界提示 */
function onToggleTab(key: string) {
  const result = toggleTab(key)
  if (result === 'max') {
    toast(`最多固定 ${maxTabs} 个，可先移除一个`, 'info')
  } else if (result === 'min') {
    toast('至少保留 1 个选项卡', 'info')
  }
}

function onResetTabs() {
  resetTabs()
  toast('已恢复默认选项卡', 'success')
}

const roleBadge = computed(() =>
  auth.isSuperAdmin
    ? { text: '超级管理员', cls: 'badge-danger' }
    : auth.isSchoolAdmin
      ? { text: '学校管理员', cls: 'badge-warning' }
      : { text: '用户', cls: 'badge-muted' },
)

async function doLogout() {
  menuOpen.value = false
  await auth.logout() // 内部已处理 passport 吊销 + 本地清理
  router.push({ name: 'login' })
}

defineExpose({ drawerOpen })
</script>

<template>
  <header class="navbar">
    <div class="navbar-inner">
      <div class="brand" @click="auth.isAuthenticated ? goByKey('home') : goPath('/calendar')">
        <div class="brand-mark">
          <img src="/logo-64.png" alt="E-algo Rank" />
        </div>
        <span class="brand-text">E-algo <span class="brand-accent">Rank</span></span>
      </div>

      <NavTabs
        :items="tabItems"
        :active-key="activeKey"
        @navigate="goByKey"
      />

      <Popover v-model:open="paletteOpen" align="start" panel-width="300px" class="nav-palette">
        <template #trigger="{ toggle, open }">
          <button
            class="nav-palette-btn"
            :class="{ active: open }"
            type="button"
            :aria-expanded="open"
            title="全部功能"
            @click="toggle"
          >
            全部功能
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M6 9l6 6 6-6" />
            </svg>
          </button>
        </template>
        <template #panel>
          <NavPalette
            :sections="paletteSections"
            :pinned-keys="pinnedKeys"
            :max-tabs="maxTabs"
            @toggle="onToggleTab"
            @move-by="moveBy"
            @move-to="moveTo"
            @reset="onResetTabs"
            @navigate="goByKey"
          />
        </template>
      </Popover>

      <div class="nav-actions">
        <button class="btn btn-ghost btn-icon" :title="theme === 'dark' ? '切换到浅色' : '切换到深色'" @click="toggleTheme">
          <svg v-if="theme === 'dark'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" /></svg>
          <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" /></svg>
        </button>

        <div v-if="auth.isAuthenticated" class="notif-wrap" ref="bellRef">
          <button class="btn btn-ghost btn-icon" title="消息" @click="toggleNotif">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" /><path d="M13.73 21a2 2 0 0 1-3.46 0" /></svg>
            <span v-if="unreadCount" class="notif-badge">{{ unreadCount > 99 ? '99+' : unreadCount }}</span>
          </button>
          <div v-if="notifOpen" class="notif-panel">
            <div class="notif-head">
              <span>消息</span>
              <button class="link-btn" @click="markAll">全部已读</button>
            </div>
            <div class="notif-list">
              <div v-if="!notifications.length" class="notif-empty">暂无消息</div>
              <button
                v-for="n in notifications"
                :key="n.id"
                class="notif-item"
                :class="{ unread: !n.is_read }"
                @click="openNotification(n)"
              >
                <div class="notif-title">{{ n.title }}</div>
                <div v-if="n.message" class="notif-msg">{{ n.message }}</div>
                <div class="notif-time">{{ fmtTime(n.created_at) }}</div>
              </button>
            </div>
          </div>
        </div>

        <button v-if="!auth.isAuthenticated" class="btn btn-primary btn-sm" @click="goPath('/login')">
          登录 / 注册
        </button>

        <Popover v-else v-model:open="menuOpen" align="end" panel-width="180px">
          <template #trigger="{ toggle, open }">
            <button class="user-trigger" type="button" :aria-expanded="open" @click="toggle">
              <UserAvatar
                :name="auth.user?.real_name || auth.user?.username"
                :avatar="auth.user?.avatar"
                :size="28"
              />
              <span class="user-name">{{ auth.user?.real_name || auth.user?.username }}</span>
              <span class="badge" :class="roleBadge.cls">{{ roleBadge.text }}</span>
            </button>
          </template>
          <template #panel>
            <div class="menu-list">
              <a v-if="auth.isAdmin" @click="goByKey('dashboard')">后台管理</a>
              <a @click="goByKey('my-scores')">个人中心</a>
              <a @click="goByKey('profile')">资料编辑</a>
              <a @click="goByKey('security')">账号安全</a>
              <a class="danger" @click="doLogout">退出登录</a>
            </div>
          </template>
        </Popover>

        <button class="nav-toggle" :aria-expanded="drawerOpen" aria-label="打开菜单" @click="drawerOpen = !drawerOpen">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M3 12h18M3 6h18M3 18h18" />
          </svg>
        </button>
      </div>
    </div>
  </header>

  <div class="mobile-drawer" :class="{ open: drawerOpen }">
    <NavPalette
      :sections="paletteSections"
      :pinned-keys="pinnedKeys"
      :max-tabs="maxTabs"
      @toggle="onToggleTab"
      @move-by="moveBy"
      @move-to="moveTo"
      @reset="onResetTabs"
      @navigate="goByKey"
    />
  </div>
</template>

<style scoped>
.user-trigger {
  display: inline-flex;
  align-items: center;
  gap: var(--space-3);
  height: var(--control-height);
  padding: 0 var(--space-3);
  border-radius: var(--radius-md);
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border);
  transition: all var(--duration-base) var(--ease-standard);
}
.user-trigger:hover {
  border-color: var(--color-border-focus);
}
.user-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 「全部功能」触发器：视觉上与选项卡同排 */
.nav-palette-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-secondary);
  background: none;
  border: none;
  cursor: pointer;
  white-space: nowrap;
  transition: all var(--duration-base) var(--ease-standard);
}
.nav-palette-btn svg {
  width: 14px;
  height: 14px;
}
.nav-palette-btn:hover,
.nav-palette-btn.active {
  color: var(--color-text-primary);
  background: var(--color-bg-elevated);
}

/* Popover 面板内的菜单列表（面板外观由 Popover 提供） */
.menu-list {
  padding: var(--space-2);
}
.menu-list a {
  display: block;
  padding: var(--space-3);
  border-radius: var(--radius-md);
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all var(--duration-fast);
}
.menu-list a:hover {
  background: var(--color-bg-overlay);
  color: var(--color-text-primary);
}
.menu-list a.danger:hover {
  color: var(--color-danger);
}

/* ---------- 站内信铃铛 ---------- */
.notif-wrap {
  position: relative;
}
.notif-badge {
  position: absolute;
  top: -4px;
  right: -4px;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  border-radius: 999px;
  background: var(--color-danger);
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  line-height: 16px;
  text-align: center;
}
.notif-panel {
  position: absolute;
  right: 0;
  top: calc(100% + 8px);
  width: 320px;
  max-height: 420px;
  display: flex;
  flex-direction: column;
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  z-index: var(--z-dropdown);
  overflow: hidden;
}
.notif-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--color-border);
  font-weight: 600;
  font-size: 14px;
  color: var(--color-text-primary);
}
.link-btn {
  background: none;
  border: none;
  color: var(--color-primary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
}
.notif-list {
  overflow-y: auto;
}
.notif-empty {
  padding: var(--space-6);
  text-align: center;
  color: var(--color-text-muted);
  font-size: 13px;
}
.notif-item {
  display: block;
  width: 100%;
  text-align: left;
  padding: var(--space-3) var(--space-4);
  background: none;
  border: none;
  border-bottom: 1px solid var(--color-border);
  cursor: pointer;
  transition: background var(--duration-fast);
}
.notif-item:hover {
  background: var(--color-bg-overlay);
}
.notif-item.unread {
  background: color-mix(in srgb, var(--color-primary) 8%, transparent);
}
.notif-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
}
.notif-msg {
  margin-top: 2px;
  font-size: 13px;
  color: var(--color-text-secondary);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.notif-time {
  margin-top: 4px;
  font-size: 12px;
  color: var(--color-text-muted);
}

/* 移动端：选项卡条由既有全局规则隐藏，这里同步隐藏「全部功能」按钮
   （抽屉里已是同一份面板，无需重复入口）。
   窄屏只保留 Logo 图形与头像：品牌文字 + 角色徽标会把导航栏撑到
   500px 以上，在 390px 视口产生横向滚动（既有缺陷，2026-09-18 随导航改造修复）。 */
@media (max-width: 768px) {
  .nav-palette-btn,
  .nav-palette,
  .brand-text,
  .user-name,
  .user-trigger .badge {
    display: none;
  }
}
</style>
