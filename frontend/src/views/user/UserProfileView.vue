<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getUserPublicProfile } from '@/api'
import type { UserPublicProfile } from '@/api/types'
import EmptyState from '@/components/ui/EmptyState.vue'
import { platformTag } from '@/utils/format'

const route = useRoute()
const router = useRouter()

const profile = ref<UserPublicProfile | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

onMounted(async () => {
  const id = Number(route.params.id)
  if (!id) {
    error.value = '无效的用户'
    loading.value = false
    return
  }
  try {
    profile.value = await getUserPublicProfile(id)
  } catch (e: any) {
    error.value = e?.response?.data?.detail || '加载用户信息失败'
  } finally {
    loading.value = false
  }
})

function accountTag(p: string) {
  return p === 'codeforces' ? 'cf' : p === 'atcoder' ? 'atcoder' : p === 'nowcoder' ? 'nowcoder' : ''
}
function fmtDate(s: string | null) {
  if (!s) return '—'
  return new Date(s).toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
}
function fmtDelta(v: number) {
  return v > 0 ? `+${v}` : `${v}`
}
</script>

<template>
  <div class="container-wide">
    <div class="page-head">
      <div>
        <div class="breadcrumb">
          <a @click="router.push('/u/rankings')">排名榜</a><span>/</span><span>用户信息</span>
        </div>
        <h1 class="page-title">用户信息</h1>
      </div>
    </div>

    <div v-if="error" class="alert">
      <span>{{ error }}</span>
      <button class="btn btn-sm btn-ghost" @click="router.back()">返回</button>
    </div>

    <div v-else-if="loading" class="card card-pad">
      <span class="skel" style="width: 40%; height: 24px" />
    </div>

    <template v-else-if="profile">
      <!-- 基本信息卡 -->
      <div class="card card-pad" style="margin-bottom: var(--space-6)">
        <div class="profile-head">
          <img
            v-if="profile.avatar"
            class="avatar lg"
            :src="profile.avatar"
            alt=""
          />
          <div v-else class="avatar lg">{{ (profile.real_name || profile.username || '?').slice(0, 1) }}</div>
          <div class="profile-id">
            <div style="display: flex; align-items: center; gap: var(--space-3); flex-wrap: wrap">
              <h2 class="h2" style="margin: 0">{{ profile.real_name || profile.username }}</h2>
              <span class="badge badge-muted">{{ profile.role_display }}</span>
            </div>
            <div class="body-sm text-secondary" style="margin-top: var(--space-2)">
              <span>{{ profile.school_name || '未绑定学校' }}</span>
            </div>
            <p v-if="profile.bio" class="body-sm text-secondary" style="margin-top: var(--space-3)">
              {{ profile.bio }}
            </p>
          </div>
        </div>
      </div>

      <!-- 各平台 rating -->
      <div v-if="profile.platform_ratings.length" class="card card-pad" style="margin-bottom: var(--space-6)">
        <div class="card-title" style="margin-bottom: var(--space-4)">各平台 Rating</div>
        <div class="grid grid-3" style="gap: var(--space-4)">
          <div v-for="pr in profile.platform_ratings" :key="pr.platform" class="stat-card">
            <div class="stat-label">
              <span class="platform-tag" :class="accountTag(pr.platform)">{{ platformTag(pr.platform) }}</span>
              <span class="caption text-tertiary" style="margin-left: var(--space-2)">{{ pr.handle }}</span>
            </div>
            <div class="stat-value num">{{ pr.rating }}</div>
            <div class="stat-sub">
              <template v-if="pr.delta == null">—</template>
              <span v-else :class="pr.delta >= 0 ? 'up' : 'down'">{{ pr.delta >= 0 ? '▲' : '▼' }} {{ fmtDelta(pr.delta) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 参赛记录 -->
      <div class="card" style="overflow: hidden">
        <div class="card-header">
          <div class="card-title">参赛记录</div>
          <span class="caption text-tertiary">共 {{ profile.participations.length }} 场</span>
        </div>
        <div class="table-wrap" style="border: none; border-radius: 0">
          <table class="data-table">
            <thead>
              <tr>
                <th>比赛名称</th>
                <th>平台</th>
                <th class="num-cell">时间</th>
                <th class="num-cell">排名</th>
                <th class="num-cell">Rating 变化</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="p in profile.participations" :key="p.id">
                <td>
                  <a v-if="p.contest_url" :href="p.contest_url" target="_blank" rel="noopener" class="title-link">{{ p.contest_name }}</a>
                  <span v-else class="title-link">{{ p.contest_name }}</span>
                </td>
                <td><span class="platform-tag" :class="accountTag(p.contest_platform)">{{ platformTag(p.contest_platform) }}</span></td>
                <td class="num-cell">{{ fmtDate(p.contest_start_time) }}</td>
                <td class="num-cell">{{ p.rank != null ? '#' + p.rank : '—' }}</td>
                <td class="num-cell">
                  <template v-if="p.rating_delta == null">—</template>
                  <span v-else :class="p.rating_delta >= 0 ? 'up' : 'down'">
                    {{ p.rating_delta >= 0 ? '▲' : '▼' }} {{ fmtDelta(p.rating_delta) }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
          <EmptyState v-if="profile.participations.length === 0" title="暂无参赛记录" hint="该用户暂无计入排行的比赛" />
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.profile-head {
  display: flex;
  align-items: center;
  gap: var(--space-6);
  flex-wrap: wrap;
}
.avatar.lg {
  width: 72px;
  height: 72px;
  border-radius: var(--radius-xl);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  font-weight: 700;
  color: #fff;
  background: var(--gradient-primary);
  flex-shrink: 0;
  object-fit: cover;
}
.profile-id { flex: 1; min-width: 200px; }
.alert {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  background: var(--color-danger-subtle);
  border: 1px solid rgba(239, 68, 68, 0.25);
  color: var(--color-danger);
  border-radius: var(--radius-md);
  padding: var(--space-3) var(--space-4);
  margin-bottom: var(--space-5);
}
.title-link { font-weight: 700; color: var(--color-text-primary); }
.title-link:hover { color: var(--color-primary); }
.up { color: var(--color-success); font-weight: 600; }
.down { color: var(--color-danger); font-weight: 600; }
</style>
