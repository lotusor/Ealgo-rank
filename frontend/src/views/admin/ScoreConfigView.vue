<script setup lang="ts">
import { reactive, ref, onMounted } from 'vue'
import { listScoreConfigs, createScoreConfig } from '@/api'
import type { ScoreConfig } from '@/api/types'
import { useToast } from '@/composables/useToast'

const toast = useToast()
const loading = ref(false)
const saving = ref(false)

const empty: ScoreConfig = {
  id: 0,
  cf_factor: '1.000',
  atcoder_factor: '1.000',
  nowcoder_factor: '0.800',
  default_contest_factor: '1.000',
  platform_weight: '0.500',
  contest_weight: '0.500',
  recent_contest_limit: 0,
  created_at: '',
  updated_at: '',
}

const form = reactive<ScoreConfig>({ ...empty })

async function load() {
  loading.value = true
  try {
    const res = await listScoreConfigs({ page: 1, page_size: 1 })
    if (res.results.length) {
      Object.assign(form, res.results[0])
    }
  } catch (e: any) {
    toast.error(e?.response?.data?.detail || '加载积分系数失败')
  } finally {
    loading.value = false
  }
}

async function onSave() {
  saving.value = true
  try {
    const payload = {
      cf_factor: form.cf_factor,
      atcoder_factor: form.atcoder_factor,
      nowcoder_factor: form.nowcoder_factor,
      default_contest_factor: form.default_contest_factor,
      platform_weight: form.platform_weight,
      contest_weight: form.contest_weight,
      recent_contest_limit: Number(form.recent_contest_limit) || 0,
    }
    const saved = await createScoreConfig(payload)
    Object.assign(form, saved)
    toast.success('积分系数已保存（全站统一生效）')
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
        <div class="breadcrumb"><span>管理后台</span><span>/</span><span>积分系数</span></div>
        <h1 class="page-title">积分系数设置</h1>
        <p class="page-subtitle">全局统一的积分加权系数，仅超级管理员可设置，对所有学校生效</p>
      </div>
    </div>

    <div v-if="loading" class="card card-pad body-sm text-tertiary">加载中…</div>

    <div v-else class="card card-pad" style="max-width: 720px">
      <div class="section-title" style="font-size: 16px; margin-bottom: var(--space-4)">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 3v18h18M7 16l4-4 4 4 5-5" /></svg>
        平台系数
      </div>
      <div class="grid-2">
        <div class="field">
          <label class="field-label">Codeforces 平台系数</label>
          <input v-model="form.cf_factor" class="input" type="number" step="0.001" />
        </div>
        <div class="field">
          <label class="field-label">AtCoder 平台系数</label>
          <input v-model="form.atcoder_factor" class="input" type="number" step="0.001" />
        </div>
        <div class="field">
          <label class="field-label">牛客 平台系数</label>
          <input v-model="form.nowcoder_factor" class="input" type="number" step="0.001" />
        </div>
        <div class="field">
          <label class="field-label">比赛难度默认系数</label>
          <input v-model="form.default_contest_factor" class="input" type="number" step="0.001" />
        </div>
      </div>

      <div class="divider"></div>

      <div class="section-title" style="font-size: 16px; margin-bottom: var(--space-4)">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8" /><path d="M21 3v5h-5" /></svg>
        加权比例
      </div>
      <p class="body-sm text-tertiary" style="margin-bottom: var(--space-4)">
        平台系数权重 + 比赛系数权重 应等于 1。最终积分 = 基础分 ×（平台系数权重×平台系数 + 比赛系数权重×比赛难度系数）。
      </p>
      <div class="grid-2">
        <div class="field">
          <label class="field-label">平台系数权重</label>
          <input v-model="form.platform_weight" class="input" type="number" step="0.001" min="0" max="1" />
        </div>
        <div class="field">
          <label class="field-label">比赛系数权重</label>
          <input v-model="form.contest_weight" class="input" type="number" step="0.001" min="0" max="1" />
        </div>
      </div>

      <div class="divider"></div>

      <div class="field" style="max-width: 320px">
        <label class="field-label">计分场次上限（0 = 不限制）</label>
        <input v-model.number="form.recent_contest_limit" class="input" type="number" min="0" />
        <p class="body-sm text-tertiary" style="margin-top: var(--space-2)">
          只统计每个平台最近 N 场，避免老账号靠场次堆积拉高积分。
        </p>
      </div>

      <div class="divider"></div>
      <button class="btn btn-primary" :disabled="saving" @click="onSave">
        {{ saving ? '保存中…' : '保存积分系数' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-4);
}
@media (max-width: 640px) {
  .grid-2 { grid-template-columns: 1fr; }
}
.divider {
  height: 1px;
  background: var(--color-border);
  margin: var(--space-5) 0;
}
</style>
