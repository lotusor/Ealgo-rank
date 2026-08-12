<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { listUsers, listSchools } from '@/api'
import type { UserRoster, School } from '@/api/types'
import { useToast } from '@/composables/useToast'
import DataPagination from '@/components/ui/DataPagination.vue'
import { fmtDate } from '@/utils/format'

const auth = useAuthStore()
const toast = useToast()

const data = ref<UserRoster[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = 20
const total = ref(0)

const keyword = ref('')
const bind = ref<'all' | 'full' | 'partial'>('all')
const schools = ref<School[]>([])
const schoolSel = ref<number | null>(null)

const bindOptions = [
  { label: '全部绑定状态', value: 'all' as const },
  { label: '三平台已绑定', value: 'full' as const },
  { label: '部分绑定', value: 'partial' as const },
]

async function load() {
  loading.value = true
  try {
    const params: any = { page: page.value, page_size: pageSize }
    if (keyword.value.trim()) params.keyword = keyword.value.trim()
    if (auth.isSuperAdmin && schoolSel.value) params.school = schoolSel.value
    const res = await listUsers(params)
    let rows = res.results
    if (bind.value === 'full') rows = rows.filter((u) => u.platform_accounts_count >= 3)
    else if (bind.value === 'partial') rows = rows.filter((u) => u.platform_accounts_count < 3)
    data.value = rows
    total.value = res.count
  } catch (e: any) {
    toast.error(e?.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
  }
}

async function loadSchools() {
  if (!auth.isSuperAdmin) return
  try {
    const res = await listSchools({ page_size: 200 })
    schools.value = res.results
  } catch {
    /* 忽略 */
  }
}

function roleCls(r: string) {
  return r === 'super_admin' ? 'badge-danger' : r === 'school_admin' ? 'badge-warning' : 'badge-muted'
}

function resetPage() {
  page.value = 1
  load()
}

onMounted(() => {
  load()
  loadSchools()
})
</script>

<template>
  <div class="container">
    <div class="page-head">
      <div>
        <div class="breadcrumb"><span>管理后台</span><span>/</span><span>成员名单</span></div>
        <h1 class="page-title">成员名单</h1>
        <p class="page-subtitle">本校已注册并绑定平台账号的学生列表</p>
      </div>
    </div>

    <div class="filter-bar">
      <div class="input-group" style="flex: 1; max-width: 320px">
        <svg class="input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" /></svg>
        <input v-model="keyword" class="input" type="text" placeholder="搜索姓名 / 学号 / 用户名…" @keyup.enter="resetPage" />
      </div>
      <select v-if="auth.isSuperAdmin" v-model.number="schoolSel" class="input" style="width: auto" @change="resetPage">
        <option :value="null">全部学校</option>
        <option v-for="s in schools" :key="s.id" :value="s.id">{{ s.name }}</option>
      </select>
      <select v-model="bind" class="input" style="width: auto" @change="resetPage">
        <option v-for="o in bindOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
      </select>
      <button class="btn btn-ghost" @click="resetPage">查询</button>
      <span class="caption text-tertiary" style="margin-left: auto">共 <b class="num">{{ total }}</b> 人</span>
    </div>

    <div class="card" style="overflow: hidden">
      <div class="table-wrap" style="border: none; border-radius: 0">
        <table class="data-table">
          <colgroup>
            <col style="width: 16%" />
            <col style="width: 14%" />
            <col style="width: 14%" />
            <col style="width: 18%" />
            <col style="width: 10%" />
            <col style="width: 14%" />
            <col style="width: 14%" />
          </colgroup>
          <thead>
            <tr><th>用户名</th><th>真实姓名</th><th>学号</th><th>学校</th><th class="num-cell">平台账号</th><th>角色</th><th class="num-cell">注册时间</th></tr>
          </thead>
          <tbody>
            <tr v-for="u in data" :key="u.id">
              <td class="cell-strong">{{ u.username }}</td>
              <td>{{ u.real_name || '—' }}</td>
              <td class="num-cell">{{ u.student_no || '—' }}</td>
              <td class="cell-ellipsis">{{ u.school_name || '—' }}</td>
              <td class="num-cell num">
                <span :class="u.platform_accounts_count >= 3 ? 'text-success' : 'text-warning'">{{ u.platform_accounts_count }}</span>
                <span class="text-tertiary">/3</span>
              </td>
              <td><span class="badge" :class="roleCls(u.role)">{{ u.role_display }}</span></td>
              <td class="num-cell">{{ fmtDate(u.date_joined) }}</td>
            </tr>
            <tr v-if="!data.length"><td colspan="7" class="empty-cell">暂无成员</td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <DataPagination v-model:page="page" :page-size="pageSize" :total="total" @update:page="(p) => { page = p; load() }" />
  </div>
</template>

<style scoped>
.empty-cell { text-align: center; color: var(--color-text-tertiary); padding: var(--space-5); }
.filter-bar { flex-wrap: wrap; }
</style>
