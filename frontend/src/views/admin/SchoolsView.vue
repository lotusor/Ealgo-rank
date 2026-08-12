<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { listSchools, updateSchool, createSchool } from '@/api'
import type { School } from '@/api/types'
import { useToast } from '@/composables/useToast'
import DataPagination from '@/components/ui/DataPagination.vue'

const auth = useAuthStore()
const toast = useToast()

const schools = ref<School[]>([])
const loading = ref(false)
const keyword = ref('')
const page = ref(1)
const pageSize = 20

const showEdit = ref(false)
const editing = ref<School | null>(null)
const saving = ref(false)
const form = ref({ name: '', short_name: '', code: '', description: '' })

const filtered = computed(() => {
  const k = keyword.value.trim().toLowerCase()
  if (!k) return schools.value
  return schools.value.filter(
    (s) =>
      s.name.toLowerCase().includes(k) ||
      s.short_name.toLowerCase().includes(k) ||
      s.code.toLowerCase().includes(k),
  )
})

async function load() {
  loading.value = true
  try {
    const res = await listSchools({ page: 1, page_size: 200 })
    schools.value = res.results
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.value = null
  form.value = { name: '', short_name: '', code: '', description: '' }
  showEdit.value = true
}
function openEdit(s: School) {
  editing.value = s
  form.value = { name: s.name, short_name: s.short_name, code: s.code, description: s.description }
  showEdit.value = true
}

async function save() {
  if (!form.value.name.trim()) {
    toast.error('请填写学校名称')
    return
  }
  saving.value = true
  try {
    if (editing.value) {
      await updateSchool(editing.value.id, { ...form.value })
      toast.success('学校已更新')
    } else {
      await createSchool({ ...form.value })
      toast.success('学校已创建')
    }
    showEdit.value = false
    await load()
  } catch (e: any) {
    toast.error(e?.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="container">
    <div class="page-head">
      <div>
        <div class="breadcrumb">
          <span>管理后台</span><span>/</span><span>学校管理</span>
        </div>
        <h1 class="page-title">学校管理</h1>
        <p class="page-subtitle">维护参与排名的高校信息</p>
      </div>
      <button v-if="auth.isSuperAdmin" class="btn btn-primary" @click="openCreate">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14" /></svg>
        新增学校
      </button>
    </div>

    <div class="filter-bar">
      <div class="input-group" style="flex: 1; max-width: 360px">
        <svg class="input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" /></svg>
        <input v-model="keyword" class="input" type="text" placeholder="搜索学校名称 / 简称 / 代码…" />
      </div>
      <span class="caption text-tertiary" style="margin-left: auto">共 <b class="num">{{ filtered.length }}</b> 所学校</span>
    </div>

    <div class="card" style="overflow: hidden">
      <div class="table-wrap" style="border: none; border-radius: 0">
        <table class="data-table">
          <colgroup>
            <col style="width: 28%" />
            <col style="width: 14%" />
            <col style="width: 14%" />
            <col style="width: 16%" />
            <col style="width: 12%" />
            <col style="width: 16%" />
          </colgroup>
          <thead>
            <tr><th>学校名称</th><th>简称</th><th class="num-cell">代码</th><th class="num-cell">学生数</th><th class="center">状态</th><th class="center">操作</th></tr>
          </thead>
          <tbody>
            <tr v-for="s in filtered.slice((page - 1) * pageSize, page * pageSize)" :key="s.id">
              <td>
                <div class="cell-strong">{{ s.name }}</div>
                <div v-if="s.description" class="cell-sub">{{ s.description }}</div>
              </td>
              <td>{{ s.short_name || '—' }}</td>
              <td class="num-cell num">{{ s.code || '—' }}</td>
              <td class="num-cell num">{{ s.member_count }}</td>
              <td class="center">
                <span class="badge" :class="s.is_active ? 'badge-success' : 'badge-muted'">{{ s.is_active ? '启用' : '停用' }}</span>
              </td>
              <td class="center">
                <button v-if="auth.isSuperAdmin" class="btn btn-sm btn-ghost" @click="openEdit(s)">编辑</button>
                <span v-else class="text-tertiary">—</span>
              </td>
            </tr>
            <tr v-if="!filtered.length"><td colspan="6" class="empty-cell">暂无学校</td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <DataPagination
      v-model:page="page"
      :page-size="pageSize"
      :total="filtered.length"
      @update:page="page = $event"
    />

    <div v-if="showEdit" class="modal-overlay" @click.self="showEdit = false">
      <div class="modal" style="width: 480px">
        <div class="modal-header">{{ editing ? '编辑学校' : '新增学校' }}</div>
        <div class="modal-body">
          <div class="field">
            <label class="field-label">学校名称</label>
            <input v-model="form.name" class="input" placeholder="如：清华大学" />
          </div>
          <div class="field">
            <label class="field-label">简称</label>
            <input v-model="form.short_name" class="input" placeholder="如：THU" />
          </div>
          <div class="field">
            <label class="field-label">代码</label>
            <input v-model="form.code" class="input" placeholder="如：THU" />
          </div>
          <div class="field">
            <label class="field-label">描述</label>
            <textarea v-model="form.description" class="input" rows="3" placeholder="可选" />
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-ghost" @click="showEdit = false">取消</button>
          <button class="btn btn-primary" :disabled="saving" @click="save">{{ saving ? '保存中…' : '保存' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.empty-cell { text-align: center; color: var(--color-text-tertiary); padding: var(--space-5); }
</style>
