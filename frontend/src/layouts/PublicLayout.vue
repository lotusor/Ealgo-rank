<script setup lang="ts">
import NavBar from '@/components/layout/NavBar.vue'
import SystemAnnouncement from '@/components/layout/SystemAnnouncement.vue'
</script>

<template>
  <div class="app-shell">
    <NavBar />
    <SystemAnnouncement />
    <main class="main-content">
      <router-view v-slot="{ Component, route }">
        <transition name="page" mode="out-in" appear>
          <component :is="Component" :key="route.path" />
        </transition>
      </router-view>
    </main>
    <footer class="app-footer">
      <div class="app-footer-inner">
        <div>
          <div class="footer-wordmark">E-algo <em>Rank</em></div>
          <div class="footer-note">高校算法竞赛积分年鉴 · Season 2026</div>
        </div>
        <div class="legal">
          © 2026 E时代算法竞赛排名系统<br />
          E-algo Rank™ 为演示项目产品名称<br />
          蜀ICP备2026045461号
        </div>
      </div>
    </footer>
  </div>
</template>
