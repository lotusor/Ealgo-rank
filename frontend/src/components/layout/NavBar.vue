<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useTheme } from '@/composables/useTheme'
import { logout } from '@/api'

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
function onDocClick(e: MouseEvent) {
  if (menuRef.value && !menuRef.value.contains(e.target as Node)) {
    menuOpen.value = false
  }
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
