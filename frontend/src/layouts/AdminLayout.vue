<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import NavBar from '@/components/layout/NavBar.vue'
import SystemAnnouncement from '@/components/layout/SystemAnnouncement.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const groups = computed(() => {
  const g: { label: string; links: { label: string; name: string; icon: string; superOnly?: boolean }[] }[] = [
    {
      label: '概览',
      links: [{ label: '仪表盘', name: 'dashboard', icon: 'M3 3h7v9H3zM14 3h7v5h-7zM14 12h7v9h-7zM3 16h7v5H3z' }],
    },
    {
      label: '数据管理',
      links: [
        { label: '学校管理', name: 'schools', icon: 'M22 10v6M2 10l10-5 10 5-10 5zM6 12v5c3 3 9 3 12 0v-5', superOnly: true },
        { label: '参赛记录', name: 'participations', icon: 'M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6' },
        { label: '成员名单', name: 'members', icon: 'M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2M9 7a4 4 0 1 0 0 0M23 21v-2a4 4 0 0 0-3-3.87' },
        { label: '群发站内信', name: 'notifications', icon: 'M3 8l7.89 5.26a2 2 0 0 0 2.22 0L21 8M5 19h14a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2z', superOnly: true },
        { label: '积分系数', name: 'score-config', icon: 'M3 3v18h18M7 16l4-4 4 4 5-5', superOnly: true },
      ],
    },
    {
      label: '运营',
      links: [
        { label: '申请审批', name: 'applications', icon: 'M9 11l3 3L22 4M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11' },
        { label: '爬虫任务', name: 'crawl', icon: 'M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M12 12a3 3 0 1 0 0 0', superOnly: true },
      ],
    },
  ]
  return g.map((grp) => ({ ...grp, links: grp.links.filter((l) => !l.superOnly || auth.isSuperAdmin) }))
})

const currentName = computed(() => route.name as string)

const drawerOpen = ref(false)
function go(name: string) {
  drawerOpen.value = false
  router.push({ name })
}
</script>

<template>
  <div class="app-shell admin-shell">
    <NavBar />
    <SystemAnnouncement />
    <div class="admin-body">
      <aside class="admin-sidebar" :class="{ open: drawerOpen }">
        <template v-for="grp in groups" :key="grp.label">
          <div class="sidebar-group-label">{{ grp.label }}</div>
          <a
            v-for="link in grp.links"
            :key="link.name"
            class="sidebar-link"
            :class="{ active: currentName === link.name }"
            @click="go(link.name)"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path :d="link.icon" />
            </svg>
            {{ link.label }}
          </a>
        </template>
      </aside>
      <div class="admin-backdrop" :class="{ open: drawerOpen }" @click="drawerOpen = false" />
      <main class="main-content admin-main">
        <router-view />
      </main>
    </div>
  </div>
</template>

<style scoped>
.admin-shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
.admin-body {
  display: flex;
  flex: 1;
  min-height: 0;
}
.admin-sidebar {
  width: var(--sidebar-width);
  flex-shrink: 0;
  background: var(--color-bg-surface);
  /* 修复：原型缺 1px solid */
  border-right: 1px solid var(--color-border);
  padding: var(--space-5) var(--space-3);
  position: sticky;
  top: var(--nav-height);
  height: calc(100vh - var(--nav-height));
  overflow-y: auto;
}
.sidebar-group-label {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--color-text-tertiary);
  padding: var(--space-4) var(--space-3) var(--space-2);
}
.sidebar-link {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-3);
  border-radius: var(--radius-md);
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-secondary);
  cursor: pointer;
  margin-bottom: 2px;
  transition: all var(--duration-fast);
}
.sidebar-link svg {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}
.sidebar-link:hover {
  background: var(--color-bg-overlay);
  color: var(--color-text-primary);
}
.sidebar-link.active {
  background: var(--color-primary-subtle);
  color: var(--color-primary);
  font-weight: 600;
}
.admin-main {
  flex: 1;
  min-width: 0;
  padding: var(--space-6) var(--space-8);
}
.admin-backdrop {
  display: none;
}
@media (max-width: 860px) {
  .admin-sidebar {
    position: fixed;
    top: var(--nav-height);
    left: 0;
    bottom: 0;
    z-index: var(--z-sidebar);
    transform: translateX(-100%);
    transition: transform var(--duration-slow) var(--ease-standard);
  }
  .admin-sidebar.open {
    transform: translateX(0);
  }
  .admin-backdrop.open {
    display: block;
    position: fixed;
    inset: var(--nav-height) 0 0 0;
    background: rgba(0, 0, 0, 0.5);
    z-index: var(--z-sidebar);
  }
  .admin-main {
    padding: var(--space-5) var(--space-4);
  }
}
</style>
