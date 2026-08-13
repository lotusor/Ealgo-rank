<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useTheme } from '@/composables/useTheme'
import {
  logout,
  fetchNotifications,
  markNotificationRead,
  markAllNotificationsRead,
} from '@/api'
import type { AppNotification } from '@/api/types'

const { theme, toggle: toggleTheme } = useTheme()

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const nav = [
  { label: '首页', key: 'home', path: '/u' },
  { label: '排名榜', key: 'rankings', path: '/u/rankings' },
  { label: '比赛列表', key: 'contests', path: '/u/contests' },
  { label: '个人中心', key: 'my-scores', path: '/u/my-scores' },
]

const activeKey = computed(() => route.name as string)

const menuOpen = ref(false)
const menuRef = ref<HTMLElement | null>(null)

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

function onDocClick(e: MouseEvent) {
  const t = e.target as Node
  if (menuRef.value && !menuRef.value.contains(t)) menuOpen.value = false
  if (bellRef.value && !bellRef.value.contains(t)) notifOpen.value = false
}
onMounted(() => document.addEventListener('mousedown', onDocClick))
onUnmounted(() => document.removeEventListener('mousedown', onDocClick))

const drawerOpen = ref(false)
function go(path: string) {
  drawerOpen.value = false
  menuOpen.value = false
  router.push(path)
}

const roleBadge = computed(() =>
  auth.isSuperAdmin
    ? { text: '超级管理员', cls: 'badge-danger' }
    : auth.isSchoolAdmin
      ? { text: '学校管理员', cls: 'badge-warning' }
      : { text: '用户', cls: 'badge-muted' },
)

function doLogout() {
  menuOpen.value = false
  logout()
  auth.logout()
  router.push({ name: 'login' })
}

defineExpose({ drawerOpen })
</script>

<template>
  <header class="navbar">
    <div class="navbar-inner">
      <div class="brand" @click="go('/u')">
        <div class="brand-mark">
          <svg viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M3 17l4-4 4 4 4-8 4 8" />
            <circle cx="7" cy="13" r="1" fill="var(--color-primary)" />
            <circle cx="19" cy="13" r="1" fill="var(--color-primary)" />
          </svg>
        </div>
        <span>E-algo <span class="brand-accent">Rank</span></span>
      </div>

      <nav class="nav-links">
        <a
          v-for="item in nav"
          :key="item.key"
          :class="{ active: activeKey === item.key }"
          @click="go(item.path)"
          >{{ item.label }}</a
        >
        <a
          v-if="auth.isAdmin"
          :class="{ active: activeKey === 'dashboard' || (route.path.startsWith('/admin') && activeKey !== 'dashboard') }"
          @click="go('/admin/dashboard')"
          >管理后台</a
        >
      </nav>

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
        <button v-if="!auth.isAuthenticated" class="btn btn-primary btn-sm" @click="go('/login')">
          登录 / 注册
        </button>
        <div v-else class="user-menu" ref="menuRef">
          <button class="user-trigger" @click="menuOpen = !menuOpen">
            <span class="user-name">{{ auth.user?.real_name || auth.user?.username }}</span>
            <span class="badge" :class="roleBadge.cls">{{ roleBadge.text }}</span>
          </button>
          <div v-if="menuOpen" class="menu">
            <a v-if="auth.isAdmin" @click="go('/admin/dashboard')">后台管理</a>
            <a @click="go('/u/my-scores')">个人中心</a>
            <a class="danger" @click="doLogout">退出登录</a>
          </div>
        </div>

        <button class="nav-toggle" @click="drawerOpen = !drawerOpen">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M3 12h18M3 6h18M3 18h18" />
          </svg>
        </button>
      </div>
    </div>
  </header>

  <div class="mobile-drawer" :class="{ open: drawerOpen }">
    <a
      v-for="item in nav"
      :key="item.key"
      :class="{ active: activeKey === item.key }"
      @click="go(item.path)"
      >{{ item.label }}</a
    >
    <a v-if="auth.isAdmin" :class="{ active: route.path.startsWith('/admin') }" @click="go('/admin/dashboard')">管理后台</a>
  </div>
</template>

<style scoped>
.user-menu {
  position: relative;
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
.menu {
  position: absolute;
  right: 0;
  top: calc(100% + 8px);
  min-width: 160px;
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  padding: var(--space-2);
  z-index: var(--z-dropdown);
}
.menu a {
  display: block;
  padding: var(--space-3) var(--space-3);
  border-radius: var(--radius-md);
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all var(--duration-fast);
}
.menu a:hover {
  background: var(--color-bg-overlay);
  color: var(--color-text-primary);
}
.menu a.danger:hover {
  color: var(--color-danger);
}
</style>
