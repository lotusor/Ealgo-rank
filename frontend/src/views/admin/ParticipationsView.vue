<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { listParticipations, excludeParticipation, restoreParticipation } from '@/api'
import type { Participation } from '@/api/types'
import { useToast } from '@/composables/useToast'
import SegmentedControl from '@/components/ui/SegmentedControl.vue'
import DataPagination from '@/components/ui/DataPagination.vue'
import { fmtDate, fmtScore } from '@/utils/format'

const toast = useToast()

const data = ref<Participation[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = 20

const user = ref('')
const platform = ref<'all' | 'codeforces' | 'atcoder' | 'nowcoder'>('all')
const exStatus = ref<'all' | 'normal' | 'excluded'>('all')

const platformOptions = [
  { label: '全部平台', value: 'all' as const },
  { label: 'CF', value: 'codeforces' as const },
  { label: 'AtCoder', value: 'atcoder' as const },
  { label: '牛客', value: 'nowcoder' as const },
]
const statusOptions = [
  { label: '全部', value: 'all' as const },
  { label: '正常', value: 'normal' as const },
  { label: '已排除', value: 'excluded' as const },
]

async function load() {
  loading.value = true
  try {
    const params: any = { page: page.value, page_size: pageSize }
    if (user.value.trim()) params.user = user.value.trim()
    if (platform.value !== 'all') params.platform = platform.value
    if (exStatus.value === 'normal') params.is_excluded = 'false'
    else if (exStatus.value === 'excluded') params.is_excluded = 'true'
    const res = await listParticipations(params)
    data.value = res.results
    total.value = res.count
  } finally {
    loading.value = false
  }
}

const total = ref(0)

async function onExclude(p: Participation) {
  try {
    await excludeParticipation(p.id)
    toast.success('已人工剔除（不计入积分）')
    await load()
  } catch (e: any) {
    toast.error(e?.response?.data?.detail || '操作失败')
  }
}
async function onRestore(p: Participation) {
  try {
    await restoreParticipation(p.id)
    toast.success('已恢复计入积分')
    await load()
  } catch (e: any) {
    toast.error(e?.response?.data?.detail || '操作失败')
  }
}

function resetPage() {
  page.value = 1
  load()
}

onMounted(load)
</script>

<template>
  <div class="container">
    <div class="page-head">
      <div>
        <div class="breadcrumb"><span>管理后台</span><span>/</span><span>参赛记录</span></div>
        <h1 class="page-title">参赛记录管理</h1>
        <p class="page-subtitle">审核与管理爬取的参赛成绩记录</p>
      </div>
    </div>

    <div class="filter-bar">
      <div class="input-group" style="flex: 1; max-width: 260px">
        <svg class="input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" /></svg>
        <input v-model="user" class="input" type="text" placeholder="选手用户名 / handle" @keyup.enter="resetPage" />
      </div>
      <SegmentedControl v-model="platform" :options="platformOptions" />
      <SegmentedControl v-model="exStatus" :options="statusOptions" />
      <button class="btn btn-ghost" @click="resetPage">查询</button>
      <span class="caption text-tertiary" style="margin-left: auto">共 <b class="num">{{ total }}</b> 条</span>
    </div>

    <div class="card" style="overflow: hidden">
      <div class="table-wrap" style="border: none; border-radius: 0">
        <table class="data-table">
          <colgroup>
            <col style="width: 14%" />
            <col style="width: 22%" />
            <col style="width: 12%" />
            <col style="width: 8%" />
            <col style="width: 8%" />
            <col style="width: 10%" />
            <col style="width: 14%" />
            <col style="width: 12%" />
            <col style="width: 8%" />
          </colgroup>
          <thead>
            <tr><th>学生</th><th>比赛</th><th>平台</th><th class="num-cell">排名</th><th class="num-cell">解题数</th><th class="num-cell">积分</th><th>状态</th><th class="num-cell">时间</th><th class="center">操作</th></tr>
          </thead>
          <tbody>
            <tr v-for="p in data" :key="p.id">
              <td class="cell-strong">{{ p.user_real_name || p.user_username }}</td>
              <td class="cell-ellipsis">{{ p.contest_name }}</td>
              <td>{{ p.contest_platform_display }}</td>
              <td class="num-cell num">{{ p.rank != null ? '#' + p.rank : '—' }}</td>
              <td class="num-cell num">{{ p.solved_count != null ? p.solved_count : '—' }}</td>
              <td class="num-cell num">{{ fmtScore(p.total_score) }}</td>
              <td>
                <span class="badge" :class="p.is_excluded ? 'badge-danger' : 'badge-success'">
                  {{ p.is_excluded ? `已排除 · ${p.exclude_reason_display}` : '计入' }}
                </span>
              </td>
              <td class="num-cell">{{ fmtDate(p.contest_start_time) }}</td>
              <td class="center">
                <button v-if="p.is_excluded" class="btn btn-sm btn-primary" @click="onRestore(p)">恢复</button>
                <button v-else class="btn btn-sm btn-danger" @click="onExclude(p)">剔除</button>
              </td>
            </tr>
            <tr v-if="!data.length"><td colspan="9" class="empty-cell">暂无记录</td></tr>
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
