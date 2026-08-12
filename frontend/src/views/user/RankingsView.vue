<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { listRankings, listSchools } from '@/api'
import type { RankSnapshot, School } from '@/api/types'
import { fmtScore, fmtCount, medalRowClass } from '@/utils/format'
import RankBadge from '@/components/ui/RankBadge.vue'
import OrgLogo from '@/components/ui/OrgLogo.vue'
import UserAvatar from '@/components/ui/UserAvatar.vue'
import PageTabs from '@/components/ui/PageTabs.vue'
import SegmentedControl from '@/components/ui/SegmentedControl.vue'
import DataPagination from '@/components/ui/DataPagination.vue'
import EmptyState from '@/components/ui/EmptyState.vue'

type Scope = 'school' | 'student'
const scope = ref<Scope>('school')
const period = ref<string>('all')
const schoolId = ref<number | null>(null)
const schoolSearch = ref('')
const page = ref(1)
const pageSize = 20

const rows = ref<RankSnapshot[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref<string | null>(null)
const schools = ref<School[]>([])

// 学校榜「少而全」：一次拉全量，搜索/翻页在前端做，贴合原型内存 mock 行为
const allSchoolRows = ref<RankSnapshot[]>([])

const year = new Date().getFullYear()
const periodOptions = computed(() => {
  const opts = [{ label: '全部时间', value: 'all' }]
  for (let y = year; y >= year - 2; y--) {
    opts.push({ label: `${y} 年`, value: String(y) })
  }
  return opts
})
const schoolOptions = computed(() =>
  schools.value.map((s) => ({ label: s.name, value: s.id })),
)

const isSchoolScope = computed(() => scope.value === 'school')

/** 学校榜按名称本地过滤（后端榜单接口无 search 参数）。 */
const filteredSchoolRows = computed(() => {
  const q = schoolSearch.value.trim().toLowerCase()
  if (!q) return allSchoolRows.value
  return allSchoolRows.value.filter((r) =>
    (r.school_name || '').toLowerCase().includes(q),
  )
})

const pageRows = computed<RankSnapshot[]>(() => {
  if (isSchoolScope.value) {
    const start = (page.value - 1) * pageSize
    return filteredSchoolRows.value.slice(start, start + pageSize)
  }
  return rows.value
})
const pageTotal = computed(() =>
  isSchoolScope.value ? filteredSchoolRows.value.length : total.value,
)

/** 学校榜行：用学校列表里的 short_name / code 提升 logo 可读性。 */
function schoolMeta(id: number | null) {
  if (id == null) return { name: '', shortName: null as string | null }
  const s = schools.value.find((x) => x.id === id)
  return { name: s?.name || '', shortName: s?.short_name || null }
}

async function loadSchoolAll() {
  loading.value = true
  error.value = null
  try {
    const { results } = await listRankings({
      scope: 'school',
      period: period.value,
      page: 1,
      page_size: 200,
    })
    allSchoolRows.value = results
  } catch (e: any) {
    error.value = e?.response?.data?.detail || '加载榜单失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

async function loadStudents() {
  loading.value = true
  error.value = null
  try {
    const { count, results } = await listRankings({
      scope: 'student',
      period: period.value,
      school: schoolId.value ?? undefined,
      page: page.value,
      page_size: pageSize,
    })
    rows.value = results
    total.value = count
  } catch (e: any) {
    error.value = e?.response?.data?.detail || '加载榜单失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

function load() {
  if (isSchoolScope.value) loadSchoolAll()
  else loadStudents()
}

onMounted(async () => {
  try {
    const { results } = await listSchools({ page_size: 100 })
    schools.value = results
  } catch {
    /* 学校下拉失败不影响榜单 */
  }
  load()
})

watch(scope, () => {
  page.value = 1
  schoolId.value = null
  schoolSearch.value = ''
  load()
})
watch(period, () => {
  page.value = 1
  load()
})
watch(schoolId, () => {
  page.value = 1
  if (!isSchoolScope.value) load()
})
watch(page, () => {
  if (!isSchoolScope.value) load()
})
watch(schoolSearch, () => {
  page.value = 1
})
</script>

<template>
  <div class="container-wide">
    <div class="page-head">
      <div>
        <div class="breadcrumb"><span>排名榜</span></div>
        <h1 class="page-title">积分排名</h1>
        <p class="page-subtitle">按学校 / 个人维度查看算法竞赛积分排行</p>
      </div>
    </div>

    <PageTabs
      v-model="scope"
      :options="[
        { label: '学校榜', value: 'school' },
        { label: '学生榜', value: 'student' },
      ]"
    />

    <div class="filter-bar">
      <SegmentedControl v-model="period" :options="periodOptions" />
      <div style="margin-left: auto">
        <div v-if="!isSchoolScope" class="input-group">
          <select class="select" v-model="schoolId">
            <option :value="null">全部学校</option>
            <option v-for="s in schoolOptions" :key="s.value" :value="s.value">
              {{ s.label }}
            </option>
          </select>
        </div>
        <div v-else class="input-group">
          <svg
            class="input-icon"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
          >
            <circle cx="11" cy="11" r="8" />
            <path d="m21 21-4.35-4.35" />
          </svg>
          <input
            class="input"
            type="text"
            v-model="schoolSearch"
            placeholder="搜索学校名称…"
          />
        </div>
      </div>
    </div>

    <div v-if="error" class="alert">
      <span>{{ error }}</span>
      <button class="btn btn-sm btn-ghost" @click="load">重试</button>
    </div>

    <div class="card" style="overflow: hidden">
      <div class="table-wrap" style="border: none; border-radius: 0">
        <table class="data-table">
          <colgroup v-if="isSchoolScope">
            <col style="width: 80px" />
            <col />
            <col style="width: 120px" />
            <col style="width: 110px" />
            <col style="width: 110px" />
          </colgroup>
          <colgroup v-else>
            <col style="width: 80px" />
            <col />
            <col style="width: 180px" />
            <col style="width: 120px" />
            <col style="width: 110px" />
          </colgroup>
          <thead>
            <tr v-if="isSchoolScope">
              <th class="center">排名</th>
              <th>学校</th>
              <th class="num-cell">总积分</th>
              <th class="center">参赛场次</th>
              <th class="center">成员数</th>
            </tr>
            <tr v-else>
              <th class="center">排名</th>
              <th>学生</th>
              <th>所属学校</th>
              <th class="num-cell">总积分</th>
              <th class="center">参赛场次</th>
            </tr>
          </thead>
          <tbody v-if="loading">
            <tr v-for="n in 8" :key="n">
              <td class="center"><span class="skel" style="width: 28px" /></td>
              <td><span class="skel" style="width: 60%" /></td>
              <td><span class="skel" style="width: 40%" /></td>
              <td class="center"><span class="skel" style="width: 36px" /></td>
              <td class="center"><span class="skel" style="width: 28px" /></td>
            </tr>
          </tbody>
          <tbody v-else-if="pageRows.length">
            <tr
              v-for="r in pageRows"
              :key="r.id"
              :class="medalRowClass(r.rank)"
            >
              <td class="center">
                <RankBadge :rank="r.rank" />
              </td>
              <template v-if="isSchoolScope">
                <td>
                  <div class="cell-org">
                    <OrgLogo
                      :name="schoolMeta(r.school).name"
                      :short-name="schoolMeta(r.school).shortName"
                    />
                    <span class="cell-ellipsis">{{ r.school_name }}</span>
                  </div>
                </td>
                <td class="score num-cell">{{ fmtScore(r.total_score) }}</td>
                <td class="num-cell center">{{ fmtCount(r.contest_count) }}</td>
                <td class="num-cell center">{{ fmtCount(r.member_count) }}</td>
              </template>
              <template v-else>
                <td>
                  <div class="cell-user">
                    <UserAvatar :name="r.user_name" :size="30" />
                    <span class="cell-ellipsis">{{ r.user_name }}</span>
                  </div>
                </td>
                <td class="text-secondary">
                  <span class="cell-ellipsis">{{ r.user_school_name || '—' }}</span>
                </td>
                <td class="score num-cell">{{ fmtScore(r.total_score) }}</td>
                <td class="num-cell center">{{ fmtCount(r.contest_count) }}</td>
              </template>
            </tr>
          </tbody>
        </table>

        <EmptyState
          v-if="!loading && !error && pageRows.length === 0"
          title="暂无榜单数据"
          hint="换个时间范围或筛选条件试试"
        />
      </div>
    </div>

    <DataPagination
      v-if="!error"
      v-model:page="page"
      :page-size="pageSize"
      :total="pageTotal"
    />
  </div>
</template>

<style scoped>
.data-table td.score {
  color: var(--color-primary);
  font-weight: 700;
  font-size: 15px;
}
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
  font-size: 14px;
}
</style>
