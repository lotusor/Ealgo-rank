import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { public: true },
    },
    {
      // 注册 / 登录入口
      path: '/register',
      name: 'register',
      component: () => import('@/views/auth/RegisterEntryView.vue'),
      meta: { public: true },
    },
    {
      // 信息填写（新建本地账号）
      path: '/register/info',
      name: 'register-info',
      component: () => import('@/views/auth/RegisterInfoView.vue'),
      meta: { public: true },
    },
    {
      // 补全流程（passport 用户绑定学校 / 资料）
      path: '/register/complete',
      name: 'register-complete',
      component: () => import('@/views/auth/RegisterCompleteView.vue'),
      meta: { requiresAuth: true },
    },
    {
      // 第二步：是否申请学校管理员
      path: '/register/admin-apply',
      name: 'register-admin',
      component: () => import('@/views/auth/RegisterAdminApplyView.vue'),
      meta: { requiresAuth: true },
    },
    {
      // passport 认证回调（解析参数 / 存储登录态 / 路由分流）
      path: '/auth/callback',
      name: 'auth-callback',
      component: () => import('@/views/auth/AuthCallbackView.vue'),
      meta: { public: true },
    },
    {
      // 用户端（普通注册用户 + 管理员均可访问）
      path: '/u',
      component: () => import('@/layouts/PublicLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        { path: '', name: 'home', component: () => import('@/views/user/HomeView.vue') },
        {
          path: 'rankings',
          name: 'rankings',
          component: () => import('@/views/user/RankingsView.vue'),
        },
        {
          path: 'my-scores',
          name: 'my-scores',
          component: () => import('@/views/user/MyScoresView.vue'),
        },
        {
          path: 'contests',
          name: 'contests',
          component: () => import('@/views/user/ContestsView.vue'),
        },
      ],
    },
    {
      // 根路径默认进入注册/登录入口（普通用户起点）
      path: '/',
      redirect: { name: 'register' },
    },
    {
      // 管理后台（仅管理员）— 整体挂在 /admin 下
      path: '/admin',
      component: () => import('@/layouts/AdminLayout.vue'),
      meta: { requiresAdmin: true },
      children: [
        { path: '', redirect: { name: 'dashboard' } },
        {
          path: 'dashboard',
          name: 'dashboard',
          component: () => import('@/views/admin/DashboardView.vue'),
        },
        {
          path: 'schools',
          name: 'schools',
          component: () => import('@/views/admin/SchoolsView.vue'),
          meta: { superOnly: true },
        },
        {
          path: 'applications',
          name: 'applications',
          component: () => import('@/views/admin/ApplicationsView.vue'),
        },
        {
          path: 'crawl',
          name: 'crawl',
          component: () => import('@/views/admin/CrawlView.vue'),
        },
        {
          path: 'participations',
          name: 'participations',
          component: () => import('@/views/admin/ParticipationsView.vue'),
        },
        {
          path: 'members',
          name: 'members',
          component: () => import('@/views/admin/MembersView.vue'),
        },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: { name: 'rankings' } },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()

  // 回调页自行处理登录态（写 token 后再 loadMe），守卫直接放行
  if (to.name === 'auth-callback') return true

  // 已登录（有 token）但还没拉取用户信息，先补一次
  if (auth.token && !auth.user && to.name !== 'login') {
    try {
      await auth.loadMe()
    } catch {
      auth.logout()
    }
  }

  if (to.meta.public) {
    if (auth.isAuthenticated && auth.isAdmin) return { name: 'dashboard' }
    if (auth.isAuthenticated && !auth.isAdmin) return { name: 'rankings' }
    return true
  }

  if (!auth.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  // 已登录但未补全资料（未绑定学校）→ 强制走补全流程；补全流程本身放行
  if (!auth.isProfileComplete && to.name !== 'register-complete') {
    return { name: 'register-complete' }
  }
  // 已补全却误入补全流程 → 按角色进入主页（申请管理员步骤对任意已登录用户开放）
  if (auth.isProfileComplete && to.name === 'register-complete') {
    return auth.isAdmin ? { name: 'dashboard' } : { name: 'rankings' }
  }

  // 普通用户访问管理后台 → 引导到用户端
  if (to.meta.requiresAdmin && !auth.isAdmin) {
    return { name: 'rankings' }
  }
  if (to.meta.superOnly && !auth.isSuperAdmin) {
    return { name: 'dashboard' }
  }
  return true
})

export default router
